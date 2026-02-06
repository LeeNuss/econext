"""Tests for heat pump entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.econet_next.button import EconetNextButton
from custom_components.econet_next.const import (
    HEATPUMP_BUTTONS,
    HEATPUMP_NUMBERS,
    HEATPUMP_SELECTS,
    HEATPUMP_SENSORS,
)
from custom_components.econet_next.coordinator import EconetNextCoordinator
from custom_components.econet_next.number import EconetNextNumber
from custom_components.econet_next.select import EconetNextSelect
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
    api = MagicMock()
    api.async_set_param = AsyncMock(return_value=True)
    return api


@pytest.fixture
def coordinator(mock_hass: MagicMock, mock_api: MagicMock, all_params_parsed: dict) -> EconetNextCoordinator:
    """Create a coordinator with data."""
    coordinator = EconetNextCoordinator(mock_hass, mock_api)
    coordinator.data = all_params_parsed
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_set_param = AsyncMock(return_value=True)
    return coordinator


class TestHeatPumpSensors:
    """Test heat pump sensor definitions."""

    def test_all_sensors_have_required_fields(self):
        """Test that all heat pump sensors have required fields."""
        for sensor in HEATPUMP_SENSORS:
            assert sensor.key
            assert sensor.param_id
            assert sensor.device_type == "heatpump"

    def test_system_pressure_sensor(self, coordinator):
        """Test system pressure sensor."""
        sensor_desc = next(s for s in HEATPUMP_SENSORS if s.key == "system_pressure")
        sensor = EconetNextSensor(coordinator, sensor_desc, device_id="heatpump")

        assert sensor.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1208"
        assert sensor.native_value == 2.5
        assert sensor.native_unit_of_measurement == "bar"
        assert sensor.device_class == "pressure"
        assert sensor.state_class == "measurement"

    def test_pump_speed_sensor(self, coordinator):
        """Test pump speed sensor."""
        sensor_desc = next(s for s in HEATPUMP_SENSORS if s.key == "pump_speed")
        sensor = EconetNextSensor(coordinator, sensor_desc, device_id="heatpump")

        assert sensor.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1209"
        assert sensor.native_value == 91
        assert sensor.native_unit_of_measurement == "%"
        assert sensor.state_class == "measurement"

    def test_compressor_frequency_sensor(self, coordinator):
        """Test compressor frequency sensor."""
        sensor_desc = next(s for s in HEATPUMP_SENSORS if s.key == "compressor_frequency")
        sensor = EconetNextSensor(coordinator, sensor_desc, device_id="heatpump")

        assert sensor.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1365"
        assert sensor.native_value == 32
        assert sensor.native_unit_of_measurement == "Hz"
        assert sensor.state_class == "measurement"


class TestHeatPumpNumbers:
    """Test heat pump number definitions."""

    def test_all_numbers_have_required_fields(self):
        """Test that all heat pump numbers have required fields."""
        for number in HEATPUMP_NUMBERS:
            assert number.key
            assert number.param_id
            assert number.device_type == "heatpump"
            assert number.native_min_value is not None
            assert number.native_max_value is not None

    def test_purge_pwm_speed_number(self, coordinator):
        """Test purge PWM speed number."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "purge_pwm_speed")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        assert number.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1370"
        assert number.native_value == 90
        assert number.native_unit_of_measurement == "%"
        assert number.native_min_value == 1
        assert number.native_max_value == 100
        assert number.native_step == 1

    def test_standby_pump_speed_number(self, coordinator):
        """Test standby pump speed number."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "standby_pump_speed")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        assert number.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1439"
        assert number.native_value == 35
        assert number.native_unit_of_measurement == "%"
        assert number.native_min_value == 0
        assert number.native_max_value == 100

    def test_min_pump_speed_number(self, coordinator):
        """Test min pump speed number."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "min_pump_speed")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        assert number.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1440"
        assert number.native_value == 45
        assert number.native_unit_of_measurement == "%"

    def test_max_pump_speed_number(self, coordinator):
        """Test max pump speed number."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "max_pump_speed")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        assert number.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1441"
        assert number.native_value == 100
        assert number.native_unit_of_measurement == "%"

    def test_fan_speed_0_number(self, coordinator):
        """Test fan speed 0 number."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "fan_speed_0")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        assert number.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1443"
        assert number.native_value == 350
        assert number.native_unit_of_measurement == "RPM"
        assert number.native_min_value == 0
        assert number.native_max_value == 1000
        assert number.native_step == 10

    def test_fan_speed_1_number(self, coordinator):
        """Test fan speed 1 number."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "fan_speed_1")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        assert number.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1444"
        assert number.native_value == 400
        assert number.native_unit_of_measurement == "RPM"

    def test_fan_speed_2_number(self, coordinator):
        """Test fan speed 2 number."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "fan_speed_2")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        assert number.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1445"
        assert number.native_value == 450
        assert number.native_unit_of_measurement == "RPM"

    def test_fan_speed_3_number(self, coordinator):
        """Test fan speed 3 number."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "fan_speed_3")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        assert number.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1446"
        assert number.native_value == 550
        assert number.native_unit_of_measurement == "RPM"

    @pytest.mark.asyncio
    async def test_set_purge_pwm_speed(self, coordinator):
        """Test setting purge PWM speed."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "purge_pwm_speed")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        await number.async_set_native_value(75)
        coordinator.async_set_param.assert_called_once_with("1370", 75)

    @pytest.mark.asyncio
    async def test_set_fan_speed_0(self, coordinator):
        """Test setting fan speed 0."""
        number_desc = next(n for n in HEATPUMP_NUMBERS if n.key == "fan_speed_0")
        number = EconetNextNumber(coordinator, number_desc, device_id="heatpump")

        await number.async_set_native_value(500)
        coordinator.async_set_param.assert_called_once_with("1443", 500)


