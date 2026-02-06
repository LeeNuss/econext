"""Tests for the econet_next climate platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import PRESET_COMFORT, PRESET_ECO
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant

from custom_components.econet_next.climate import CIRCUITS, CircuitClimate, CircuitWorkState, async_setup_entry
from custom_components.econet_next.coordinator import EconetNextCoordinator


@pytest.fixture(autouse=True)
def patch_frame_helper():
    """Patch Home Assistant frame helper for all tests."""
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    return hass


@pytest.fixture
def mock_api() -> MagicMock:
    """Create a mock API."""
    api = MagicMock()
    api.async_set_param = AsyncMock()
    return api


@pytest.fixture
def coordinator(mock_hass: MagicMock, mock_api: MagicMock, all_params_parsed: dict) -> EconetNextCoordinator:
    """Create a coordinator with data."""
    coordinator = EconetNextCoordinator(mock_hass, mock_api)
    coordinator.data = all_params_parsed
    coordinator.async_set_param = AsyncMock()
    return coordinator


class TestCircuitConfiguration:
    """Test circuit configuration constants."""

    def test_all_circuits_defined(self) -> None:
        """Test all 7 circuits are defined."""
        assert len(CIRCUITS) == 7
        assert set(CIRCUITS.keys()) == {1, 2, 3, 4, 5, 6, 7}

    def test_circuit_2_parameters(self) -> None:
        """Test Circuit 2 (UFH) has correct parameter IDs."""
        circuit = CIRCUITS[2]
        assert circuit.active_param == "329"  # Circuit2active
        assert circuit.name_param == "328"  # Circuit2name
        assert circuit.work_state_param == "286"  # Circuit2WorkState
        assert circuit.thermostat_param == "327"  # Circuit2thermostatTemp
        assert circuit.comfort_param == "288"  # Circuit2ComfortTemp
        assert circuit.eco_param == "289"  # Circuit2EcoTemp


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_creates_all_circuits_in_fixture(
        self, mock_hass: MagicMock, coordinator: EconetNextCoordinator
    ) -> None:
        """Test only active circuits create climate entities from fixture data."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_hass.data = {"econet_next": {"test_entry": {"coordinator": coordinator}}}

        entities_added = []

        def mock_add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

        # Only Circuit 2 is active in fixture (value=1)
        assert len(entities_added) == 1
        assert entities_added[0]._circuit_num == 2

    @pytest.mark.asyncio
    async def test_setup_skips_inactive_circuits(
        self, mock_hass: MagicMock, coordinator: EconetNextCoordinator
    ) -> None:
        """Test circuits with active param value=0 are skipped."""
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        mock_hass.data = {"econet_next": {"test_entry": {"coordinator": coordinator}}}

        # Activate Circuit 1 by setting its active param to 1
        coordinator.data["279"]["value"] = 1

        entities_added = []

        def mock_add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

        # Both Circuit 1 and Circuit 2 should be created
        circuit_nums = {e._circuit_num for e in entities_added}
        assert circuit_nums == {1, 2}
        assert len(entities_added) == 2


