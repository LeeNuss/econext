"""Sensor platform for ecoNEXT integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .climate import CIRCUITS
from .const import (
    CIRCUIT_SCHEDULE_DIAGNOSTIC_SENSORS,
    CIRCUIT_SENSORS,
    CONTROLLER_SENSORS,
    DHW_SCHEDULE_DIAGNOSTIC_SENSORS,
    DHW_SENSORS,
    DOMAIN,
    EconextSensorEntityDescription,
    HEATPUMP_SCHEDULE_DIAGNOSTIC_SENSORS,
    HEATPUMP_SENSORS,
    SILENT_MODE_SCHEDULE_DIAGNOSTIC_SENSORS,
    get_alarm_name,
)
from .coordinator import EconextCoordinator
from .entity import EconextEntity

_LOGGER = logging.getLogger(__name__)


def decode_schedule_bitfield(value: int, is_am: bool = True) -> str:
    """
    Decode a schedule bitfield into human-readable time ranges.

    Args:
        value: uint32 bitfield where each bit = 30-minute slot
        is_am: True for AM schedule (00:00-11:30), False for PM (12:00-23:30)

    Returns:
        String like "06:00-09:30, 17:00-21:00" or "No active periods"
    """
    if value == 0:
        return "No active periods"

    ranges = []
    start_bit = None
    start_offset = 0 if is_am else 24  # PM schedules start at 12:00 (24 half-hours)

    for bit in range(24):  # 24 half-hour slots
        is_set = (value >> bit) & 1

        if is_set and start_bit is None:
            start_bit = bit
        elif not is_set and start_bit is not None:
            # End of range
            start_hour = (start_offset + start_bit) // 2
            start_min = ((start_offset + start_bit) % 2) * 30
            end_hour = (start_offset + bit) // 2
            end_min = ((start_offset + bit) % 2) * 30
            ranges.append(f"{start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}")
            start_bit = None

    # Handle range extending to end
    if start_bit is not None:
        start_hour = (start_offset + start_bit) // 2
        start_min = ((start_offset + start_bit) % 2) * 30
        end_hour = (start_offset + 24) // 2
        end_min = 0
        ranges.append(f"{start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}")

    return ", ".join(ranges)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNEXT sensors from a config entry."""
    coordinator: EconextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = []

    # Add controller sensors
    for description in CONTROLLER_SENSORS:
        # Only add if parameter exists in data
        if coordinator.get_param(description.param_id) is not None:
            entities.append(EconextSensor(coordinator, description))
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
                    entities.append(EconextSensor(coordinator, description))
                else:
                    _LOGGER.debug(
                        "Skipping DHW sensor %s - parameter %s not found",
                        description.key,
                        description.param_id,
                    )

            # Add DHW schedule diagnostic sensors
            for description in DHW_SCHEDULE_DIAGNOSTIC_SENSORS:
                # Check that both AM and PM params exist
                if (
                    coordinator.get_param(description.param_id_am) is not None
                    and coordinator.get_param(description.param_id_pm) is not None
                ):
                    entities.append(EconextScheduleDiagnosticSensor(coordinator, description))
                else:
                    _LOGGER.debug(
                        "Skipping DHW schedule diagnostic sensor %s - parameters %s/%s not found",
                        description.key,
                        description.param_id_am,
                        description.param_id_pm,
                    )

    # Add heat pump sensors if heat pump device should be created
    # Check if AxenWorkState parameter exists to determine if heat pump is present
    heatpump_param = coordinator.get_param("1133")
    if heatpump_param is not None:
        for description in HEATPUMP_SENSORS:
            if coordinator.get_param(description.param_id) is not None:
                entities.append(EconextSensor(coordinator, description, device_id="heatpump"))
            else:
                _LOGGER.debug(
                    "Skipping heat pump sensor %s - parameter %s not found",
                    description.key,
                    description.param_id,
                )

        # Add silent mode schedule diagnostic sensors
        for description in SILENT_MODE_SCHEDULE_DIAGNOSTIC_SENSORS:
            # Check that both AM and PM params exist
            if (
                coordinator.get_param(description.param_id_am) is not None
                and coordinator.get_param(description.param_id_pm) is not None
            ):
                entities.append(EconextScheduleDiagnosticSensor(coordinator, description, device_id="heatpump"))
            else:
                _LOGGER.debug(
                    "Skipping silent mode schedule diagnostic sensor %s - parameters %s/%s not found",
                    description.key,
                    description.param_id_am,
                    description.param_id_pm,
                )

        # Add heat pump schedule diagnostic sensors
        for description in HEATPUMP_SCHEDULE_DIAGNOSTIC_SENSORS:
            # Check that both AM and PM params exist
            if (
                coordinator.get_param(description.param_id_am) is not None
                and coordinator.get_param(description.param_id_pm) is not None
            ):
                entities.append(EconextScheduleDiagnosticSensor(coordinator, description, device_id="heatpump"))
            else:
                _LOGGER.debug(
                    "Skipping heat pump schedule diagnostic sensor %s - parameters %s/%s not found",
                    description.key,
                    description.param_id_am,
                    description.param_id_pm,
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
                    circuit_desc = EconextSensorEntityDescription(
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

                    # Use special sensor class for active_preset_mode
                    if description.key == "active_preset_mode":
                        # Also check that eco, comfort and setpoint params exist
                        if (
                            coordinator.get_param(circuit.eco_param) is not None
                            and coordinator.get_param(circuit.comfort_param) is not None
                            and coordinator.get_param(circuit.room_temp_setpoint_param) is not None
                        ):
                            entities.append(
                                EconextActiveScheduleModeSensor(
                                    coordinator,
                                    circuit_desc,
                                    circuit.eco_param,
                                    circuit.comfort_param,
                                    circuit.room_temp_setpoint_param,
                                    device_id=f"circuit_{circuit_num}",
                                )
                            )
                    else:
                        entities.append(EconextSensor(coordinator, circuit_desc, device_id=f"circuit_{circuit_num}"))
                else:
                    _LOGGER.debug(
                        "Skipping Circuit %s sensor %s - parameter %s not found",
                        circuit_num,
                        description.key,
                        param_id,
                    )

            # Add circuit schedule diagnostic sensors
            for description in CIRCUIT_SCHEDULE_DIAGNOSTIC_SENSORS:
                # Get AM and PM param IDs from circuit
                param_id_am, param_id_pm = _get_circuit_schedule_diagnostic_params(circuit, description.key)
                if (
                    param_id_am
                    and param_id_pm
                    and coordinator.get_param(param_id_am) is not None
                    and coordinator.get_param(param_id_pm) is not None
                ):
                    # Create a copy of the description with the actual param IDs
                    circuit_schedule_desc = EconextSensorEntityDescription(
                        key=description.key,
                        param_id=param_id_am,  # Use AM as primary
                        param_id_am=param_id_am,
                        param_id_pm=param_id_pm,
                        device_type=description.device_type,
                        icon=description.icon,
                        entity_category=description.entity_category,
                    )
                    entities.append(
                        EconextScheduleDiagnosticSensor(
                            coordinator, circuit_schedule_desc, device_id=f"circuit_{circuit_num}"
                        )
                    )
                else:
                    _LOGGER.debug(
                        "Skipping Circuit %s schedule diagnostic sensor %s - parameters %s/%s not found",
                        circuit_num,
                        description.key,
                        param_id_am,
                        param_id_pm,
                    )

    # Add alarm history sensor
    entities.append(EconextAlarmSensor(coordinator))

    async_add_entities(entities)


def _get_circuit_param_id(circuit, sensor_key: str) -> str | None:
    """Get the parameter ID for a circuit sensor based on its key."""
    mapping = {
        "thermostat_temp": circuit.thermostat_param,
        "calc_temp": circuit.calc_temp_param,
        "room_temp_setpoint": circuit.room_temp_setpoint_param,
        "active_preset_mode": circuit.eco_param,  # Uses eco as primary param for unique ID
    }
    return mapping.get(sensor_key)


def _get_circuit_schedule_diagnostic_params(circuit, sensor_key: str) -> tuple[str | None, str | None]:
    """Get the AM and PM parameter IDs for a circuit schedule diagnostic sensor based on its key."""
    mapping = {
        "schedule_sunday_decoded": (circuit.schedule_sunday_am, circuit.schedule_sunday_pm),
        "schedule_monday_decoded": (circuit.schedule_monday_am, circuit.schedule_monday_pm),
        "schedule_tuesday_decoded": (circuit.schedule_tuesday_am, circuit.schedule_tuesday_pm),
        "schedule_wednesday_decoded": (circuit.schedule_wednesday_am, circuit.schedule_wednesday_pm),
        "schedule_thursday_decoded": (circuit.schedule_thursday_am, circuit.schedule_thursday_pm),
        "schedule_friday_decoded": (circuit.schedule_friday_am, circuit.schedule_friday_pm),
        "schedule_saturday_decoded": (circuit.schedule_saturday_am, circuit.schedule_saturday_pm),
    }
    return mapping.get(sensor_key, (None, None))


class EconextSensor(EconextEntity, SensorEntity):
    """Representation of an ecoNEXT sensor."""

    def __init__(
        self,
        coordinator: EconextCoordinator,
        description: EconextSensorEntityDescription,
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


class EconextScheduleDiagnosticSensor(EconextSensor):
    """Sensor that decodes schedule bitfields into human-readable format.

    This sensor combines both AM and PM schedule periods into a single daily view.
    """

    def __init__(
        self,
        coordinator: EconextCoordinator,
        description: EconextSensorEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator, description, device_id)

    @property
    def native_value(self) -> str | None:
        """Return the decoded schedule as a string combining AM and PM periods."""
        # Get AM param value
        am_param = self.coordinator.get_param(self._description.param_id_am)
        pm_param = self.coordinator.get_param(self._description.param_id_pm)

        if am_param is None or pm_param is None:
            return None

        am_value = am_param.get("value")
        pm_value = pm_param.get("value")

        if am_value is None or pm_value is None:
            return None

        try:
            # Decode both AM and PM periods
            am_decoded = decode_schedule_bitfield(int(am_value), is_am=True)
            pm_decoded = decode_schedule_bitfield(int(pm_value), is_am=False)

            # Combine results
            if am_decoded == "No active periods" and pm_decoded == "No active periods":
                return "No active periods"
            elif am_decoded == "No active periods":
                return pm_decoded
            elif pm_decoded == "No active periods":
                return am_decoded
            else:
                return f"{am_decoded}, {pm_decoded}"
        except (ValueError, TypeError):
            return None


class EconextActiveScheduleModeSensor(EconextSensor):
    """Sensor that shows the active schedule mode (eco/comfort) for a circuit.

    Computes the active mode by comparing the room temperature setpoint
    to the eco and comfort temperature settings.
    """

    def __init__(
        self,
        coordinator: EconextCoordinator,
        description: EconextSensorEntityDescription,
        eco_param_id: str,
        comfort_param_id: str,
        setpoint_param_id: str,
        device_id: str | None = None,
    ) -> None:
        """Initialize the active schedule mode sensor."""
        super().__init__(coordinator, description, device_id)
        self._eco_param_id = eco_param_id
        self._comfort_param_id = comfort_param_id
        self._setpoint_param_id = setpoint_param_id

    @property
    def native_value(self) -> str | None:
        """Return the active schedule mode (eco or comfort).

        Compares the current room_temp_setpoint to eco_temp and comfort_temp
        to determine which mode the circuit is currently following.
        """
        # Get current room temperature setpoint (the target temp the system is using)
        setpoint_param = self.coordinator.get_param(self._setpoint_param_id)
        if not setpoint_param:
            return None

        setpoint = setpoint_param.get("value")
        if setpoint is None or setpoint == 999.0:
            return None

        # Get eco and comfort temperatures
        eco_param = self.coordinator.get_param(self._eco_param_id)
        comfort_param = self.coordinator.get_param(self._comfort_param_id)

        if not eco_param or not comfort_param:
            return None

        eco_temp = eco_param.get("value")
        comfort_temp = comfort_param.get("value")

        if eco_temp is None or comfort_temp is None:
            return None

        if eco_temp == 999.0 or comfort_temp == 999.0:
            return None

        try:
            setpoint_float = float(setpoint)
            eco_float = float(eco_temp)
            comfort_float = float(comfort_temp)

            # Compare setpoint to eco and comfort temps
            # If setpoint is closer to comfort, we're in comfort (day) mode
            # If setpoint is closer to eco, we're in eco (night) mode
            eco_diff = abs(setpoint_float - eco_float)
            comfort_diff = abs(setpoint_float - comfort_float)

            if comfort_diff < eco_diff:
                return "comfort"
            else:
                return "eco"
        except (ValueError, TypeError):
            return None


class EconextAlarmSensor(EconextEntity, SensorEntity):
    """Sensor showing the most recent alarm with history in attributes."""

    _attr_icon = "mdi:alert-circle-outline"
    _attr_translation_key = "last_alarm"

    def __init__(self, coordinator: EconextCoordinator) -> None:
        """Initialize the alarm sensor."""
        super().__init__(coordinator, "_alarms", None)
        uid = coordinator.get_device_uid()
        self._attr_unique_id = f"{uid}_last_alarm"

    @property
    def native_value(self) -> str | None:
        """Return description of the most recent alarm."""
        latest = self.coordinator.latest_alarm
        if latest is None:
            return "No alarms"
        return get_alarm_name(latest.get("code", 0))

    @property
    def extra_state_attributes(self) -> dict:
        """Return alarm details and history."""
        latest = self.coordinator.latest_alarm
        active = self.coordinator.active_alarms
        alarms = self.coordinator.alarms

        attrs: dict = {
            "active_alarm_count": len(active),
        }

        if latest:
            attrs["alarm_code"] = latest.get("code")
            attrs["from_date"] = latest.get("from_date")
            attrs["to_date"] = latest.get("to_date")

        # Include recent alarm history (last 10)
        attrs["alarm_history"] = [
            {
                "code": a.get("code"),
                "name": get_alarm_name(a.get("code", 0)),
                "from_date": a.get("from_date"),
                "to_date": a.get("to_date"),
            }
            for a in alarms[:10]
        ]

        return attrs

    def _is_value_valid(self) -> bool:
        """Alarm data is always valid if coordinator is updating."""
        return True
