"""Tests for the econext number platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import UnitOfTemperature

from custom_components.econext.const import CONTROLLER_NUMBERS, EconextNumberEntityDescription
from custom_components.econext.coordinator import EconextCoordinator
from custom_components.econext.number import EconextNumber


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
def coordinator(mock_hass: MagicMock, mock_api: MagicMock, all_params_parsed: dict) -> EconextCoordinator:
    """Create a coordinator with data."""
    coordinator = EconextCoordinator(mock_hass, mock_api)
    coordinator.data = all_params_parsed
    coordinator.async_set_param = AsyncMock(return_value=True)
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


class TestControllerNumbersDefinition:
    """Test that controller number definitions are correct."""

    def test_all_numbers_have_required_fields(self) -> None:
        """Test all numbers have required key and param_id."""
        for number in CONTROLLER_NUMBERS:
            assert number.key, "Number must have a key"
            assert number.param_id, "Number must have a param_id"

    def test_summer_mode_on_config(self) -> None:
        """Test summer mode on number has correct configuration."""
        summer_on = next(n for n in CONTROLLER_NUMBERS if n.key == "summer_mode_on")

        assert summer_on.param_id == "702"
        assert summer_on.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        # Limits are read from allParams, these are just fallbacks
        assert summer_on.native_min_value == 22
        assert summer_on.native_max_value == 30

    def test_summer_mode_off_config(self) -> None:
        """Test summer mode off number has correct configuration."""
        summer_off = next(n for n in CONTROLLER_NUMBERS if n.key == "summer_mode_off")

        assert summer_off.param_id == "703"
        assert summer_off.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        # Limits are read from allParams, these are just fallbacks
        assert summer_off.native_min_value == 0
        assert summer_off.native_max_value == 24


class TestEconextNumber:
    """Test the EconextNumber class."""

    def test_number_initialization(self, coordinator: EconextCoordinator) -> None:
        """Test number initialization."""
        description = EconextNumberEntityDescription(
            key="test_number",
            param_id="702",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=10,
            native_max_value=30,
        )

        number = EconextNumber(coordinator, description)

        assert number._attr_translation_key == "test_number"
        assert number._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS

    def test_number_native_value(self, coordinator: EconextCoordinator) -> None:
        """Test number returns correct native value."""
        description = EconextNumberEntityDescription(
            key="summer_mode_on",
            param_id="702",
            native_min_value=22,
            native_max_value=30,
        )

        number = EconextNumber(coordinator, description)
        value = number.native_value

        # From fixture, param 702 (SummerOn) = 24
        assert value == 24.0

    def test_number_static_min_max_from_allparams(self, coordinator: EconextCoordinator) -> None:
        """Test number uses static minv/maxv from allParams."""
        # Param 703 has static minv=0, maxv=24 in allParams (no dynamic pointers)
        description = EconextNumberEntityDescription(
            key="summer_mode_off",
            param_id="703",
            native_min_value=999,  # Should be overridden by allParams
            native_max_value=999,  # Should be overridden by allParams
        )

        number = EconextNumber(coordinator, description)

        # Should read from allParams, not description
        assert number.native_min_value == 0.0  # From allParams minv
        assert number.native_max_value == 24.0  # From allParams maxvDP → param 702 value

    def test_number_dynamic_min_from_allparams(self, coordinator: EconextCoordinator) -> None:
        """Test number uses dynamic min from minvDP in allParams."""
        # Param 702 has minvDP=703 in allParams, which means min comes from param 703's value
        description = EconextNumberEntityDescription(
            key="summer_mode_on",
            param_id="702",
            native_min_value=999,  # Fallback (should not be used)
            native_max_value=999,
        )

        number = EconextNumber(coordinator, description)

        # From fixture: param 702 has minvDP=703, param 703 value=22
        assert number.native_min_value == 22.0

    def test_number_dynamic_max_from_allparams(self, coordinator: EconextCoordinator) -> None:
        """Test number uses dynamic max from maxvDP in allParams."""
        # Param 703 has maxvDP=702 in allParams, which means max comes from param 702's value
        description = EconextNumberEntityDescription(
            key="summer_mode_off",
            param_id="703",
            native_min_value=999,
            native_max_value=999,  # Fallback (should not be used)
        )

        number = EconextNumber(coordinator, description)

        # From fixture: param 703 has maxvDP=702, param 702 value=24
        assert number.native_max_value == 24.0

    def test_number_fallback_when_no_allparams(self, coordinator: EconextCoordinator) -> None:
        """Test number falls back to description limits when param not in allParams."""
        description = EconextNumberEntityDescription(
            key="test_number",
            param_id="99999",  # Non-existent param
            native_min_value=15,
            native_max_value=30,
        )

        number = EconextNumber(coordinator, description)

        # Should use fallback values from description
        assert number.native_min_value == 15
        assert number.native_max_value == 30

    @pytest.mark.asyncio
    async def test_set_native_value(self, coordinator: EconextCoordinator) -> None:
        """Test setting a number value."""
        description = EconextNumberEntityDescription(
            key="summer_mode_on",
            param_id="702",
            native_min_value=22,
            native_max_value=30,
        )

        number = EconextNumber(coordinator, description)
        await number.async_set_native_value(25.0)

        coordinator.async_set_param.assert_called_once_with("702", 25)


class TestCircuitNumbers:
    """Test circuit number functionality."""

    def test_circuit_number_definitions(self) -> None:
        """Test circuit number definitions are correct."""
        from custom_components.econext.const import CIRCUIT_NUMBERS, DeviceType

        assert len(CIRCUIT_NUMBERS) == 14
        keys = {n.key for n in CIRCUIT_NUMBERS}
        expected_keys = {
            "comfort_temp",
            "eco_temp",
            "hysteresis",
            "max_temp_radiator",
            "max_temp_heat",
            "fixed_temp",
            "temp_reduction",
            "heating_curve",
            "curve_shift",
            "curve_multiplier",
            "room_temp_correction",
            "min_setpoint_cooling",
            "max_setpoint_cooling",
            "cooling_fixed_temp",
        }
        assert keys == expected_keys

        # All should be circuit device type
        for number in CIRCUIT_NUMBERS:
            assert number.device_type == DeviceType.CIRCUIT

    def test_circuit_comfort_temp_number(self, coordinator: EconextCoordinator) -> None:
        """Test circuit comfort temperature number."""
        description = EconextNumberEntityDescription(
            key="comfort_temp",
            param_id="288",  # Circuit2ComfortTemp
            device_type="circuit",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:sun-thermometer",
            native_min_value=10.0,
            native_max_value=35.0,
            native_step=0.5,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")

        # From fixture, param 288 = 21.0
        assert number.native_value == 21.0
        assert number.native_min_value == 10.0
        assert number.native_max_value == 35.0
        assert number._attr_native_step == 0.5
        assert number._attr_icon == "mdi:sun-thermometer"
        assert number._device_id == "circuit_2"

    def test_circuit_eco_temp_number(self, coordinator: EconextCoordinator) -> None:
        """Test circuit eco temperature number."""
        description = EconextNumberEntityDescription(
            key="eco_temp",
            param_id="289",  # Circuit2EcoTemp
            device_type="circuit",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:leaf",
            native_min_value=10.0,
            native_max_value=35.0,
            native_step=0.5,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")

        # From fixture, param 289 = 17.5
        assert number.native_value == 17.5
        assert number._attr_icon == "mdi:leaf"

    def test_circuit_hysteresis_number(self, coordinator: EconextCoordinator) -> None:
        """Test circuit hysteresis number."""
        description = EconextNumberEntityDescription(
            key="hysteresis",
            param_id="290",  # Circuit2DownHist
            device_type="circuit",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:thermometer-lines",
            native_min_value=0.0,
            native_max_value=5.0,
            native_step=0.5,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")

        # From fixture, param 290 = 0.3
        assert number.native_value == 0.3
        assert number.native_min_value == 0.0
        assert number.native_max_value == 5.0

    def test_circuit_heating_curve_radiator_type(self, coordinator: EconextCoordinator) -> None:
        """Test circuit heating curve for radiator type (type=1)."""
        # Circuit 1 has type=1 (radiator), so heating_curve should use curve_radiator_param
        description = EconextNumberEntityDescription(
            key="heating_curve",
            param_id="273",  # Circuit1CurveRadiator (for type=1)
            device_type="circuit",
            icon="mdi:chart-line",
            native_min_value=0.0,
            native_max_value=4.0,
            native_step=0.1,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_1")

        # From fixture, param 273 = 0.5
        assert number.native_value == 0.5
        assert number._attr_icon == "mdi:chart-line"

    def test_circuit_heating_curve_ufh_type(self, coordinator: EconextCoordinator) -> None:
        """Test circuit heating curve for UFH type (type=2)."""
        # Circuit 2 has type=2 (UFH), so heating_curve should use curve_floor_param
        description = EconextNumberEntityDescription(
            key="heating_curve",
            param_id="324",  # Circuit2CurveFloor (for type=2)
            device_type="circuit",
            icon="mdi:chart-line",
            native_min_value=0.0,
            native_max_value=4.0,
            native_step=0.1,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")

        # From fixture, param 324 = 0.5
        assert number.native_value == 0.5
        assert number._attr_icon == "mdi:chart-line"

    def test_circuit_curve_shift_number(self, coordinator: EconextCoordinator) -> None:
        """Test circuit curve shift number."""
        description = EconextNumberEntityDescription(
            key="curve_shift",
            param_id="325",  # Circuit2Curveshift
            device_type="circuit",
            icon="mdi:arrow-up-down",
            native_min_value=-20,
            native_max_value=20,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")

        # From fixture, param 325 = 5
        assert number.native_value == 5.0

    @pytest.mark.asyncio
    async def test_circuit_set_comfort_temp(self, coordinator: EconextCoordinator) -> None:
        """Test setting circuit comfort temperature."""
        description = EconextNumberEntityDescription(
            key="comfort_temp",
            param_id="288",  # Circuit2ComfortTemp
            device_type="circuit",
            native_min_value=10.0,
            native_max_value=35.0,
            native_step=0.5,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")
        await number.async_set_native_value(22.5)

        coordinator.async_set_param.assert_called_once_with("288", 22.5)

    @pytest.mark.asyncio
    async def test_circuit_set_eco_temp(self, coordinator: EconextCoordinator) -> None:
        """Test setting circuit eco temperature."""
        description = EconextNumberEntityDescription(
            key="eco_temp",
            param_id="289",  # Circuit2EcoTemp
            device_type="circuit",
            native_min_value=10.0,
            native_max_value=35.0,
            native_step=0.5,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")
        await number.async_set_native_value(18.0)

        coordinator.async_set_param.assert_called_once_with("289", 18.0)

    def test_circuit_number_with_device_id(self, coordinator: EconextCoordinator) -> None:
        """Test circuit number is associated with correct device."""
        description = EconextNumberEntityDescription(
            key="comfort_temp",
            param_id="288",
            device_type="circuit",
        )

        # Create number for circuit 2
        number = EconextNumber(coordinator, description, device_id="circuit_2")

        assert number._device_id == "circuit_2"
        assert number._param_id == "288"

        # Unique ID should include circuit device_id
        assert "circuit_2" in number.unique_id

    def test_circuit_min_setpoint_cooling_number(self, coordinator: EconextCoordinator) -> None:
        """Test circuit minimum cooling setpoint number."""
        description = EconextNumberEntityDescription(
            key="min_setpoint_cooling",
            param_id="787",  # Circuit2MinSetPointCooling
            device_type="circuit",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:snowflake-thermometer",
            native_min_value=0,
            native_max_value=30,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")

        # From fixture, param 787 = 18
        assert number.native_value == 18.0
        assert number.native_min_value == 18.0  # From allParams minv
        assert number.native_max_value == 25.0  # From allParams maxv
        assert number._attr_icon == "mdi:snowflake-thermometer"
        assert number._device_id == "circuit_2"

    def test_circuit_max_setpoint_cooling_number(self, coordinator: EconextCoordinator) -> None:
        """Test circuit maximum cooling setpoint number."""
        description = EconextNumberEntityDescription(
            key="max_setpoint_cooling",
            param_id="788",  # Circuit2MaxSetPointCooling
            device_type="circuit",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:snowflake-thermometer",
            native_min_value=0,
            native_max_value=30,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")

        # From fixture, param 788 = 25
        assert number.native_value == 25.0
        assert number.native_min_value == 18.0  # From allParams minv
        assert number.native_max_value == 30.0  # From allParams maxv
        assert number._attr_icon == "mdi:snowflake-thermometer"

    def test_circuit_cooling_fixed_temp_number(self, coordinator: EconextCoordinator) -> None:
        """Test circuit cooling fixed temperature number."""
        description = EconextNumberEntityDescription(
            key="cooling_fixed_temp",
            param_id="789",  # Circuit2MixerCoolBaseTemp
            device_type="circuit",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:snowflake",
            native_min_value=0,
            native_max_value=30,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")

        # From fixture, param 789 = 18
        assert number.native_value == 18.0
        assert number.native_min_value == 18.0  # From allParams minv
        assert number.native_max_value == 25.0  # From allParams maxv
        assert number._attr_icon == "mdi:snowflake"

    @pytest.mark.asyncio
    async def test_set_cooling_setpoint(self, coordinator: EconextCoordinator) -> None:
        """Test setting circuit cooling setpoint."""
        description = EconextNumberEntityDescription(
            key="min_setpoint_cooling",
            param_id="787",  # Circuit2MinSetPointCooling
            device_type="circuit",
            native_min_value=0,
            native_max_value=30,
        )

        number = EconextNumber(coordinator, description, device_id="circuit_2")
        await number.async_set_native_value(20.0)

        coordinator.async_set_param.assert_called_once_with("787", 20)

    def test_schedule_number_fallback_invalid_api_range(self, coordinator: EconextCoordinator) -> None:
        """Test schedule number uses description values when API has invalid range (minv=maxv=0)."""
        # Param 120 (HDWSundayAM) has minv=0, maxv=0 in fixture (invalid range)
        description = EconextNumberEntityDescription(
            key="hdw_schedule_sunday_am",
            param_id="120",
            device_type="dhw",
            icon="mdi:calendar-clock",
            native_min_value=0,
            native_max_value=4294967295,
            native_step=1,
        )

        number = EconextNumber(coordinator, description, device_id="dhw")

        # Should fall back to description values since API has invalid range
        assert number.native_min_value == 0
        assert number.native_max_value == 4294967295
        # Value from fixture
        assert number.native_value == 1792
