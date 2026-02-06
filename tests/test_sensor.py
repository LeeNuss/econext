"""Tests for the econet_next sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature

from custom_components.econet_next.const import CONTROLLER_SENSORS, DeviceType, EconetSensorEntityDescription
from custom_components.econet_next.coordinator import EconetNextCoordinator
from custom_components.econet_next.sensor import EconetNextSensor


@pytest.fixture(autouse=True)
def patch_frame_helper():
    """Patch Home Assistant frame helper for all tests."""
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    return hass


@pytest.fixture
def mock_api() -> MagicMock:
    """Create a mock API."""
    return MagicMock()


@pytest.fixture
def coordinator(mock_hass: MagicMock, mock_api: MagicMock, all_params_parsed: dict) -> EconetNextCoordinator:
    """Create a coordinator with data."""
    coordinator = EconetNextCoordinator(mock_hass, mock_api)
    coordinator.data = all_params_parsed
    return coordinator


class TestControllerSensorsDefinition:
    """Test that controller sensor definitions are correct."""

    def test_all_sensors_have_required_fields(self) -> None:
        """Test all sensors have required key and param_id."""
        for sensor in CONTROLLER_SENSORS:
            assert sensor.key, "Sensor must have a key"
            assert sensor.param_id, "Sensor must have a param_id"

    def test_outdoor_temperature_sensor_config(self) -> None:
        """Test outdoor temperature sensor has correct configuration."""
        outdoor_temp = next(s for s in CONTROLLER_SENSORS if s.key == "outdoor_temperature")

        assert outdoor_temp.param_id == "68"
        assert outdoor_temp.device_class == SensorDeviceClass.TEMPERATURE
        assert outdoor_temp.state_class == SensorStateClass.MEASUREMENT
        assert outdoor_temp.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert outdoor_temp.precision == 1

    def test_wifi_signal_sensor_config(self) -> None:
        """Test WiFi signal sensor has correct configuration."""
        wifi_signal = next(s for s in CONTROLLER_SENSORS if s.key == "wifi_signal_strength")

        assert wifi_signal.param_id == "380"
        assert wifi_signal.device_class is None  # % is not valid for SIGNAL_STRENGTH
        assert wifi_signal.native_unit_of_measurement == PERCENTAGE
        assert wifi_signal.entity_category == EntityCategory.DIAGNOSTIC

    def test_diagnostic_sensors_have_entity_category(self) -> None:
        """Test diagnostic sensors have correct entity category."""
        diagnostic_keys = [
            "software_version",
            "hardware_version",
            "uid",
            "device_name",
            "compilation_date",
            "reset_counter",
            "wifi_ssid",
            "wifi_signal_strength",
            "wifi_ip_address",
            "lan_ip_address",
        ]

        for key in diagnostic_keys:
            sensor = next(s for s in CONTROLLER_SENSORS if s.key == key)
            assert sensor.entity_category == EntityCategory.DIAGNOSTIC, f"{key} should be diagnostic"


class TestEconetNextSensor:
    """Test the EconetNextSensor class."""

    def test_sensor_initialization(self, coordinator: EconetNextCoordinator) -> None:
        """Test sensor initialization."""
        description = EconetSensorEntityDescription(
            key="test_sensor",
            param_id="68",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        )

        sensor = EconetNextSensor(coordinator, description)

        assert sensor._attr_translation_key == "test_sensor"
        assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS

    def test_sensor_unique_id(self, coordinator: EconetNextCoordinator) -> None:
        """Test sensor unique_id generation."""
        description = EconetSensorEntityDescription(
            key="test_sensor",
            param_id="68",
        )

        sensor = EconetNextSensor(coordinator, description)

        # UID from fixture is "2L7SDPN6KQ38CIH2401K01U"
        assert sensor._attr_unique_id == "2L7SDPN6KQ38CIH2401K01U_68"

    def test_sensor_native_value(self, coordinator: EconetNextCoordinator) -> None:
        """Test sensor returns correct native value."""
        description = EconetSensorEntityDescription(
            key="outdoor_temperature",
            param_id="68",
        )

        sensor = EconetNextSensor(coordinator, description)
        value = sensor.native_value

        # From fixture, param 68 (TempWthr) = 10.0
        assert value == 10.0

    def test_sensor_native_value_with_precision(self, coordinator: EconetNextCoordinator) -> None:
        """Test sensor applies precision rounding."""
        description = EconetSensorEntityDescription(
            key="outdoor_temperature",
            param_id="68",
            precision=0,
        )

        sensor = EconetNextSensor(coordinator, description)
        value = sensor.native_value

        # 10.0 rounded to 0 decimal places = 10
        assert value == 10

    def test_sensor_string_value(self, coordinator: EconetNextCoordinator) -> None:
        """Test sensor handles string values."""
        description = EconetSensorEntityDescription(
            key="software_version",
            param_id="0",
        )

        sensor = EconetNextSensor(coordinator, description)
        value = sensor.native_value

        # From fixture, param 0 (PS) = "S024.25"
        assert value == "S024.25"

    def test_sensor_device_info_controller(self, coordinator: EconetNextCoordinator) -> None:
        """Test sensor device info for controller."""
        description = EconetSensorEntityDescription(
            key="test_sensor",
            param_id="68",
            device_type=DeviceType.CONTROLLER,
        )

        sensor = EconetNextSensor(coordinator, description)
        device_info = sensor.device_info

        assert ("econet_next", "2L7SDPN6KQ38CIH2401K01U") in device_info["identifiers"]
        assert device_info["name"] == "ecoMAX360i"
        assert device_info["manufacturer"] == "Plum"

    def test_sensor_availability_valid(self, coordinator: EconetNextCoordinator) -> None:
        """Test sensor is available when data is valid."""
        coordinator.last_update_success = True

        description = EconetSensorEntityDescription(
            key="outdoor_temperature",
            param_id="68",
            device_class=SensorDeviceClass.TEMPERATURE,
        )

        sensor = EconetNextSensor(coordinator, description)

        assert sensor.available is True

    def test_sensor_availability_missing_param(self, coordinator: EconetNextCoordinator) -> None:
        """Test sensor is unavailable when param is missing."""
        coordinator.last_update_success = True

        description = EconetSensorEntityDescription(
            key="test_sensor",
            param_id="99999",  # Non-existent param
        )

        sensor = EconetNextSensor(coordinator, description)

        assert sensor.available is False

    def test_temperature_sensor_invalid_value(self, coordinator: EconetNextCoordinator) -> None:
        """Test temperature sensor treats 999.0 as invalid."""
        coordinator.last_update_success = True
        # Modify fixture data to have invalid temp
        coordinator.data["68"] = {"value": 999.0, "name": "TempWthr", "info": 23}

        description = EconetSensorEntityDescription(
            key="outdoor_temperature",
            param_id="68",
            device_class=SensorDeviceClass.TEMPERATURE,
        )

        sensor = EconetNextSensor(coordinator, description)

        assert sensor.available is False


class TestEnumSensor:
    """Test enum sensor functionality."""

    def test_flap_valve_enum_value(self, coordinator: EconetNextCoordinator) -> None:
        """Test flap valve sensor returns mapped enum value."""
        from custom_components.econet_next.const import FLAP_VALVE_STATE_MAPPING, FLAP_VALVE_STATE_OPTIONS

        description = EconetSensorEntityDescription(
            key="flap_valve_state",
            param_id="83",
            device_class=SensorDeviceClass.ENUM,
            options=FLAP_VALVE_STATE_OPTIONS,
            value_map=FLAP_VALVE_STATE_MAPPING,
        )

        sensor = EconetNextSensor(coordinator, description)

        # From fixture, param 83 = 0 which maps to "ch"
        assert sensor.native_value == "ch"
        assert sensor._attr_options == ["ch", "dhw"]


class TestSensorEntityCategory:
    """Test sensor entity categories."""

    def test_diagnostic_sensor_has_category(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor has correct entity category."""
        description = EconetSensorEntityDescription(
            key="software_version",
            param_id="0",
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextSensor(coordinator, description)

        assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC

    def test_measurement_sensor_no_category(self, coordinator: EconetNextCoordinator) -> None:
        """Test measurement sensor has no entity category."""
        description = EconetSensorEntityDescription(
            key="outdoor_temperature",
            param_id="68",
        )

        sensor = EconetNextSensor(coordinator, description)

        assert not hasattr(sensor, "_attr_entity_category") or sensor._attr_entity_category is None


class TestCircuitSensors:
    """Test circuit sensor functionality."""

    def test_circuit_sensor_definitions(self) -> None:
        """Test circuit sensor definitions are correct."""
        from custom_components.econet_next.const import CIRCUIT_SENSORS

        assert len(CIRCUIT_SENSORS) == 4
        keys = {s.key for s in CIRCUIT_SENSORS}
        assert keys == {"thermostat_temp", "calc_temp", "room_temp_setpoint", "active_preset_mode"}

        # Temperature sensors should have correct attributes
        temp_sensors = [s for s in CIRCUIT_SENSORS if s.device_class == SensorDeviceClass.TEMPERATURE]
        assert len(temp_sensors) == 3
        for sensor in temp_sensors:
            assert sensor.state_class == SensorStateClass.MEASUREMENT
            assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
            assert sensor.precision == 1
            assert sensor.device_type == DeviceType.CIRCUIT

    def test_circuit_thermostat_temp_sensor(self, coordinator: EconetNextCoordinator) -> None:
        """Test circuit thermostat temperature sensor."""
        description = EconetSensorEntityDescription(
            key="thermostat_temp",
            param_id="327",  # Circuit2thermostatTemp
            device_type=DeviceType.CIRCUIT,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:thermometer",
            precision=1,
        )

        sensor = EconetNextSensor(coordinator, description, device_id="circuit_2")

        # From fixture, param 327 = 19.93, rounded to 19.9 with precision=1
        assert sensor.native_value == 19.9
        assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE
        assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor._device_id == "circuit_2"

    def test_circuit_calc_temp_sensor(self, coordinator: EconetNextCoordinator) -> None:
        """Test circuit calculated temperature sensor."""
        description = EconetSensorEntityDescription(
            key="calc_temp",
            param_id="287",  # Circuit2CalcTemp
            device_type=DeviceType.CIRCUIT,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:thermometer-auto",
            precision=1,
        )

        sensor = EconetNextSensor(coordinator, description, device_id="circuit_2")

        # From fixture, param 287 = 35.92, rounded to 35.9 with precision=1
        assert sensor.native_value == 35.9
        assert sensor._attr_icon == "mdi:thermometer-auto"

    def test_circuit_room_temp_setpoint_sensor(self, coordinator: EconetNextCoordinator) -> None:
        """Test circuit room temperature setpoint sensor."""
        description = EconetSensorEntityDescription(
            key="room_temp_setpoint",
            param_id="92",  # Circuit2_romTempSet
            device_type=DeviceType.CIRCUIT,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:target",
            precision=1,
        )

        sensor = EconetNextSensor(coordinator, description, device_id="circuit_2")

        # From fixture, param 92 = 21.0
        assert sensor.native_value == 21.0
        assert sensor._attr_icon == "mdi:target"

    def test_circuit_sensor_invalid_temp(self, coordinator: EconetNextCoordinator) -> None:
        """Test circuit sensor handles invalid temperature (999.0)."""
        coordinator.last_update_success = True
        coordinator.data["327"] = {"value": 999.0, "name": "Circuit2thermostatTemp", "info": 23}

        description = EconetSensorEntityDescription(
            key="thermostat_temp",
            param_id="327",
            device_type=DeviceType.CIRCUIT,
            device_class=SensorDeviceClass.TEMPERATURE,
        )

        sensor = EconetNextSensor(coordinator, description, device_id="circuit_2")

        # 999.0 should be treated as unavailable
        assert sensor.available is False

    def test_circuit_sensor_with_device_id(self, coordinator: EconetNextCoordinator) -> None:
        """Test circuit sensor is associated with correct device."""
        description = EconetSensorEntityDescription(
            key="thermostat_temp",
            param_id="327",
            device_type=DeviceType.CIRCUIT,
        )

        # Create sensor for circuit 2
        sensor = EconetNextSensor(coordinator, description, device_id="circuit_2")

        assert sensor._device_id == "circuit_2"
        assert sensor._param_id == "327"

        # Unique ID should include circuit device_id
        assert "circuit_2" in sensor.unique_id


class TestScheduleBitfieldDecoder:
    """Test the decode_schedule_bitfield function."""

    def test_decode_empty_schedule(self) -> None:
        """Test decoding a schedule with no active periods."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        result = decode_schedule_bitfield(0, is_am=True)
        assert result == "No active periods"

        result = decode_schedule_bitfield(0, is_am=False)
        assert result == "No active periods"

    def test_decode_am_single_slot(self) -> None:
        """Test decoding a single 30-minute slot in AM period."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # Bit 0 = 00:00-00:30
        result = decode_schedule_bitfield(1, is_am=True)
        assert result == "00:00-00:30"

        # Bit 1 = 00:30-01:00
        result = decode_schedule_bitfield(2, is_am=True)
        assert result == "00:30-01:00"

        # Bit 8 = 04:00-04:30
        result = decode_schedule_bitfield(256, is_am=True)
        assert result == "04:00-04:30"

    def test_decode_pm_single_slot(self) -> None:
        """Test decoding a single 30-minute slot in PM period."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # Bit 0 in PM = 12:00-12:30
        result = decode_schedule_bitfield(1, is_am=False)
        assert result == "12:00-12:30"

        # Bit 1 in PM = 12:30-13:00
        result = decode_schedule_bitfield(2, is_am=False)
        assert result == "12:30-13:00"

        # Bit 8 in PM = 16:00-16:30
        result = decode_schedule_bitfield(256, is_am=False)
        assert result == "16:00-16:30"

    def test_decode_am_continuous_range(self) -> None:
        """Test decoding a continuous time range in AM period."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # Bits 8-10 set (256 + 512 + 1024 = 1792) = 04:00-05:30
        result = decode_schedule_bitfield(1792, is_am=True)
        assert result == "04:00-05:30"

        # Bits 0-3 set (1 + 2 + 4 + 8 = 15) = 00:00-02:00
        result = decode_schedule_bitfield(15, is_am=True)
        assert result == "00:00-02:00"

    def test_decode_pm_continuous_range(self) -> None:
        """Test decoding a continuous time range in PM period."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # Bits 8-10 set (1792) in PM = 16:00-17:30
        result = decode_schedule_bitfield(1792, is_am=False)
        assert result == "16:00-17:30"

        # Bits 10-15 set (64512) in PM = 17:00-20:00
        result = decode_schedule_bitfield(64512, is_am=False)
        assert result == "17:00-20:00"

    def test_decode_multiple_ranges(self) -> None:
        """Test decoding multiple separate time ranges."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # Bits 0-1 and 4-5 set (3 + 48 = 51) = 00:00-01:00, 02:00-03:00
        result = decode_schedule_bitfield(51, is_am=True)
        assert result == "00:00-01:00, 02:00-03:00"

        # Bits 2-3 and 8-9 set (12 + 768 = 780) = 01:00-02:00, 04:00-05:00
        result = decode_schedule_bitfield(780, is_am=True)
        assert result == "01:00-02:00, 04:00-05:00"

    def test_decode_all_slots_am(self) -> None:
        """Test decoding all 24 slots in AM period."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # All 24 bits set (2^24 - 1 = 16777215) = 00:00-12:00
        result = decode_schedule_bitfield(16777215, is_am=True)
        assert result == "00:00-12:00"

    def test_decode_all_slots_pm(self) -> None:
        """Test decoding all 24 slots in PM period."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # All 24 bits set (16777215) in PM = 12:00-24:00
        result = decode_schedule_bitfield(16777215, is_am=False)
        assert result == "12:00-24:00"

    def test_decode_last_slot_am(self) -> None:
        """Test decoding the last slot in AM period."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # Bit 23 (last slot) = 11:30-12:00
        result = decode_schedule_bitfield(8388608, is_am=True)
        assert result == "11:30-12:00"

    def test_decode_last_slot_pm(self) -> None:
        """Test decoding the last slot in PM period."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # Bit 23 in PM = 23:30-24:00
        result = decode_schedule_bitfield(8388608, is_am=False)
        assert result == "23:30-24:00"

    def test_decode_complex_pattern(self) -> None:
        """Test decoding a complex realistic pattern."""
        from custom_components.econet_next.sensor import decode_schedule_bitfield

        # Morning: 06:00-09:00 (bits 12-17 = 258048)
        # Evening: 17:00-22:00 (bits 34-43 would be in PM, but we only have 24 bits)
        # For AM: bits 12-17 = 06:00-09:00
        result = decode_schedule_bitfield(258048, is_am=True)
        assert result == "06:00-09:00"

        # For PM: bits 10-19 = 17:00-22:00
        result = decode_schedule_bitfield(1047552, is_am=False)
        assert result == "17:00-22:00"


class TestScheduleDiagnosticSensor:
    """Test the EconetNextScheduleDiagnosticSensor class (combines AM+PM)."""

    def test_diagnostic_sensor_combined_schedule(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor combining AM and PM schedules."""
        from custom_components.econet_next.sensor import EconetNextScheduleDiagnosticSensor

        # Set DHW Sunday AM schedule: bits 8-10 set (1792) = 04:00-05:30
        coordinator.data["120"] = {"id": 120, "value": 1792}
        # Set DHW Sunday PM schedule: bits 10-15 (64512) = 17:00-20:00
        coordinator.data["121"] = {"id": 121, "value": 64512}

        description = EconetSensorEntityDescription(
            key="hdw_schedule_sunday_decoded",
            param_id="120",
            param_id_am="120",
            param_id_pm="121",
            device_type=DeviceType.CONTROLLER,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextScheduleDiagnosticSensor(coordinator, description)
        assert sensor.native_value == "04:00-05:30, 17:00-20:00"

    def test_diagnostic_sensor_only_am_active(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor with only AM schedule active."""
        from custom_components.econet_next.sensor import EconetNextScheduleDiagnosticSensor

        # AM schedule active
        coordinator.data["120"] = {"id": 120, "value": 1792}
        # PM schedule empty
        coordinator.data["121"] = {"id": 121, "value": 0}

        description = EconetSensorEntityDescription(
            key="hdw_schedule_sunday_decoded",
            param_id="120",
            param_id_am="120",
            param_id_pm="121",
            device_type=DeviceType.CONTROLLER,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextScheduleDiagnosticSensor(coordinator, description)
        assert sensor.native_value == "04:00-05:30"

    def test_diagnostic_sensor_only_pm_active(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor with only PM schedule active."""
        from custom_components.econet_next.sensor import EconetNextScheduleDiagnosticSensor

        # AM schedule empty
        coordinator.data["120"] = {"id": 120, "value": 0}
        # PM schedule active
        coordinator.data["121"] = {"id": 121, "value": 64512}

        description = EconetSensorEntityDescription(
            key="hdw_schedule_sunday_decoded",
            param_id="120",
            param_id_am="120",
            param_id_pm="121",
            device_type=DeviceType.CONTROLLER,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextScheduleDiagnosticSensor(coordinator, description)
        assert sensor.native_value == "17:00-20:00"

    def test_diagnostic_sensor_no_active_periods(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor with no active periods in either AM or PM."""
        from custom_components.econet_next.sensor import EconetNextScheduleDiagnosticSensor

        # Both schedules empty
        coordinator.data["120"] = {"id": 120, "value": 0}
        coordinator.data["121"] = {"id": 121, "value": 0}

        description = EconetSensorEntityDescription(
            key="hdw_schedule_sunday_decoded",
            param_id="120",
            param_id_am="120",
            param_id_pm="121",
            device_type=DeviceType.CONTROLLER,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextScheduleDiagnosticSensor(coordinator, description)
        assert sensor.native_value == "No active periods"

    def test_diagnostic_sensor_none_value(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor returns None when param value is None."""
        from custom_components.econet_next.sensor import EconetNextScheduleDiagnosticSensor

        # Set AM value to None
        coordinator.data["120"] = {"id": 120, "value": None}
        coordinator.data["121"] = {"id": 121, "value": 0}

        description = EconetSensorEntityDescription(
            key="hdw_schedule_sunday_decoded",
            param_id="120",
            param_id_am="120",
            param_id_pm="121",
            device_type=DeviceType.CONTROLLER,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextScheduleDiagnosticSensor(coordinator, description)
        assert sensor.native_value is None

    def test_diagnostic_sensor_missing_am_param(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor returns None when AM param is missing."""
        from custom_components.econet_next.sensor import EconetNextScheduleDiagnosticSensor

        # Remove AM param from data
        if "120" in coordinator.data:
            del coordinator.data["120"]
        coordinator.data["121"] = {"id": 121, "value": 0}

        description = EconetSensorEntityDescription(
            key="hdw_schedule_sunday_decoded",
            param_id="120",
            param_id_am="120",
            param_id_pm="121",
            device_type=DeviceType.CONTROLLER,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextScheduleDiagnosticSensor(coordinator, description)
        assert sensor.native_value is None

    def test_diagnostic_sensor_missing_pm_param(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor returns None when PM param is missing."""
        from custom_components.econet_next.sensor import EconetNextScheduleDiagnosticSensor

        # Remove PM param from data
        coordinator.data["120"] = {"id": 120, "value": 0}
        if "121" in coordinator.data:
            del coordinator.data["121"]

        description = EconetSensorEntityDescription(
            key="hdw_schedule_sunday_decoded",
            param_id="120",
            param_id_am="120",
            param_id_pm="121",
            device_type=DeviceType.CONTROLLER,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextScheduleDiagnosticSensor(coordinator, description)
        assert sensor.native_value is None

    def test_diagnostic_sensor_all_day(self, coordinator: EconetNextCoordinator) -> None:
        """Test diagnostic sensor with all slots active (full day)."""
        from custom_components.econet_next.sensor import EconetNextScheduleDiagnosticSensor

        # All 24 bits set for both AM and PM (16777215)
        coordinator.data["120"] = {"id": 120, "value": 16777215}
        coordinator.data["121"] = {"id": 121, "value": 16777215}

        description = EconetSensorEntityDescription(
            key="hdw_schedule_sunday_decoded",
            param_id="120",
            param_id_am="120",
            param_id_pm="121",
            device_type=DeviceType.CONTROLLER,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        sensor = EconetNextScheduleDiagnosticSensor(coordinator, description)
        assert sensor.native_value == "00:00-12:00, 12:00-24:00"
