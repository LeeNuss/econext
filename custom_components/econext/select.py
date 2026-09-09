"""Select platform for ecoNEXT integration."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .climate import CIRCUITS, is_circuit_enabled
from .const import (
    CIRCUIT_SELECTS,
    CONTROLLER_SELECTS,
    DHW_SELECTS,
    DOMAIN,
    EconextSelectEntityDescription,
    HEATPUMP_SELECTS,
)
from .coordinator import EconextCoordinator
from .entity import EconextEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNEXT select entities from a config entry."""
    coordinator: EconextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[EconextSelect] = []

    # Add controller select entities
    for description in CONTROLLER_SELECTS:
        # Only add if parameter exists in data
        if coordinator.get_param(description.param_id) is not None:
            entities.append(EconextSelect(coordinator, description))
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
                    entities.append(EconextSelect(coordinator, description))
                else:
                    _LOGGER.debug(
                        "Skipping DHW select %s - parameter %s not found",
                        description.key,
                        description.param_id,
                    )

    # Add heat pump select entities if heat pump device should be created
    # Check if AxenWorkState parameter exists to determine if heat pump is present
    heatpump_param = coordinator.get_param("1133")
    if heatpump_param is not None:
        for description in HEATPUMP_SELECTS:
            if coordinator.get_param(description.param_id) is not None:
                entities.append(EconextSelect(coordinator, description))
            else:
                _LOGGER.debug(
                    "Skipping heat pump select %s - parameter %s not found",
                    description.key,
                    description.param_id,
                )

    # Add circuit select entities for enabled circuits ("Circuit support" bit)
    for circuit_num, circuit in CIRCUITS.items():
        if is_circuit_enabled(coordinator, circuit):
            # Create select entities for this circuit
            for description in CIRCUIT_SELECTS:
                # Map the select key to the appropriate circuit parameter
                param_id = _get_circuit_param_id(circuit, description.key)
                if param_id and coordinator.get_param(param_id) is not None:
                    # Create a copy of the description with the actual param_id
                    circuit_desc = EconextSelectEntityDescription(
                        key=description.key,
                        param_id=param_id,
                        device_type=description.device_type,
                        entity_category=description.entity_category,
                        icon=description.icon,
                        options=description.options,
                        value_map=description.value_map,
                        reverse_map=description.reverse_map,
                        bit_position=description.bit_position,
                    )
                    entities.append(EconextSelect(coordinator, circuit_desc, device_id=f"circuit_{circuit_num}"))
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
        "regulation_method": circuit.settings_param,
    }
    return mapping.get(select_key)


class EconextSelect(EconextEntity, SelectEntity):
    """Representation of an ecoNEXT select entity."""

    def __init__(
        self,
        coordinator: EconextCoordinator,
        description: EconextSelectEntityDescription,
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

        raw_value = int(value)
        if self._description.bit_position is not None:
            raw_value = (raw_value >> self._description.bit_position) & 1

        return self._description.value_map.get(raw_value)

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
        if self._description.bit_position is not None:
            current_value = self._get_param_value()
            if current_value is None:
                _LOGGER.error(
                    "Cannot set %s because current value of param %s is unavailable",
                    self._description.key,
                    self._description.param_id,
                )
                return

            bit_mask = 1 << self._description.bit_position
            new_value = int(current_value) | bit_mask if raw_value else int(current_value) & ~bit_mask
            await self.coordinator.async_set_param(self._description.param_id, new_value)
            return

        await self.coordinator.async_set_param(self._description.param_id, raw_value)
