"""Entities for the cooling controller device.

These are driver-backed (not register-backed): switches and numbers write
the driver's live tunables, sensors and binary sensors reflect its state.
All attach to a single "Cooling Controller" sub-device via_device the main
controller. Builder functions are called from the platform modules.
"""

from __future__ import annotations

from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..const import DOMAIN, MANUFACTURER
from ..coordinator import EconextCoordinator
from ..entity import via_device_info
from .const import CYCLE_STATES
from .models import working_target

COOLING_DEVICE_ID = "cooling"

# (key, min, max, step, unit)
_MIN = "min"
_SEC = "s"
_C = UnitOfTemperature.CELSIUS

COOLING_NUMBER_SPECS: tuple[tuple[str, float, float, float, str | None], ...] = (
    ("safety_margin", 0, 3, 0.1, _C),
    ("delta_t_est", 0, 5, 0.1, _C),
    ("max_run_minutes", 30, 480, 10, _MIN),
    ("min_break_minutes", 0, 180, 5, _MIN),
    ("aborted_break_minutes", 0, 120, 5, _MIN),
    ("real_cycle_threshold_minutes", 0, 60, 1, _MIN),
    ("flow_below_dew_cutoff", 0, 10, 0.5, _C),
    ("flow_below_dew_min_duration_s", 0, 1800, 30, _SEC),
    ("working_target_offset", 0, 10, 0.5, _C),
    ("stale_loop_flow", 10, 50, 1, _C),
    ("hp_quiet_minutes", 0, 60, 1, _MIN),
    ("hard_floor", 0, 10, 0.5, _C),
    ("hard_floor_duration_s", 0, 1800, 30, _SEC),
    ("panic_floor", 0, 15, 0.5, _C),
    ("start_timeout_minutes", 1, 15, 1, _MIN),
    ("dip_target", 5, 20, 1, _C),
    ("cooldown_target", 18, 30, 1, _C),
)

COOLING_SWITCH_KEYS = ("enable", "dry_run")


