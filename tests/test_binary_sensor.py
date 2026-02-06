"""Tests for the binary_sensor platform."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.econet_next.binary_sensor import EconetNextBinarySensor
from custom_components.econet_next.const import ALARM_BINARY_SENSORS
from custom_components.econet_next.coordinator import EconetNextCoordinator


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


class TestAlarmBinarySensors:
    """Test alarm binary sensors."""

    @pytest.mark.asyncio
    async def test_antifreeze_alarm_off(self, coordinator: EconetNextCoordinator) -> None:
        """Test anti-freeze alarm when inactive."""
        coordinator.data["1042"]["value"] = 0  # No alarms

        description = ALARM_BINARY_SENSORS[0]  # Anti-freeze sensor
        sensor = EconetNextBinarySensor(coordinator, description)

        assert sensor.is_on is False
        assert sensor.device_class == "problem"
        assert sensor.translation_key == "alarm_antifreeze_active"

    @pytest.mark.asyncio
    async def test_antifreeze_alarm_on(self, coordinator: EconetNextCoordinator) -> None:
        """Test anti-freeze alarm when active."""
        coordinator.data["1042"]["value"] = 64  # Bit 6 set

        description = ALARM_BINARY_SENSORS[0]  # Anti-freeze sensor
        sensor = EconetNextBinarySensor(coordinator, description)

        assert sensor.is_on is True

    @pytest.mark.asyncio
    async def test_water_flow_alarm_off(self, coordinator: EconetNextCoordinator) -> None:
        """Test water flow alarm when inactive."""
        coordinator.data["1044"]["value"] = 0  # No alarms

        description = ALARM_BINARY_SENSORS[1]  # Water flow sensor
        sensor = EconetNextBinarySensor(coordinator, description)

        assert sensor.is_on is False
        assert sensor.translation_key == "alarm_water_flow_failure"

    @pytest.mark.asyncio
    async def test_water_flow_alarm_on(self, coordinator: EconetNextCoordinator) -> None:
        """Test water flow alarm when active."""
        coordinator.data["1044"]["value"] = 65536  # Bit 16 set

        description = ALARM_BINARY_SENSORS[1]  # Water flow sensor
        sensor = EconetNextBinarySensor(coordinator, description)

        assert sensor.is_on is True

    @pytest.mark.asyncio
    async def test_multiple_alarms(self, coordinator: EconetNextCoordinator) -> None:
        """Test multiple alarms can be active simultaneously."""
        # Set multiple bits in alarm_bits_1
        coordinator.data["1042"]["value"] = 64 + 128  # Bits 6 and 7

        description = ALARM_BINARY_SENSORS[0]  # Anti-freeze sensor (bit 6)
        sensor = EconetNextBinarySensor(coordinator, description)

        # Should still detect bit 6
        assert sensor.is_on is True

    @pytest.mark.asyncio
    async def test_unique_id(self, coordinator: EconetNextCoordinator) -> None:
        """Test binary sensor has unique ID."""
        description = ALARM_BINARY_SENSORS[0]
        sensor = EconetNextBinarySensor(coordinator, description)

        # Should include param_id and key to differentiate from other bits
        assert "1042" in sensor.unique_id
        assert "alarm_antifreeze_active" in sensor.unique_id

    @pytest.mark.asyncio
    async def test_availability(self, coordinator: EconetNextCoordinator) -> None:
        """Test binary sensor availability."""
        description = ALARM_BINARY_SENSORS[0]
        sensor = EconetNextBinarySensor(coordinator, description)

        # Available when parameter exists
        coordinator.data["1042"] = {"value": 0}
        assert sensor.available is True

        # Unavailable when parameter missing
        del coordinator.data["1042"]
        assert sensor.available is False
