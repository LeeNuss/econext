"""Button platform for ecoNEXT integration."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_THERMOSTAT_ENTITY, DOMAIN, EconextButtonEntityDescription, HEATPUMP_BUTTONS
from .coordinator import EconextCoordinator
from .entity import EconextEntity

_LOGGER = logging.getLogger(__name__)


def thermostat_device_info(coordinator: EconextCoordinator) -> dict:
    """Build device info for the Virtual Thermostat sub-device."""
    uid = coordinator.get_device_uid()
    return {
        "identifiers": {(DOMAIN, f"{uid}_virtual_thermostat")},
        "name": "Virtual Thermostat",
        "manufacturer": "ecoNEXT Gateway",
        "model": "ecoSTER (virtual)",
        "via_device": (DOMAIN, uid),
    }


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

    # Add thermostat pairing button only if thermostat is configured
    if entry.options.get(CONF_THERMOSTAT_ENTITY):
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

    _attr_has_entity_name = True
    _attr_name = "Pair"

    def __init__(self, coordinator: EconextCoordinator) -> None:
        """Initialize the pairing button."""
        self._coordinator = coordinator
        uid = coordinator.get_device_uid()
        self._attr_unique_id = f"{uid}_virtual_thermostat_pair"
        self._attr_device_info = thermostat_device_info(coordinator)
        self._update_icon()

    def _update_icon(self) -> None:
        """Update icon based on pairing state."""
        status = self._coordinator.thermostat_status
        if status and status.get("pairing_state") == "paired":
            self._attr_icon = "mdi:link-variant"
        elif status and status.get("pairing_state") == "pairing_requested":
            self._attr_icon = "mdi:link-variant-plus"
        else:
            self._attr_icon = "mdi:link-variant-off"

    async def async_press(self) -> None:
        """Request thermostat pairing. User must enter panel pairing mode within 60s."""
        _LOGGER.info("Thermostat pairing requested via HA button")
        await self._coordinator.api.async_request_thermostat_pair()
        # Force immediate status refresh
        self._coordinator.thermostat_status = await self._coordinator.api.async_get_thermostat_status()
        self._update_icon()
        self.async_write_ha_state()