class CoolingControllerEntity(CoordinatorEntity[EconextCoordinator]):
    """Base entity attached to the Cooling Controller sub-device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EconextCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = f"cooling_{key}"
        uid = coordinator.get_device_uid()
        self._attr_unique_id = f"{uid}_{COOLING_DEVICE_ID}_{key}"

    @property
    def driver(self):
        return self.coordinator.cooling_driver

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.driver is not None
            and self.driver.available
        )

    @property
    def device_info(self) -> DeviceInfo:
        uid = self.coordinator.get_device_uid()
        return DeviceInfo(
            identifiers={(DOMAIN, f"{uid}_{COOLING_DEVICE_ID}")},
            # Distinct from the standalone "Cooling Controller" integration so
            # entity_ids don't collide while both run in parallel.
            name="Cooling (econext)",
            manufacturer=MANUFACTURER,
            **via_device_info(self.coordinator),
        )


class CoolingNumber(CoolingControllerEntity, RestoreNumber):
    """A tunable backed by driver.tunables[key], persisted across restarts."""

    _attr_mode = NumberMode.BOX
    _attr_entity_category = None

    def __init__(
        self,
        coordinator: EconextCoordinator,
        key: str,
        minimum: float,
        maximum: float,
        step: float,
        unit: str | None,
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None and self.driver is not None:
            self.driver.update_tunable(self._key, float(last.native_value))

    @property
    def native_value(self) -> float | None:
        if self.driver is None:
            return None
        return float(self.driver.tunables[self._key])

    async def async_set_native_value(self, value: float) -> None:
        if self.driver is not None:
            self.driver.update_tunable(self._key, value)
        self.async_write_ha_state()


class CoolingSwitch(CoolingControllerEntity, SwitchEntity, RestoreEntity):
    """A boolean tunable (enable / dry_run) backed by driver.tunables[key]."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and self.driver is not None:
            self.driver.update_tunable(self._key, last.state == "on")

    @property
    def is_on(self) -> bool | None:
        if self.driver is None:
            return None
        return bool(self.driver.tunables[self._key])

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.driver is not None:
            self.driver.update_tunable(self._key, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.driver is not None:
            self.driver.update_tunable(self._key, False)
        self.async_write_ha_state()


class CoolingSensor(CoolingControllerEntity, SensorEntity):
    """A status sensor whose value is computed from the driver."""

    def __init__(
        self,
        coordinator: EconextCoordinator,
        key: str,
        value_fn: Callable[[Any], Any],
        *,
        unit: str | None = None,
        device_class: SensorDeviceClass | None = None,
        options: list[str] | None = None,
    ) -> None:
        super().__init__(coordinator, key)
        self._value_fn = value_fn
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if options is not None:
            self._attr_options = options

    @property
    def native_value(self) -> Any:
        if self.driver is None:
            return None
        return self._value_fn(self.driver)


class CoolingBinarySensor(CoolingControllerEntity, BinarySensorEntity):
    """A boolean status reflection computed from the driver."""

    def __init__(
        self,
        coordinator: EconextCoordinator,
        key: str,
        value_fn: Callable[[Any], bool | None],
    ) -> None:
        super().__init__(coordinator, key)
        self._value_fn = value_fn

    @property
    def is_on(self) -> bool | None:
        if self.driver is None:
            return None
        return self._value_fn(self.driver)


# ---------- sensor value helpers ----------


def _working_target(driver) -> float | None:
    s = driver.last_sensors
    if s is None:
        return None
    return working_target(
        s.safe_target,
        float(driver.tunables["working_target_offset"]),
        float(driver.tunables["dip_target"]),
    )


def _hp_quiet(driver) -> bool | None:
    last = driver.state.last_preempt_active_at
    if last is None:
        return True
    quiet_min = (dt_util.now() - last).total_seconds() / 60
    return quiet_min >= float(driver.tunables["hp_quiet_minutes"])


# ---------- builders called from platform modules ----------


def build_cooling_numbers(coordinator: EconextCoordinator) -> list[CoolingNumber]:
    if coordinator.cooling_driver is None:
        return []
    return [
        CoolingNumber(coordinator, key, lo, hi, step, unit)
        for key, lo, hi, step, unit in COOLING_NUMBER_SPECS
    ]


def build_cooling_switches(coordinator: EconextCoordinator) -> list[CoolingSwitch]:
    if coordinator.cooling_driver is None:
        return []
    return [CoolingSwitch(coordinator, key) for key in COOLING_SWITCH_KEYS]


def build_cooling_sensors(coordinator: EconextCoordinator) -> list[CoolingSensor]:
    if coordinator.cooling_driver is None:
        return []
    return [
        CoolingSensor(
            coordinator,
            "cycle_state",
            lambda d: d.state.cycle_state,
            device_class=SensorDeviceClass.ENUM,
            options=list(CYCLE_STATES),
        ),
        CoolingSensor(
            coordinator,
            "safe_target",
            lambda d: d.last_sensors.safe_target if d.last_sensors else None,
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        CoolingSensor(
            coordinator,
            "working_target",
            _working_target,
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        CoolingSensor(
            coordinator,
            "flow_below_dew",
            lambda d: d.last_sensors.flow_below_dew if d.last_sensors else None,
            unit=UnitOfTemperature.CELSIUS,
        ),
        CoolingSensor(
            coordinator,
            "last_running_minutes",
            lambda d: d.state.last_running_minutes,
            unit="min",
        ),
        CoolingSensor(
            coordinator,
            "last_cycle_end",
            lambda d: d.state.last_cycle_end,
            device_class=SensorDeviceClass.TIMESTAMP,
        ),
    ]


def build_cooling_binary_sensors(coordinator: EconextCoordinator) -> list[CoolingBinarySensor]:
    if coordinator.cooling_driver is None:
        return []
    return [
        CoolingBinarySensor(coordinator, "hp_quiet", _hp_quiet),
        CoolingBinarySensor(
            coordinator,
            "schedule_active",
            lambda d: d.last_sensors.schedule_active if d.last_sensors else None,
        ),
    ]
