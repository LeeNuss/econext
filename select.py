"""Select platform for ecoNET Next integration."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .climate import CIRCUITS
from .const import (
    CIRCUIT_SELECTS,
    CONTROLLER_SELECTS,
    DHW_SELECTS,
    DOMAIN,
    EconetSelectEntityDescription,
)
from .coordinator import EconetNextCoordinator
from .entity import EconetNextEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNET Next select entities from a config entry."""
    coordinator: EconetNextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[EconetNextSelect] = []

    # Add controller select entities
    for description in CONTROLLER_SELECTS:
        # Only add if parameter exists in data
        if coordinator.get_param(description.param_id) is not None:
            entities.append(EconetNextSelect(coordinator, description))
        else:
            _LOGGER.debug(
                "Skipping select %s - parameter %s not found",
                description.key,
                description.param_id,
            )

    # Add DHW select entities if DHW device should be created
    dhw_temp_param = coordinator.get_param("61")
    if dhw_temp_param is not None:
        dhw_temp_value = dhw_temp_param.get("value")
        if dhw_temp_value is not None and dhw_temp_value != 999.0:
            for description in DHW_SELECTS:
                if coordinator.get_param(description.param_id) is not None:
                    entities.append(EconetNextSelect(coordinator, description))
                else:
                    _LOGGER.debug(
                        "Skipping DHW select %s - parameter %s not found",
                        description.key,
                        description.param_id,
                    )

    # Add circuit select entities if circuit is active
    for circuit_num, circuit in CIRCUITS.items():
        # Check if circuit is active
        active = coordinator.get_param(circuit.active_param)
        if active and active.get("value") > 0:
            # Create select entities for this circuit
            for description in CIRCUIT_SELECTS:
                # Map the select key to the appropriate circuit parameter
                param_id = _get_circuit_param_id(circuit, description.key)
                if param_id and coordinator.get_param(param_id) is not None:
                    # Create a copy of the description with the actual param_id
                    circuit_desc = EconetSelectEntityDescription(
                        key=description.key,
                        param_id=param_id,
                        device_type=description.device_type,
                        entity_category=description.entity_category,
                        icon=description.icon,
                        options=description.options,
                        value_map=description.value_map,
                        reverse_map=description.reverse_map,
                    )
                    entities.append(EconetNextSelect(coordinator, circuit_desc, device_id=f"circuit_{circuit_num}"))
                else:
                    _LOGGER.debug(
                        "Skipping Circuit %s select %s - parameter %s not found",
                        circuit_num,
                        description.key,
                        param_id,
                    )

    async_add_entities(entities)


def _get_circuit_param_id(circuit, select_key: str) -> str | None:
    """Get the parameter ID for a circuit select entity based on its key."""
    mapping = {
        "circuit_type": circuit.type_settings_param,
    }
    return mapping.get(select_key)


class EconetNextSelect(EconetNextEntity, SelectEntity):
    """Representation of an ecoNET Next select entity."""

    def __init__(
        self,
        coordinator: EconetNextCoordinator,
        description: EconetSelectEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the select entity."""
        # Use provided device_id or determine from device_type
        if device_id is None and description.device_type != "controller":
            device_id = description.device_type

        super().__init__(coordinator, description.param_id, device_id)

        self._description = description
        self._attr_translation_key = description.key
        self._attr_options = description.options

        # Apply description attributes
        if description.entity_category:
            self._attr_entity_category = description.entity_category
        if description.icon:
            self._attr_icon = description.icon

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        value = self._get_param_value()
        if value is None:
            return None

        # Map the raw value to an option string
        return self._description.value_map.get(int(value))

    async def async_select_option(self, option: str) -> None:
        """Set the selected option."""
        # Map the option string to raw value
        raw_value = self._description.reverse_map.get(option)
        if raw_value is None:
            _LOGGER.error("Unknown option %s for %s", option, self._description.key)
            return

        _LOGGER.debug(
            "Setting %s (param %s) to %s (raw: %d)",
            self._description.key,
            self._description.param_id,
            option,
            raw_value,
        )
        await self.coordinator.async_set_param(self._description.param_id, raw_value)
