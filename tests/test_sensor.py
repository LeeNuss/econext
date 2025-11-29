"""Tests for the econet_next sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature

from econet_next.const import CONTROLLER_SENSORS, DeviceType, EconetSensorEntityDescription
from econet_next.coordinator import EconetNextCoordinator
from econet_next.sensor import EconetNextSensor


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
        from econet_next.const import FLAP_VALVE_STATE_MAPPING, FLAP_VALVE_STATE_OPTIONS

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
        from econet_next.const import CIRCUIT_SENSORS

        assert len(CIRCUIT_SENSORS) == 3
        keys = {s.key for s in CIRCUIT_SENSORS}
        assert keys == {"thermostat_temp", "calc_temp", "room_temp_setpoint"}

        # All should be temperature sensors
        for sensor in CIRCUIT_SENSORS:
            assert sensor.device_class == SensorDeviceClass.TEMPERATURE
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
