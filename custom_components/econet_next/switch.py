"""Switch platform for ecoNET Next integration."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .climate import CIRCUITS
from .const import (
    CIRCUIT_SWITCHES,
    CONTROLLER_SWITCHES,
    DHW_SWITCHES,
    DOMAIN,
    EconetSwitchEntityDescription,
    HEATPUMP_SWITCHES,
)
from .coordinator import EconetNextCoordinator
from .entity import EconetNextEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNET Next switch entities from a config entry."""
    coordinator: EconetNextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[EconetNextSwitch] = []

    # Add controller switch entities
    for description in CONTROLLER_SWITCHES:
        # Only add if parameter exists in data
        if coordinator.get_param(description.param_id) is not None:
            entities.append(EconetNextSwitch(coordinator, description))
        else:
            _LOGGER.debug(
                "Skipping switch %s - parameter %s not found",
                description.key,
                description.param_id,
            )

    # Add DHW switch entities if DHW device should be created
    dhw_temp_param = coordinator.get_param("61")
    if dhw_temp_param is not None:
        dhw_temp_value = dhw_temp_param.get("value")
        if dhw_temp_value is not None and dhw_temp_value != 999.0:
            for description in DHW_SWITCHES:
                if coordinator.get_param(description.param_id) is not None:
                    entities.append(EconetNextSwitch(coordinator, description))
                else:
                    _LOGGER.debug(
                        "Skipping DHW switch %s - parameter %s not found",
                        description.key,
                        description.param_id,
                    )

    # Add heat pump switch entities if heat pump device should be created
    heatpump_param = coordinator.get_param("1133")
    if heatpump_param is not None:
        for description in HEATPUMP_SWITCHES:
            if coordinator.get_param(description.param_id) is not None:
                entities.append(EconetNextSwitch(coordinator, description, device_id="heatpump"))
            else:
                _LOGGER.debug(
                    "Skipping heat pump switch %s - parameter %s not found",
                    description.key,
                    description.param_id,
                )

    # Add circuit switch entities if circuit is active
    for circuit_num, circuit in CIRCUITS.items():
        active = coordinator.get_param(circuit.active_param)
        if active and active.get("value", 0) > 0:
            for description in CIRCUIT_SWITCHES:
                param_id = circuit.settings_param
                if param_id and coordinator.get_param(param_id) is not None:
                    # Create a copy of the description with the actual param_id
                    circuit_desc = EconetSwitchEntityDescription(
                        key=description.key,
                        param_id=param_id,
                        device_type=description.device_type,
                        entity_category=description.entity_category,
                        icon=description.icon,
                        bit_position=description.bit_position,
                        invert_logic=description.invert_logic,
                    )
                    entities.append(EconetNextSwitch(coordinator, circuit_desc, device_id=f"circuit_{circuit_num}"))
                else:
                    _LOGGER.debug(
                        "Skipping Circuit %s switch %s - parameter %s not found",
                        circuit_num,
                        description.key,
                        param_id,
                    )

    async_add_entities(entities)


class EconetNextSwitch(EconetNextEntity, SwitchEntity):
    """Representation of an ecoNET Next switch entity."""

    def __init__(
        self,
        coordinator: EconetNextCoordinator,
        description: EconetSwitchEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the switch entity."""
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

        # Override unique_id for bitmap switches to include the key
        # This ensures each bit position gets a unique ID
        if description.bit_position is not None:
            uid = coordinator.get_device_uid()
            if device_id:
                self._attr_unique_id = f"{uid}_{device_id}_{description.param_id}_{description.key}"
            else:
                self._attr_unique_id = f"{uid}_{description.param_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return True if the switch is on."""
        value = self._get_param_value()
        if value is None:
            return None

        # Handle bitmap-based switches
        if self._description.bit_position is not None:
            bit_value = (int(value) >> self._description.bit_position) & 1
            # Apply invert logic if needed
            if self._description.invert_logic:
                return bit_value == 0  # Bit 0 = ON
            return bit_value == 1  # Bit 1 = ON

        # Standard boolean switch: API uses 1 for on, 0 for off
        return bool(int(value))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        _LOGGER.debug(
            "Turning on %s (param %s)",
            self._description.key,
            self._description.param_id,
        )

        # Handle bitmap-based switches
        if self._description.bit_position is not None:
            current_value = int(self._get_param_value() or 0)
            bit_pos = self._description.bit_position

            if self._description.invert_logic:
                # Clear the bit (0 = ON)
                new_value = current_value & ~(1 << bit_pos)
            else:
                # Set the bit (1 = ON)
                new_value = current_value | (1 << bit_pos)

            await self.coordinator.async_set_param(self._description.param_id, new_value)
        else:
            # Standard boolean switch
            await self.coordinator.async_set_param(self._description.param_id, 1)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        _LOGGER.debug(
            "Turning off %s (param %s)",
            self._description.key,
            self._description.param_id,
        )

        # Handle bitmap-based switches
        if self._description.bit_position is not None:
            current_value = int(self._get_param_value() or 0)
            bit_pos = self._description.bit_position

            if self._description.invert_logic:
                # Set the bit (1 = OFF)
                new_value = current_value | (1 << bit_pos)
            else:
                # Clear the bit (0 = OFF)
                new_value = current_value & ~(1 << bit_pos)

            await self.coordinator.async_set_param(self._description.param_id, new_value)
        else:
            # Standard boolean switch
            await self.coordinator.async_set_param(self._description.param_id, 0)