class TestCircuitClimate:
    """Test CircuitClimate entity."""

    @pytest.fixture
    def circuit_2_entity(self, coordinator: EconetNextCoordinator) -> CircuitClimate:
        """Create Circuit 2 climate entity."""
        circuit = CIRCUITS[2]
        return CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

    def test_entity_initialization(self, circuit_2_entity: CircuitClimate) -> None:
        """Test climate entity initialization."""
        assert circuit_2_entity._circuit_num == 2
        assert circuit_2_entity._attr_temperature_unit == UnitOfTemperature.CELSIUS
        assert circuit_2_entity._attr_translation_key == "circuit"

    def test_entity_name_from_controller(self, circuit_2_entity: CircuitClimate) -> None:
        """Test entity uses custom name from controller."""
        # From fixture, Circuit2name = "UFH "
        assert circuit_2_entity._attr_name == "UFH"  # Stripped

    def test_supported_features(self, circuit_2_entity: CircuitClimate) -> None:
        """Test entity has correct supported features based on HVAC mode."""
        # Fixture has HEAT_COOL mode, so should support TARGET_TEMPERATURE_RANGE
        expected = ClimateEntityFeature.TARGET_TEMPERATURE_RANGE | ClimateEntityFeature.PRESET_MODE
        assert circuit_2_entity.supported_features == expected

    def test_hvac_modes(self, circuit_2_entity: CircuitClimate) -> None:
        """Test entity has correct HVAC modes based on settings."""
        # From fixture, Circuit2Settings (param 281) should have heating and cooling enabled
        # Test expects OFF, HEAT, COOL, and HEAT_COOL modes (no AUTO - that's now a preset)
        modes = circuit_2_entity.hvac_modes
        assert HVACMode.OFF in modes
        assert HVACMode.HEAT in modes
        # AUTO is no longer an HVAC mode - use SCHEDULE preset instead
        assert HVACMode.AUTO not in modes

    def test_preset_modes(self, circuit_2_entity: CircuitClimate) -> None:
        """Test entity has correct preset modes."""
        from custom_components.econet_next.climate import PRESET_SCHEDULE

        assert circuit_2_entity._attr_preset_modes == [PRESET_ECO, PRESET_COMFORT, PRESET_SCHEDULE]

    def test_temperature_limits(self, circuit_2_entity: CircuitClimate) -> None:
        """Test entity has correct temperature limits."""
        assert circuit_2_entity._attr_min_temp == 10.0
        assert circuit_2_entity._attr_max_temp == 35.0
        assert circuit_2_entity._attr_target_temperature_step == 0.5

    def test_current_temperature(self, circuit_2_entity: CircuitClimate) -> None:
        """Test current temperature from thermostat."""
        # From fixture, Circuit2thermostatTemp = 19.93
        assert circuit_2_entity.current_temperature == 19.93

    def test_current_temperature_invalid(self, coordinator: EconetNextCoordinator) -> None:
        """Test current temperature returns None for invalid value."""
        # Modify fixture to have invalid temp
        coordinator.data["327"]["value"] = 999.0

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.current_temperature is None

    def test_hvac_mode_off(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC mode when circuit is off."""
        # Set work state to 0 (off)
        coordinator.data["286"]["value"] = 0

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.hvac_mode == HVACMode.OFF

    def test_hvac_mode_heat_eco(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC mode when circuit is in eco mode with only heating enabled."""
        # Set work state to 1 (eco)
        coordinator.data["286"]["value"] = 1
        # Set heating enabled (bit 20 = 0), cooling disabled (bit 17 = 0)
        coordinator.data["281"]["value"] = 0

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.hvac_mode == HVACMode.HEAT

    def test_hvac_mode_heat_comfort(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC mode when circuit is in comfort mode with only heating enabled."""
        # Set work state to 2 (comfort)
        coordinator.data["286"]["value"] = 2
        # Set heating enabled (bit 20 = 0), cooling disabled (bit 17 = 0)
        coordinator.data["281"]["value"] = 0

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.hvac_mode == HVACMode.HEAT

    def test_hvac_mode_schedule(self, circuit_2_entity: CircuitClimate) -> None:
        """Test HVAC mode when circuit is in schedule mode."""
        # From fixture, Circuit2WorkState = 3 (schedule/auto)
        # HVAC mode is determined by heating/cooling enable bits, not work state
        # Fixture has both heating and cooling enabled, so should return HEAT_COOL
        assert circuit_2_entity.hvac_mode == HVACMode.HEAT_COOL

    def test_preset_mode_eco(self, coordinator: EconetNextCoordinator) -> None:
        """Test preset mode when in eco."""
        coordinator.data["286"]["value"] = CircuitWorkState.ECO

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.preset_mode == PRESET_ECO

    def test_preset_mode_comfort(self, coordinator: EconetNextCoordinator) -> None:
        """Test preset mode when in comfort."""
        coordinator.data["286"]["value"] = CircuitWorkState.COMFORT

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.preset_mode == PRESET_COMFORT

    def test_preset_mode_schedule(self, circuit_2_entity: CircuitClimate) -> None:
        """Test preset mode returns SCHEDULE when in schedule/auto mode."""
        from custom_components.econet_next.climate import PRESET_SCHEDULE

        # From fixture: Circuit2WorkState = 3 (schedule/auto)
        # Should return PRESET_SCHEDULE
        assert circuit_2_entity.preset_mode == PRESET_SCHEDULE

    def test_target_temperature_comfort(self, coordinator: EconetNextCoordinator) -> None:
        """Test target temperature in comfort mode."""
        coordinator.data["286"]["value"] = CircuitWorkState.COMFORT

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        # From fixture, Circuit2ComfortTemp = 21.0
        assert entity.target_temperature == 21.0

    def test_target_temperature_eco(self, coordinator: EconetNextCoordinator) -> None:
        """Test target temperature in eco mode."""
        coordinator.data["286"]["value"] = CircuitWorkState.ECO

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        # From fixture, Circuit2EcoTemp = 17.5
        assert entity.target_temperature == 17.5

    def test_target_temperature_auto(self, circuit_2_entity: CircuitClimate) -> None:
        """Test target temperature shows active setpoint in auto mode."""
        # From fixture: Circuit2WorkState = 3 (auto), room_temp_setpoint (92) = 21.0, comfort (288) = 21.0
        # Setpoint matches comfort, so should show comfort temperature
        assert circuit_2_entity.target_temperature == 21.0

    def test_hvac_action_off(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC action when circuit is off."""
        # Set work state to 0 (off)
        coordinator.data["286"]["value"] = 0

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.hvac_action == HVACAction.OFF

    def test_hvac_action_heating(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC action when actively heating."""
        coordinator.data["286"]["value"] = CircuitWorkState.COMFORT
        coordinator.data["327"]["value"] = 18.0  # Current temp
        coordinator.data["288"]["value"] = 21.0  # Comfort temp (target)

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        # 18.0 < 21.0 - 0.5 = true, so HEATING
        assert entity.hvac_action == HVACAction.HEATING

    def test_hvac_action_idle(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC action when at target temperature."""
        coordinator.data["286"]["value"] = CircuitWorkState.COMFORT
        coordinator.data["327"]["value"] = 21.0  # Current temp
        coordinator.data["288"]["value"] = 21.0  # Comfort temp (target)

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        # 21.0 < 21.0 - 0.5 = false, so IDLE
        assert entity.hvac_action == HVACAction.IDLE

    @pytest.mark.asyncio
    async def test_set_hvac_mode_off(
        self, circuit_2_entity: CircuitClimate, coordinator: EconetNextCoordinator
    ) -> None:
        """Test setting HVAC mode to OFF."""
        await circuit_2_entity.async_set_hvac_mode(HVACMode.OFF)

        coordinator.async_set_param.assert_called_once_with("286", CircuitWorkState.OFF)

    @pytest.mark.asyncio
    async def test_set_hvac_mode_heat(
        self, circuit_2_entity: CircuitClimate, coordinator: EconetNextCoordinator
    ) -> None:
        """Test setting HVAC mode to HEAT updates heating/cooling enable bits."""
        # Circuit is already on in fixture, so should only update settings
        await circuit_2_entity.async_set_hvac_mode(HVACMode.HEAT)

        # Should set bit 20=0 (heating on), bit 17=0 (cooling off)
        # Current settings value from fixture would be updated
        coordinator.async_set_param.assert_called()
        call_args = coordinator.async_set_param.call_args
        assert call_args[0][0] == "281"  # settings param
        # Verify heating enabled (bit 20 = 0) and cooling disabled (bit 17 = 0)
        settings_value = call_args[0][1]
        assert ((settings_value >> 20) & 1) == 0  # Heating ON
        assert ((settings_value >> 17) & 1) == 0  # Cooling OFF

    # Note: The tests for remembering presets when switching HVAC modes were removed
    # because HVAC modes (HEAT/COOL/HEAT_COOL) now only control heating/cooling enable bits,
    # not the work state. Presets (ECO/COMFORT/SCHEDULE) are controlled separately via
    # async_set_preset_mode.

    @pytest.mark.asyncio
    async def test_set_preset_mode_eco(
        self, circuit_2_entity: CircuitClimate, coordinator: EconetNextCoordinator
    ) -> None:
        """Test setting preset mode to ECO."""
        await circuit_2_entity.async_set_preset_mode(PRESET_ECO)

        coordinator.async_set_param.assert_called_once_with("286", CircuitWorkState.ECO)

    @pytest.mark.asyncio
    async def test_set_preset_mode_comfort(
        self, circuit_2_entity: CircuitClimate, coordinator: EconetNextCoordinator
    ) -> None:
        """Test setting preset mode to COMFORT."""
        await circuit_2_entity.async_set_preset_mode(PRESET_COMFORT)

        coordinator.async_set_param.assert_called_once_with("286", CircuitWorkState.COMFORT)

    @pytest.mark.asyncio
    async def test_set_preset_mode_schedule(
        self, circuit_2_entity: CircuitClimate, coordinator: EconetNextCoordinator
    ) -> None:
        """Test setting preset mode to SCHEDULE."""
        from custom_components.econet_next.climate import PRESET_SCHEDULE

        await circuit_2_entity.async_set_preset_mode(PRESET_SCHEDULE)

        coordinator.async_set_param.assert_called_once_with("286", CircuitWorkState.AUTO)

    @pytest.mark.asyncio
    async def test_set_temperature_comfort(self, coordinator: EconetNextCoordinator) -> None:
        """Test setting temperature in comfort mode with HEAT only."""
        coordinator.data["286"]["value"] = CircuitWorkState.COMFORT
        # Set to HEAT mode only (heating enabled, cooling disabled)
        coordinator.data["281"]["value"] = 0  # bit 20=0 (heat on), bit 17=0 (cool off)

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        await entity.async_set_temperature(**{ATTR_TEMPERATURE: 22.5})

        coordinator.async_set_param.assert_called_once_with("288", 22.5)

    @pytest.mark.asyncio
    async def test_set_temperature_eco(self, coordinator: EconetNextCoordinator) -> None:
        """Test setting temperature in eco mode with HEAT only."""
        coordinator.data["286"]["value"] = CircuitWorkState.ECO
        # Set to HEAT mode only (heating enabled, cooling disabled)
        coordinator.data["281"]["value"] = 0  # bit 20=0 (heat on), bit 17=0 (cool off)

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        await entity.async_set_temperature(**{ATTR_TEMPERATURE: 18.5})

        coordinator.async_set_param.assert_called_once_with("289", 18.5)

    def test_preset_mode_schedule_detects_eco(self, coordinator: EconetNextCoordinator) -> None:
        """Test that SCHEDULE mode updates _last_preset when setpoint matches ECO temp."""
        from custom_components.econet_next.climate import PRESET_SCHEDULE

        coordinator.data["286"]["value"] = CircuitWorkState.AUTO
        coordinator.data["289"]["value"] = 19.0  # Eco temp
        coordinator.data["288"]["value"] = 22.0  # Comfort temp
        coordinator.data["92"]["value"] = 19.0  # Room temp setpoint matches eco

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        # Should return SCHEDULE preset
        assert entity.preset_mode == PRESET_SCHEDULE
        # But _last_preset should be updated to ECO for temperature adjustments
        assert entity._last_preset == PRESET_ECO

    def test_preset_mode_schedule_detects_comfort(self, coordinator: EconetNextCoordinator) -> None:
        """Test that SCHEDULE mode updates _last_preset when setpoint matches COMFORT temp."""
        from custom_components.econet_next.climate import PRESET_SCHEDULE

        coordinator.data["286"]["value"] = CircuitWorkState.AUTO
        coordinator.data["289"]["value"] = 19.0  # Eco temp
        coordinator.data["288"]["value"] = 22.0  # Comfort temp
        coordinator.data["92"]["value"] = 22.0  # Room temp setpoint matches comfort

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        # Should return SCHEDULE preset
        assert entity.preset_mode == PRESET_SCHEDULE
        # But _last_preset should be updated to COMFORT for temperature adjustments
        assert entity._last_preset == PRESET_COMFORT

    def test_target_temperature_auto_shows_eco(self, coordinator: EconetNextCoordinator) -> None:
        """Test target temperature in AUTO mode shows ECO temp when setpoint matches."""
        coordinator.data["286"]["value"] = CircuitWorkState.AUTO
        coordinator.data["289"]["value"] = 19.0  # Eco temp
        coordinator.data["288"]["value"] = 22.0  # Comfort temp
        coordinator.data["92"]["value"] = 19.0  # Room temp setpoint matches eco

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.target_temperature == 19.0

    def test_target_temperature_auto_shows_comfort(self, coordinator: EconetNextCoordinator) -> None:
        """Test target temperature in AUTO mode shows COMFORT temp when setpoint matches."""
        coordinator.data["286"]["value"] = CircuitWorkState.AUTO
        coordinator.data["289"]["value"] = 19.0  # Eco temp
        coordinator.data["288"]["value"] = 22.0  # Comfort temp
        coordinator.data["92"]["value"] = 22.0  # Room temp setpoint matches comfort

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        assert entity.target_temperature == 22.0

    @pytest.mark.asyncio
    async def test_set_temperature_auto_mode_eco(self, coordinator: EconetNextCoordinator) -> None:
        """Test setting temperature in AUTO mode when currently in ECO."""
        coordinator.data["286"]["value"] = CircuitWorkState.AUTO
        coordinator.data["289"]["value"] = 19.0  # Eco temp
        coordinator.data["288"]["value"] = 22.0  # Comfort temp
        coordinator.data["92"]["value"] = 19.0  # Room temp setpoint matches eco
        # Set to HEAT mode only (heating enabled, cooling disabled)
        coordinator.data["281"]["value"] = 0  # bit 20=0 (heat on), bit 17=0 (cool off)

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        await entity.async_set_temperature(**{ATTR_TEMPERATURE: 20.0})

        # Should set ECO temp (param 289)
        coordinator.async_set_param.assert_called_once_with("289", 20.0)

    @pytest.mark.asyncio
    async def test_set_temperature_auto_mode_comfort(self, coordinator: EconetNextCoordinator) -> None:
        """Test setting temperature in AUTO mode when currently in COMFORT."""
        coordinator.data["286"]["value"] = CircuitWorkState.AUTO
        coordinator.data["289"]["value"] = 19.0  # Eco temp
        coordinator.data["288"]["value"] = 22.0  # Comfort temp
        coordinator.data["92"]["value"] = 22.0  # Room temp setpoint matches comfort
        # Set to HEAT mode only (heating enabled, cooling disabled)
        coordinator.data["281"]["value"] = 0  # bit 20=0 (heat on), bit 17=0 (cool off)

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        await entity.async_set_temperature(**{ATTR_TEMPERATURE: 23.0})

        # Should set COMFORT temp (param 288)
        coordinator.async_set_param.assert_called_once_with("288", 23.0)

    def test_unique_id(self, circuit_2_entity: CircuitClimate) -> None:
        """Test climate entity unique_id generation."""
        # UID from fixture is "2L7SDPN6KQ38CIH2401K01U", device_id is "circuit_2", work_state_param is "286"
        assert circuit_2_entity._attr_unique_id == "2L7SDPN6KQ38CIH2401K01U_circuit_2_286"

    def test_device_info(self, circuit_2_entity: CircuitClimate) -> None:
        """Test climate entity device info."""
        device_info = circuit_2_entity.device_info

        # Should be part of circuit_2 device, not controller
        assert ("econet_next", "2L7SDPN6KQ38CIH2401K01U_circuit_2") in device_info["identifiers"]
        assert device_info["name"] == "UFH"
        assert device_info["manufacturer"] == "Plum"
        assert device_info["model"] == "Circuit 2"
        # Should have parent (controller)
        assert device_info["via_device"] == ("econet_next", "2L7SDPN6KQ38CIH2401K01U")


class TestOperatingModeHVACModes:
    """Test HVAC modes based on operating mode and circuit settings."""

    def test_hvac_modes_winter_mode_heating_enabled(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC modes in winter mode with heating enabled."""
        # Set operating mode to winter (2)
        coordinator.data["162"]["value"] = 2
        # Circuit2Settings: heating enabled (bit 20 = 0), cooling disabled (bit 17 = 0)
        coordinator.data["281"]["value"] = 0

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        modes = entity.hvac_modes
        assert HVACMode.OFF in modes
        # AUTO is now a preset (SCHEDULE), not an HVAC mode
        # assert HVACMode.AUTO in modes  # Removed - AUTO is now PRESET_SCHEDULE
        assert HVACMode.HEAT in modes
        assert HVACMode.COOL not in modes
        assert HVACMode.HEAT_COOL not in modes

    def test_hvac_modes_summer_mode_cooling_enabled(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC modes in summer mode with cooling enabled."""
        # Set operating mode to summer (1)
        coordinator.data["162"]["value"] = 1
        # Circuit2Settings: heating disabled (bit 20 = 1), cooling enabled (bit 17 = 1)
        coordinator.data["281"]["value"] = (1 << 20) | (1 << 17)

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        modes = entity.hvac_modes
        assert HVACMode.OFF in modes
        # AUTO is now a preset (SCHEDULE), not an HVAC mode
        # assert HVACMode.AUTO in modes  # Removed - AUTO is now PRESET_SCHEDULE
        assert HVACMode.COOL in modes
        assert HVACMode.HEAT not in modes
        assert HVACMode.HEAT_COOL not in modes

    def test_hvac_modes_auto_mode_both_enabled(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC modes in auto mode with both heating and cooling enabled."""
        # Set operating mode to auto (3)
        coordinator.data["162"]["value"] = 3
        # Circuit2Settings: heating enabled (bit 20 = 0), cooling enabled (bit 17 = 1)
        coordinator.data["281"]["value"] = 1 << 17

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        modes = entity.hvac_modes
        assert HVACMode.OFF in modes
        # AUTO is now a preset (SCHEDULE), not an HVAC mode
        # assert HVACMode.AUTO in modes  # Removed - AUTO is now PRESET_SCHEDULE
        assert HVACMode.HEAT_COOL in modes
        assert HVACMode.HEAT in modes
        assert HVACMode.COOL in modes

    def test_hvac_modes_auto_mode_only_heating(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC modes in auto mode with only heating enabled."""
        # Set operating mode to auto (3)
        coordinator.data["162"]["value"] = 3
        # Circuit2Settings: heating enabled (bit 20 = 0), cooling disabled (bit 17 = 0)
        coordinator.data["281"]["value"] = 0

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        modes = entity.hvac_modes
        assert HVACMode.OFF in modes
        # AUTO is now a preset (SCHEDULE), not an HVAC mode
        # assert HVACMode.AUTO in modes  # Removed - AUTO is now PRESET_SCHEDULE
        assert HVACMode.HEAT in modes
        assert HVACMode.COOL not in modes
        assert HVACMode.HEAT_COOL not in modes

    def test_hvac_modes_auto_mode_only_cooling(self, coordinator: EconetNextCoordinator) -> None:
        """Test HVAC modes in auto mode with only cooling enabled."""
        # Set operating mode to auto (3)
        coordinator.data["162"]["value"] = 3
        # Circuit2Settings: heating disabled (bit 20 = 1), cooling enabled (bit 17 = 1)
        coordinator.data["281"]["value"] = (1 << 20) | (1 << 17)

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        modes = entity.hvac_modes
        assert HVACMode.OFF in modes
        # AUTO is now a preset (SCHEDULE), not an HVAC mode
        # assert HVACMode.AUTO in modes  # Removed - AUTO is now PRESET_SCHEDULE
        assert HVACMode.COOL in modes
        assert HVACMode.HEAT not in modes
        assert HVACMode.HEAT_COOL not in modes

    def test_hvac_modes_winter_cooling_enabled_ignored(self, coordinator: EconetNextCoordinator) -> None:
        """Test that cooling is not available in winter mode even if enabled in settings."""
        # Set operating mode to winter (2)
        coordinator.data["162"]["value"] = 2
        # Circuit2Settings: both heating and cooling enabled
        coordinator.data["281"]["value"] = 1 << 17

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        modes = entity.hvac_modes
        assert HVACMode.OFF in modes
        # AUTO is now a preset (SCHEDULE), not an HVAC mode
        # assert HVACMode.AUTO in modes  # Removed - AUTO is now PRESET_SCHEDULE
        assert HVACMode.HEAT in modes
        # Cooling should not be available in winter mode
        assert HVACMode.COOL not in modes
        assert HVACMode.HEAT_COOL not in modes

    def test_hvac_modes_summer_heating_enabled_ignored(self, coordinator: EconetNextCoordinator) -> None:
        """Test that heating is not available in summer mode even if enabled in settings."""
        # Set operating mode to summer (1)
        coordinator.data["162"]["value"] = 1
        # Circuit2Settings: both heating and cooling enabled
        coordinator.data["281"]["value"] = 1 << 17

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        modes = entity.hvac_modes
        assert HVACMode.OFF in modes
        # AUTO is now a preset (SCHEDULE), not an HVAC mode
        # assert HVACMode.AUTO in modes  # Removed - AUTO is now PRESET_SCHEDULE
        assert HVACMode.COOL in modes
        # Heating should not be available in summer mode
        assert HVACMode.HEAT not in modes
        assert HVACMode.HEAT_COOL not in modes

    def test_hvac_modes_no_operating_mode_defaults_auto(self, coordinator: EconetNextCoordinator) -> None:
        """Test that when operating mode is not available, system defaults to auto behavior."""
        # Remove operating mode parameter
        del coordinator.data["162"]
        # Circuit2Settings: both heating and cooling enabled
        coordinator.data["281"]["value"] = 1 << 17

        circuit = CIRCUITS[2]
        entity = CircuitClimate(
            coordinator,
            circuit_num=2,
            name_param=circuit.name_param,
            work_state_param=circuit.work_state_param,
            settings_param=circuit.settings_param,
            thermostat_param=circuit.thermostat_param,
            comfort_param=circuit.comfort_param,
            eco_param=circuit.eco_param,
            room_temp_setpoint_param=circuit.room_temp_setpoint_param,
        )

        modes = entity.hvac_modes
        assert HVACMode.OFF in modes
        # AUTO is now a preset (SCHEDULE), not an HVAC mode
        # assert HVACMode.AUTO in modes  # Removed - AUTO is now PRESET_SCHEDULE
        # Should behave like auto mode
        assert HVACMode.HEAT_COOL in modes
        assert HVACMode.HEAT in modes
        assert HVACMode.COOL in modes
