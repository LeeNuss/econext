"""Tests for the econet_next switch platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.econet_next.const import CONTROLLER_SWITCHES, EconetSwitchEntityDescription
from custom_components.econet_next.coordinator import EconetNextCoordinator
from custom_components.econet_next.switch import EconetNextSwitch


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
    return coordinator


class TestControllerSwitchesDefinition:
    """Test that controller switch definitions are correct."""

    def test_all_switches_have_required_fields(self) -> None:
        """Test all switches have required key and param_id."""
        for switch in CONTROLLER_SWITCHES:
            assert switch.key, "Switch must have a key"
            assert switch.param_id, "Switch must have a param_id"

    def test_cooling_support_config(self) -> None:
        """Test cooling support switch has correct configuration."""
        cooling_support = next(s for s in CONTROLLER_SWITCHES if s.key == "cooling_support")

        assert cooling_support.param_id == "485"
        assert cooling_support.icon == "mdi:snowflake"


class TestEconetNextSwitch:
    """Test the EconetNextSwitch class."""

    def test_switch_initialization(self, coordinator: EconetNextCoordinator) -> None:
        """Test switch initialization."""
        description = EconetSwitchEntityDescription(
            key="cooling_support",
            param_id="485",
            icon="mdi:snowflake",
        )

        switch = EconetNextSwitch(coordinator, description)

        assert switch._attr_translation_key == "cooling_support"
        assert switch._attr_icon == "mdi:snowflake"

    def test_switch_is_on_true(self, coordinator: EconetNextCoordinator) -> None:
        """Test switch returns True when value is 1."""
        coordinator.data["485"] = {"id": 485, "value": 1}

        description = EconetSwitchEntityDescription(
            key="cooling_support",
            param_id="485",
        )

        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is True

    def test_switch_is_on_false(self, coordinator: EconetNextCoordinator) -> None:
        """Test switch returns False when value is 0."""
        coordinator.data["485"] = {"id": 485, "value": 0}

        description = EconetSwitchEntityDescription(
            key="cooling_support",
            param_id="485",
        )

        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is False

    def test_switch_is_on_none(self, coordinator: EconetNextCoordinator) -> None:
        """Test switch returns None when value is None."""
        coordinator.data["485"] = {"id": 485, "value": None}

        description = EconetSwitchEntityDescription(
            key="cooling_support",
            param_id="485",
        )

        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is None

    def test_switch_is_on_missing_param(self, coordinator: EconetNextCoordinator) -> None:
        """Test switch returns None when param is missing."""
        # Use a param ID that doesn't exist in the fixture
        description = EconetSwitchEntityDescription(
            key="test_switch",
            param_id="99999",
        )

        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is None

    @pytest.mark.asyncio
    async def test_turn_on(self, coordinator: EconetNextCoordinator) -> None:
        """Test turning switch on."""
        description = EconetSwitchEntityDescription(
            key="cooling_support",
            param_id="485",
        )

        switch = EconetNextSwitch(coordinator, description)
        await switch.async_turn_on()

        coordinator.api.async_set_param.assert_called_once_with(485, 1)
        # Optimistic update should set the local value
        assert coordinator.data["485"]["value"] == 1

    @pytest.mark.asyncio
    async def test_turn_off(self, coordinator: EconetNextCoordinator) -> None:
        """Test turning switch off."""
        description = EconetSwitchEntityDescription(
            key="cooling_support",
            param_id="485",
        )

        switch = EconetNextSwitch(coordinator, description)
        await switch.async_turn_off()

        coordinator.api.async_set_param.assert_called_once_with(485, 0)
        # Optimistic update should set the local value
        assert coordinator.data["485"]["value"] == 0


class TestBitfieldSwitches:
    """Test bitmap-based switches (bit position switches)."""

    def test_bitfield_switch_is_on_bit_set(self, coordinator: EconetNextCoordinator) -> None:
        """Test bitfield switch returns True when bit is set."""
        # Set bit 10 in the value (1 << 10 = 1024)
        coordinator.data["231"] = {"id": 231, "value": 1024}

        description = EconetSwitchEntityDescription(
            key="pump_blockage",
            param_id="231",
            bit_position=10,
            invert_logic=False,
        )

        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is True

    def test_bitfield_switch_is_on_bit_clear(self, coordinator: EconetNextCoordinator) -> None:
        """Test bitfield switch returns False when bit is clear."""
        # Bit 10 is not set
        coordinator.data["231"] = {"id": 231, "value": 0}

        description = EconetSwitchEntityDescription(
            key="pump_blockage",
            param_id="231",
            bit_position=10,
            invert_logic=False,
        )

        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is False

    def test_bitfield_switch_inverted_logic_on(self, coordinator: EconetNextCoordinator) -> None:
        """Test bitfield switch with inverted logic returns True when bit is clear."""
        # Bit 20 is not set (0 = ON for inverted logic)
        coordinator.data["231"] = {"id": 231, "value": 0}

        description = EconetSwitchEntityDescription(
            key="heating_enable",
            param_id="231",
            bit_position=20,
            invert_logic=True,
        )

        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is True

    def test_bitfield_switch_inverted_logic_off(self, coordinator: EconetNextCoordinator) -> None:
        """Test bitfield switch with inverted logic returns False when bit is set."""
        # Set bit 20 (1 << 20 = 1048576, so 1 = OFF for inverted logic)
        coordinator.data["231"] = {"id": 231, "value": 1048576}

        description = EconetSwitchEntityDescription(
            key="heating_enable",
            param_id="231",
            bit_position=20,
            invert_logic=True,
        )

        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is False

    def test_bitfield_switch_multiple_bits_set(self, coordinator: EconetNextCoordinator) -> None:
        """Test bitfield switch with multiple bits set."""
        # Set bits 10, 13, and 17 (1024 + 8192 + 131072 = 140288)
        coordinator.data["231"] = {"id": 231, "value": 140288}

        # Test bit 10 is on
        description = EconetSwitchEntityDescription(
            key="pump_blockage",
            param_id="231",
            bit_position=10,
            invert_logic=False,
        )
        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is True

        # Test bit 13 is on
        description = EconetSwitchEntityDescription(
            key="pump_only_mode",
            param_id="231",
            bit_position=13,
            invert_logic=False,
        )
        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is True

        # Test bit 17 is on
        description = EconetSwitchEntityDescription(
            key="cooling_enable",
            param_id="231",
            bit_position=17,
            invert_logic=False,
        )
        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is True

        # Test bit 20 is off
        description = EconetSwitchEntityDescription(
            key="heating_enable",
            param_id="231",
            bit_position=20,
            invert_logic=False,
        )
        switch = EconetNextSwitch(coordinator, description)
        assert switch.is_on is False

    @pytest.mark.asyncio
    async def test_bitfield_turn_on_sets_bit(self, coordinator: EconetNextCoordinator) -> None:
        """Test turning on a bitfield switch sets the correct bit."""
        # Start with bits 13 and 17 set (8192 + 131072 = 139264)
        coordinator.data["231"] = {"id": 231, "value": 139264}

        description = EconetSwitchEntityDescription(
            key="pump_blockage",
            param_id="231",
            bit_position=10,
            invert_logic=False,
        )

        switch = EconetNextSwitch(coordinator, description)
        await switch.async_turn_on()

        # Should set bit 10: 139264 | 1024 = 140288
        coordinator.api.async_set_param.assert_called_once_with(231, 140288)
        assert coordinator.data["231"]["value"] == 140288

    @pytest.mark.asyncio
    async def test_bitfield_turn_off_clears_bit(self, coordinator: EconetNextCoordinator) -> None:
        """Test turning off a bitfield switch clears the correct bit."""
        # Start with bits 10, 13, and 17 set (140288)
        coordinator.data["231"] = {"id": 231, "value": 140288}

        description = EconetSwitchEntityDescription(
            key="pump_blockage",
            param_id="231",
            bit_position=10,
            invert_logic=False,
        )

        switch = EconetNextSwitch(coordinator, description)
        await switch.async_turn_off()

        # Should clear bit 10: 140288 & ~1024 = 139264
        coordinator.api.async_set_param.assert_called_once_with(231, 139264)
        assert coordinator.data["231"]["value"] == 139264

    @pytest.mark.asyncio
    async def test_bitfield_inverted_turn_on_clears_bit(self, coordinator: EconetNextCoordinator) -> None:
        """Test turning on inverted bitfield switch clears the bit."""
        # Start with bit 20 set (1048576)
        coordinator.data["231"] = {"id": 231, "value": 1048576}

        description = EconetSwitchEntityDescription(
            key="heating_enable",
            param_id="231",
            bit_position=20,
            invert_logic=True,
        )

        switch = EconetNextSwitch(coordinator, description)
        await switch.async_turn_on()

        # Should clear bit 20 (inverted logic): 1048576 & ~1048576 = 0
        coordinator.api.async_set_param.assert_called_once_with(231, 0)
        assert coordinator.data["231"]["value"] == 0

    @pytest.mark.asyncio
    async def test_bitfield_inverted_turn_off_sets_bit(self, coordinator: EconetNextCoordinator) -> None:
        """Test turning off inverted bitfield switch sets the bit."""
        # Start with no bits set
        coordinator.data["231"] = {"id": 231, "value": 0}

        description = EconetSwitchEntityDescription(
            key="heating_enable",
            param_id="231",
            bit_position=20,
            invert_logic=True,
        )

        switch = EconetNextSwitch(coordinator, description)
        await switch.async_turn_off()

        # Should set bit 20 (inverted logic): 0 | 1048576 = 1048576
        coordinator.api.async_set_param.assert_called_once_with(231, 1048576)
        assert coordinator.data["231"]["value"] == 1048576
