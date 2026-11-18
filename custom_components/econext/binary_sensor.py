"""Binary sensor platform for ecoNEXT integration."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, get_alarm_name
from .cooling.entity import build_cooling_binary_sensors
from .coordinator import EconextCoordinator
from .entity import EconextEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNEXT binary sensor entities from a config entry."""
    coordinator: EconextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[BinarySensorEntity] = [
        EconextAlarmActiveBinarySensor(coordinator),
        EconextDataProblemBinarySensor(coordinator),
    ]
    entities.extend(build_cooling_binary_sensors(coordinator))
    async_add_entities(entities)


class EconextAlarmActiveBinarySensor(EconextEntity, BinarySensorEntity):
    """Binary sensor that indicates if any alarm is currently active."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert"
    _attr_translation_key = "alarm_active"

    def __init__(self, coordinator: EconextCoordinator) -> None:
        """Initialize the alarm active binary sensor."""
        # Use a sentinel param_id since this entity reads from alarm data, not parameters
        super().__init__(coordinator, "_alarms", None)
        uid = coordinator.get_device_uid()
        self._attr_unique_id = f"{uid}_alarm_active"

    @property
    def is_on(self) -> bool | None:
        """Return True if any alarm is currently active (unresolved)."""
        return len(self.coordinator.active_alarms) > 0

    @property
    def extra_state_attributes(self) -> dict:
        """Return active alarm details."""
        active = self.coordinator.active_alarms
        return {
            "active_alarm_count": len(active),
            "active_alarm_codes": [{"code": a.get("code"), "name": get_alarm_name(a.get("code", 0))} for a in active],
        }

    def _is_value_valid(self) -> bool:
        """Alarm data is always valid if coordinator is updating."""
        return True


class EconextDataProblemBinarySensor(EconextEntity, BinarySensorEntity):
    """On while the gateway does not vouch for its values.

    That is after a controller restart or while the controller does not
    answer. The other entities then keep the last valid values and turn
    unavailable when it lasts; this one says so at once, with the reason.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "controller_data"

    def __init__(self, coordinator: EconextCoordinator) -> None:
        """Initialize the data problem binary sensor."""
        # Sentinel param_id: this entity reads the readiness, not a parameter
        super().__init__(coordinator, "_data_ready", None)
        uid = coordinator.get_device_uid()
        self._attr_unique_id = f"{uid}_controller_data"

    @property
    def is_on(self) -> bool:
        """Return True while the data is not ready."""
        return not self.coordinator.data_ready

    @property
    def extra_state_attributes(self) -> dict:
        """Return why the data is not ready, or "ok"."""
        return {"reason": self.coordinator.ready_reason}

    @property
    def available(self) -> bool:
        """Stay available while the data is not ready: that is what it reports."""
        return self.coordinator.last_update_success