class TestHeatPumpSelects:
    """Test heat pump select definitions."""

    def test_all_selects_have_required_fields(self):
        """Test that all heat pump selects have required fields."""
        for select in HEATPUMP_SELECTS:
            assert select.key
            assert select.param_id
            assert select.device_type == "heatpump"
            assert select.options
            assert select.value_map
            assert select.reverse_map

    def test_work_mode_select(self, coordinator):
        """Test work mode select."""
        select_desc = next(s for s in HEATPUMP_SELECTS if s.key == "work_mode")
        select = EconetNextSelect(coordinator, select_desc, device_id="heatpump")

        assert select.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1133"
        assert select.current_option == "schedule"
        assert "off" in select.options
        assert "on" in select.options
        assert "schedule" in select.options

    def test_silent_mode_level_select(self, coordinator):
        """Test silent mode level select."""
        select_desc = next(s for s in HEATPUMP_SELECTS if s.key == "silent_mode_level")
        select = EconetNextSelect(coordinator, select_desc, device_id="heatpump")

        assert select.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1385"
        assert select.current_option == "level_1"
        assert "level_1" in select.options
        assert "level_2" in select.options

    def test_silent_mode_schedule_select(self, coordinator):
        """Test silent mode schedule select."""
        select_desc = next(s for s in HEATPUMP_SELECTS if s.key == "silent_mode_schedule")
        select = EconetNextSelect(coordinator, select_desc, device_id="heatpump")

        assert select.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1386"
        assert select.current_option == "schedule"
        assert "off" in select.options
        assert "schedule" in select.options

    @pytest.mark.asyncio
    async def test_set_work_mode(self, coordinator):
        """Test setting work mode."""
        select_desc = next(s for s in HEATPUMP_SELECTS if s.key == "work_mode")
        select = EconetNextSelect(coordinator, select_desc, device_id="heatpump")

        await select.async_select_option("on")
        coordinator.async_set_param.assert_called_once_with("1133", 1)

    @pytest.mark.asyncio
    async def test_set_silent_mode_level(self, coordinator):
        """Test setting silent mode level."""
        select_desc = next(s for s in HEATPUMP_SELECTS if s.key == "silent_mode_level")
        select = EconetNextSelect(coordinator, select_desc, device_id="heatpump")

        await select.async_select_option("level_2")
        coordinator.async_set_param.assert_called_once_with("1385", 2)


class TestHeatPumpButtons:
    """Test heat pump button definitions."""

    def test_all_buttons_have_required_fields(self):
        """Test that all heat pump buttons have required fields."""
        for button in HEATPUMP_BUTTONS:
            assert button.key
            assert button.param_id
            assert button.device_type == "heatpump"

    def test_reboot_button(self, coordinator):
        """Test reboot button."""
        button_desc = next(b for b in HEATPUMP_BUTTONS if b.key == "reboot")
        button = EconetNextButton(coordinator, button_desc, device_id="heatpump")

        assert button.unique_id == "2L7SDPN6KQ38CIH2401K01U_heatpump_1369"
        assert button.entity_category == "config"

    @pytest.mark.asyncio
    async def test_press_reboot_button(self, coordinator):
        """Test pressing reboot button."""
        button_desc = next(b for b in HEATPUMP_BUTTONS if b.key == "reboot")
        button = EconetNextButton(coordinator, button_desc, device_id="heatpump")

        await button.async_press()
        coordinator.async_set_param.assert_called_once_with("1369", 1)


class TestHeatPumpDeviceInfo:
    """Test heat pump device info."""

    def test_heatpump_device_info(self, coordinator):
        """Test that heat pump entities have correct device info."""
        sensor_desc = next(s for s in HEATPUMP_SENSORS if s.key == "system_pressure")
        sensor = EconetNextSensor(coordinator, sensor_desc, device_id="heatpump")

        device_info = sensor.device_info
        assert device_info["identifiers"] == {("econet_next", "2L7SDPN6KQ38CIH2401K01U_heatpump")}
        assert device_info["name"] == "Heat Pump"
        assert device_info["manufacturer"] == "Plum"
        assert device_info["via_device"] == ("econet_next", "2L7SDPN6KQ38CIH2401K01U")
