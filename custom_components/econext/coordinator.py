"""Data coordinator for ecoNEXT."""

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from .api import (
    EconextApi,
    EconextApiError,
    EconextBatchRejectedError,
    EconextBatchUnsupportedError,
)
from .const import CONF_THERMOSTAT_ENTITY, DOMAIN, UPDATE_INTERVAL, WRITE_COALESCE_SECONDS

_LOGGER = logging.getLogger(__name__)


@dataclass
class _PendingWrite:
    """A queued write and the callers waiting on it."""

    param_key: str
    value: Any
    waiters: list[asyncio.Future[bool]] = field(default_factory=list)


class EconextCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator to manage data updates from econext device."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: EconextApi,
        thermostat_entity_id: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api
        self._alarms: list[dict[str, Any]] = []
        self._thermostat_entity_id = thermostat_entity_id
        self.thermostat_status: dict[str, Any] | None = None
        self.thermostat_source_state: str = "ok"
        # Optional cooling controller; attached by async_setup_entry when the
        # cooling feature is enabled. Ticked at the end of each refresh.
        self.cooling_driver: Any | None = None
        # Write coalescing: writes requested close together go to the gateway
        # as one batch. Keyed by parameter name, last value wins.
        self._pending_writes: dict[str, _PendingWrite] = {}
        self._write_task: asyncio.Task[None] | None = None
        self._batch_supported = True
        # Parameter count when the platforms created their entities; see
        # _check_late_parameters.
        self._entities_param_count: int | None = None
        # Device registry id of the main controller device. Set by
        # async_setup_entry before the platforms load, so sub-devices can
        # reference it via `via_device_id`.
        self.main_device_id: str | None = None

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data from the API."""
        try:
            params = await self.api.async_fetch_all_params()
        except EconextApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

        if not params:
            # A gateway that has just started has nothing cached yet. Failing
            # here makes the first refresh raise ConfigEntryNotReady, so setup
            # is retried instead of creating no entities.
            raise UpdateFailed("Gateway returned no parameters yet")
        self._check_late_parameters(len(params))

        # Fetch alarms (non-fatal - alarms are secondary to parameters)
        try:
            self._alarms = await self.api.async_fetch_alarms()
        except EconextApiError:
            _LOGGER.debug("Failed to fetch alarms, keeping previous data")

        # Submit thermostat temperature if configured
        await self._async_submit_thermostat_temperature()

        # Fetch thermostat status (non-fatal)
        try:
            self.thermostat_status = await self.api.async_get_thermostat_status()
        except Exception:
            _LOGGER.debug("Failed to fetch thermostat status")

        # Run the cooling controller tick (non-fatal — must never break the poll)
        if self.cooling_driver is not None:
            try:
                await self.cooling_driver.async_tick(dt_util.now())
            except Exception:
                _LOGGER.exception("Cooling controller tick failed")

        return params

    def mark_entities_created(self) -> None:
        """Record how many parameters the entity platforms were built from."""
        self._entities_param_count = len(self.data or {})

    def _check_late_parameters(self, count: int) -> None:
        """Reload once if many parameters arrived after the entities were made.

        Entities are only created for parameters present at setup. Gateways
        before 0.3.0b2 serve their cache while the first poll is still
        filling it, so Home Assistant starting at the same time can set up
        from a partial set and miss whole groups of entities (schedules).
        Newer gateways answer 503 until the set is complete. Small growth is
        normal (values that read as a sentinel at first), so only a jump of
        over 10% triggers the reload.
        """
        baseline = self._entities_param_count
        if baseline is None or count <= baseline * 1.1:
            return
        entry = self.config_entry
        if entry is None:
            return
        _LOGGER.info(
            "Gateway now reports %d parameters, %d at setup; reloading to add the missing entities",
            count,
            baseline,
        )
        self._entities_param_count = None
        self.hass.config_entries.async_schedule_reload(entry.entry_id)

    def get_param(self, param_id: str | int) -> dict[str, Any] | None:
        """Get a parameter by ID."""
        if self.data is None:
            return None
        return self.data.get(str(param_id))

    def get_param_value(self, param_id: str | int) -> Any:
        """Get a parameter value by ID."""
        param = self.get_param(param_id)
        if param is None:
            return None
        return param.get("value")

    def get_device_uid(self) -> str:
        """Get the device UID."""
        return self.get_param_value(10) or "unknown"

    def get_device_name(self) -> str:
        """Get the device name."""
        return self.get_param_value(374) or "ecoMAX360i"

    @property
    def alarms(self) -> list[dict[str, Any]]:
        """Get alarm history."""
        return self._alarms

    @property
    def active_alarms(self) -> list[dict[str, Any]]:
        """Get currently active (unresolved) alarms."""
        return [a for a in self._alarms if a.get("to_date") is None]

    @property
    def latest_alarm(self) -> dict[str, Any] | None:
        """Get the most recent alarm."""
        if not self._alarms:
            return None
        return self._alarms[0]

    def _classify_source(self, state) -> tuple[str, Any]:
        """Classify the source entity state. Returns (status, raw_value)."""
        if state is None:
            return "missing", None
        if state.state == STATE_UNAVAILABLE:
            return "unavailable", state.state
        if state.state == STATE_UNKNOWN:
            return "unknown", state.state
        try:
            float(state.state)
        except (ValueError, TypeError):
            return "unparseable", state.state
        return "ok", state.state

    def _update_source_state(self, new_state: str, raw: Any) -> None:
        """Log transitions of the source-entity status and remember the new one."""
        if new_state == self.thermostat_source_state:
            return
        if new_state == "ok":
            _LOGGER.info(
                "Thermostat source %s recovered (was %s)",
                self._thermostat_entity_id,
                self.thermostat_source_state,
            )
        else:
            _LOGGER.warning(
                "Thermostat source %s is %s (raw=%r); skipping push",
                self._thermostat_entity_id,
                new_state,
                raw,
            )
        self.thermostat_source_state = new_state

    async def _async_submit_thermostat_temperature(self) -> None:
        """Read the configured temperature entity and submit to gateway."""
        if not self._thermostat_entity_id:
            return

        state = self.hass.states.get(self._thermostat_entity_id)
        new_state, raw = self._classify_source(state)
        self._update_source_state(new_state, raw)
        if new_state != "ok":
            return

        await self.api.async_submit_thermostat_temperature(float(state.state))

    async def async_set_param(self, param_id: str | int, value: Any) -> bool:
        """Set a parameter value on the device with optimistic local update.

        Looks up the parameter name from cached data and queues the write.
        Writes requested within WRITE_COALESCE_SECONDS of each other (or while
        a previous batch is on the bus) are sent to the gateway together, so
        N concurrent writes cost one bus token wait instead of N. On success
        the local cache is updated for instant UI feedback.

        Raises:
            EconextApiError: The parameter is unknown or the write failed.

        """
        param_key = str(param_id)
        param = self.get_param(param_key)
        if param is None:
            raise EconextApiError(f"Unknown parameter: {param_id}")

        name = param.get("name")
        if not name:
            raise EconextApiError(f"Parameter {param_id} has no name")

        waiter: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        pending = self._pending_writes.get(name)
        if pending is None:
            self._pending_writes[name] = _PendingWrite(param_key, value, [waiter])
        else:
            pending.value = value
            pending.waiters.append(waiter)

        if self._write_task is None or self._write_task.done():
            self._write_task = asyncio.get_running_loop().create_task(self._async_flush_writes())

        return await waiter

    async def _async_flush_writes(self) -> None:
        """Send queued writes in batches until the queue is empty."""
        while self._pending_writes:
            await asyncio.sleep(WRITE_COALESCE_SECONDS)
            batch, self._pending_writes = self._pending_writes, {}
            values = {name: write.value for name, write in batch.items()}

            try:
                outcomes = await self._async_send_writes(values)
            except Exception as err:  # noqa: BLE001 - surfaced to every waiting caller
                outcomes = dict.fromkeys(values, err)

            changed = False
            for name, write in batch.items():
                outcome = outcomes.get(name)
                if outcome is True and self.data is not None and write.param_key in self.data:
                    self.data[write.param_key]["value"] = write.value
                    changed = True
                for waiter in write.waiters:
                    if waiter.done():
                        continue
                    if outcome is True:
                        waiter.set_result(True)
                    elif isinstance(outcome, BaseException):
                        waiter.set_exception(outcome)
                    else:
                        waiter.set_exception(EconextApiError(f"Controller did not acknowledge write to {name}"))

            if changed:
                self.async_set_updated_data(self.data)

    async def _async_send_writes(self, values: dict[str, Any]) -> dict[str, bool | Exception]:
        """Write values through the gateway, batched when it supports it."""
        if len(values) > 1 and self._batch_supported:
            try:
                return dict(await self.api.async_set_params(values))
            except EconextBatchUnsupportedError:
                _LOGGER.info("Gateway has no batch write endpoint; writing values one by one")
                self._batch_supported = False
            except EconextBatchRejectedError as err:
                # Nothing was written. Fall back to single writes so the valid
                # values still apply and each failure reaches its own caller.
                _LOGGER.debug("Batch rejected (%s); retrying values one by one", err)

        outcomes: dict[str, bool | Exception] = {}
        for name, value in values.items():
            try:
                outcomes[name] = await self.api.async_set_param(name, value)
            except EconextApiError as err:
                outcomes[name] = err
        return outcomes
