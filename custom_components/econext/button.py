"""Button platform for ecoNEXT integration."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EconextButtonEntityDescription, HEATPUMP_BUTTONS
from .coordinator import EconextCoordinator
from .entity import EconextEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNEXT button entities from a config entry."""
    coordinator: EconextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[ButtonEntity] = []

    # Add heat pump button entities if heat pump device should be created
    heatpump_param = coordinator.get_param("1133")
    if heatpump_param is not None:
        for description in HEATPUMP_BUTTONS:
            if coordinator.get_param(description.param_id) is not None:
                entities.append(EconextButton(coordinator, description, device_id="heatpump"))
            else:
                _LOGGER.debug(
                    "Skipping heat pump button %s - parameter %s not found",
                    description.key,
                    description.param_id,
                )

    # Add thermostat pairing button
    entities.append(ThermostatPairButton(coordinator))

    async_add_entities(entities)


class EconextButton(EconextEntity, ButtonEntity):
    """Representation of an ecoNEXT button entity."""

    def __init__(
        self,
        coordinator: EconextCoordinator,
        description: EconextButtonEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the button entity."""
        # Use provided device_id or determine from device_type
        if device_id is None and description.device_type != "controller":
            device_id = description.device_type

        super().__init__(coordinator, description.param_id, device_id)

        self._description = description
        self._attr_translation_key = description.key

        # Apply description attributes
        if description.entity_category:
            self._attr_entity_category = description.entity_category
        if description.icon:
            self._attr_icon = description.icon

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug(
            "Button %s pressed - setting parameter %s to 1",
            self._description.key,
            self._description.param_id,
        )
        await self.coordinator.async_set_param(self._description.param_id, 1)


class ThermostatPairButton(ButtonEntity):
    """Button to trigger virtual thermostat pairing on the bus."""

    _attr_name = "Pair Virtual Thermostat"
    _attr_icon = "mdi:link-variant-plus"
    _attr_entity_category = None

    def __init__(self, coordinator: EconextCoordinator) -> None:
        """Initialize the pairing button."""
        self._coordinator = coordinator
        uid = coordinator.get_device_uid()
        self._attr_unique_id = f"{uid}_thermostat_pair"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, uid)},
        }

    async def async_press(self) -> None:
        """Request thermostat pairing. User must enter panel pairing mode within 60s."""
        _LOGGER.info("Thermostat pairing requested via HA button")
        success = await self._coordinator.api.async_request_thermostat_pair()
        if not success:
            _LOGGER.warning("Thermostat pairing request failed or already paired")
