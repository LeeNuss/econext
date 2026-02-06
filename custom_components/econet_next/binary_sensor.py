"""Binary sensor platform for ecoNET Next integration."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ALARM_BINARY_SENSORS,
    DOMAIN,
    EconetBinarySensorEntityDescription,
)
from .coordinator import EconetNextCoordinator
from .entity import EconetNextEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNET Next binary sensor entities from a config entry."""
    coordinator: EconetNextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[EconetNextBinarySensor] = []

    # Add alarm binary sensor entities
    for description in ALARM_BINARY_SENSORS:
        # Only add if parameter exists in data
        if coordinator.get_param(description.param_id) is not None:
            entities.append(EconetNextBinarySensor(coordinator, description))
        else:
            _LOGGER.debug(
                "Skipping binary sensor %s - parameter %s not found",
                description.key,
                description.param_id,
            )

    async_add_entities(entities)


class EconetNextBinarySensor(EconetNextEntity, BinarySensorEntity):
    """Representation of an ecoNET Next binary sensor entity."""

    def __init__(
        self,
        coordinator: EconetNextCoordinator,
        description: EconetBinarySensorEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the binary sensor entity."""
        # Use provided device_id or determine from device_type
        if device_id is None and description.device_type != "controller":
            device_id = description.device_type

        super().__init__(coordinator, description.param_id, device_id)

        self._description = description
        self._attr_translation_key = description.key

        # Apply description attributes
        if description.device_class:
            self._attr_device_class = description.device_class
        if description.entity_category:
            self._attr_entity_category = description.entity_category
        if description.icon:
            self._attr_icon = description.icon

        # Override unique_id to include the key for bitfield sensors
        # This ensures each bit position gets a unique ID
        uid = coordinator.get_device_uid()
        if device_id:
            self._attr_unique_id = f"{uid}_{device_id}_{description.param_id}_{description.key}"
        else:
            self._attr_unique_id = f"{uid}_{description.param_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on."""
        value = self._get_param_value()
        if value is None:
            return None

        # Read the specific bit from the bitfield
        bit_value = (int(value) >> self._description.bit_position) & 1
        return bit_value == 1
