"""Data coordinator for ecoNEXT."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EconextApiError, EconextApi
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EconextCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator to manage data updates from econext device."""

    def __init__(self, hass: HomeAssistant, api: EconextApi) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api
        self._alarms: list[dict[str, Any]] = []

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data from the API."""
        try:
            params = await self.api.async_fetch_all_params()
        except EconextApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

        # Fetch alarms (non-fatal - alarms are secondary to parameters)
        try:
            self._alarms = await self.api.async_fetch_alarms()
        except EconextApiError:
            _LOGGER.debug("Failed to fetch alarms, keeping previous data")

        return params

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

    async def async_set_param(self, param_id: str | int, value: Any) -> bool:
        """Set a parameter value on the device with optimistic local update.

        Looks up the parameter name from cached data, calls the gateway API
        by name, and on success updates the local cache for instant UI feedback.

        """
        param_key = str(param_id)
        param = self.get_param(param_key)
        if param is None:
            raise EconextApiError(f"Unknown parameter: {param_id}")

        name = param.get("name")
        if not name:
            raise EconextApiError(f"Parameter {param_id} has no name")

        result = await self.api.async_set_param(name, value)

        # On success, update local cache for instant UI feedback
        if result and self.data is not None and param_key in self.data:
            self.data[param_key]["value"] = value
            self.async_set_updated_data(self.data)

        return result
