"""Sensor platform for ecoNET Next integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .climate import CIRCUITS
from .const import (
    CIRCUIT_SENSORS,
    CONTROLLER_SENSORS,
    DHW_SENSORS,
    DOMAIN,
    EconetSensorEntityDescription,
)
from .coordinator import EconetNextCoordinator
from .entity import EconetNextEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNET Next sensors from a config entry."""
    coordinator: EconetNextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[EconetNextSensor] = []

    # Add controller sensors
    for description in CONTROLLER_SENSORS:
        # Only add if parameter exists in data
        if coordinator.get_param(description.param_id) is not None:
            entities.append(EconetNextSensor(coordinator, description))
        else:
            _LOGGER.debug(
                "Skipping sensor %s - parameter %s not found",
                description.key,
                description.param_id,
            )

    # Add DHW sensors if DHW device should be created
    # DHW device is created if TempCWU (61) exists and is valid (not 999.0)
    dhw_temp_param = coordinator.get_param("61")
    if dhw_temp_param is not None:
        dhw_temp_value = dhw_temp_param.get("value")
        if dhw_temp_value is not None and dhw_temp_value != 999.0:
            for description in DHW_SENSORS:
                if coordinator.get_param(description.param_id) is not None:
                    entities.append(EconetNextSensor(coordinator, description))
                else:
                    _LOGGER.debug(
                        "Skipping DHW sensor %s - parameter %s not found",
                        description.key,
                        description.param_id,
                    )

    # Add circuit sensors if circuit is active
    for circuit_num, circuit in CIRCUITS.items():
        # Check if circuit is active
        active = coordinator.get_param(circuit.active_param)
        if active and active.get("value") > 0:
            # Create sensors for this circuit
            for description in CIRCUIT_SENSORS:
                # Map the sensor key to the appropriate circuit parameter
                param_id = _get_circuit_param_id(circuit, description.key)
                if param_id and coordinator.get_param(param_id) is not None:
                    # Create a copy of the description with the actual param_id and device_id
                    circuit_desc = EconetSensorEntityDescription(
                        key=description.key,
                        param_id=param_id,
                        device_type=description.device_type,
                        device_class=description.device_class,
                        state_class=description.state_class,
                        native_unit_of_measurement=description.native_unit_of_measurement,
                        entity_category=description.entity_category,
                        icon=description.icon,
                        precision=description.precision,
                        options=description.options,
                        value_map=description.value_map,
                    )
                    entities.append(EconetNextSensor(coordinator, circuit_desc, device_id=f"circuit_{circuit_num}"))
                else:
                    _LOGGER.debug(
                        "Skipping Circuit %s sensor %s - parameter %s not found",
                        circuit_num,
                        description.key,
                        param_id,
                    )

    async_add_entities(entities)


def _get_circuit_param_id(circuit, sensor_key: str) -> str | None:
    """Get the parameter ID for a circuit sensor based on its key."""
    mapping = {
        "thermostat_temp": circuit.thermostat_param,
        "calc_temp": circuit.calc_temp_param,
        "room_temp_setpoint": circuit.room_temp_setpoint_param,
    }
    return mapping.get(sensor_key)


class EconetNextSensor(EconetNextEntity, SensorEntity):
    """Representation of an ecoNET Next sensor."""

    def __init__(
        self,
        coordinator: EconetNextCoordinator,
        description: EconetSensorEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        # Use provided device_id or determine from device_type
        if device_id is None and description.device_type != "controller":
            device_id = description.device_type

        super().__init__(coordinator, description.param_id, device_id)

        self._description = description
        self._attr_translation_key = description.key

        # Apply description attributes
        if description.device_class:
            self._attr_device_class = description.device_class
        if description.state_class:
            self._attr_state_class = description.state_class
        if description.native_unit_of_measurement:
            self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        if description.entity_category:
            self._attr_entity_category = description.entity_category
        if description.icon:
            self._attr_icon = description.icon
        if description.options:
            self._attr_options = description.options

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self._get_param_value()

        if value is None:
            return None

        # Apply value mapping for enum sensors
        if self._description.value_map is not None:
            return self._description.value_map.get(int(value))

        # Apply precision if specified
        if self._description.precision is not None and isinstance(value, (int, float)):
            return round(value, self._description.precision)

        return value

    def _is_value_valid(self) -> bool:
        """Check if the parameter value is valid."""
        value = self._get_param_value()
        if value is None:
            return False

        # Temperature sensors: 999.0 means sensor disconnected
        if self._description.device_class == "temperature":
            return value != 999.0

        return True
