"""Tests for the binary_sensor platform."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.econext.binary_sensor import EconextAlarmActiveBinarySensor
from custom_components.econext.coordinator import EconextCoordinator


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
def coordinator(mock_hass: MagicMock, mock_api: MagicMock, all_params_parsed: dict) -> EconextCoordinator:
    """Create a coordinator with data."""
    coordinator = EconextCoordinator(mock_hass, mock_api)
    coordinator.data = all_params_parsed
    return coordinator


class TestAlarmActiveBinarySensor:
    """Test alarm active binary sensor."""

    def test_no_active_alarms(self, coordinator: EconextCoordinator) -> None:
        """Test sensor is off when no alarms are active."""
        coordinator._alarms = []

        sensor = EconextAlarmActiveBinarySensor(coordinator)

        assert sensor.is_on is False

    def test_active_alarm_present(self, coordinator: EconextCoordinator) -> None:
        """Test sensor is on when an unresolved alarm exists."""
        coordinator._alarms = [
            {"code": 218, "from_date": "2026-01-15 10:00:00", "to_date": None},
        ]

        sensor = EconextAlarmActiveBinarySensor(coordinator)

        assert sensor.is_on is True

    def test_only_resolved_alarms(self, coordinator: EconextCoordinator) -> None:
        """Test sensor is off when all alarms are resolved."""
        coordinator._alarms = [
            {"code": 218, "from_date": "2026-01-15 10:00:00", "to_date": "2026-01-15 12:00:00"},
            {"code": 100, "from_date": "2026-01-10 08:00:00", "to_date": "2026-01-10 09:00:00"},
        ]

        sensor = EconextAlarmActiveBinarySensor(coordinator)

        assert sensor.is_on is False

    def test_mixed_active_and_resolved(self, coordinator: EconextCoordinator) -> None:
        """Test sensor is on when mix of active and resolved alarms."""
        coordinator._alarms = [
            {"code": 218, "from_date": "2026-01-15 10:00:00", "to_date": None},
            {"code": 100, "from_date": "2026-01-10 08:00:00", "to_date": "2026-01-10 09:00:00"},
        ]

        sensor = EconextAlarmActiveBinarySensor(coordinator)

        assert sensor.is_on is True

    def test_extra_state_attributes_no_alarms(self, coordinator: EconextCoordinator) -> None:
        """Test extra state attributes when no alarms."""
        coordinator._alarms = []

        sensor = EconextAlarmActiveBinarySensor(coordinator)
        attrs = sensor.extra_state_attributes

        assert attrs["active_alarm_count"] == 0
        assert attrs["active_alarm_codes"] == []

    def test_extra_state_attributes_with_active(self, coordinator: EconextCoordinator) -> None:
        """Test extra state attributes include active alarm details."""
        coordinator._alarms = [
            {"code": 218, "from_date": "2026-01-15 10:00:00", "to_date": None},
        ]

        sensor = EconextAlarmActiveBinarySensor(coordinator)
        attrs = sensor.extra_state_attributes

        assert attrs["active_alarm_count"] == 1
        assert len(attrs["active_alarm_codes"]) == 1
        assert attrs["active_alarm_codes"][0]["code"] == 218

    def test_unique_id(self, coordinator: EconextCoordinator) -> None:
        """Test binary sensor has correct unique ID."""
        sensor = EconextAlarmActiveBinarySensor(coordinator)

        uid = coordinator.get_device_uid()
        assert sensor.unique_id == f"{uid}_alarm_active"

    def test_device_class(self, coordinator: EconextCoordinator) -> None:
        """Test binary sensor device class is problem."""
        sensor = EconextAlarmActiveBinarySensor(coordinator)

        assert sensor.device_class.value == "problem"

    def test_always_available(self, coordinator: EconextCoordinator) -> None:
        """Test alarm sensor is always valid (reads alarm data, not params)."""
        sensor = EconextAlarmActiveBinarySensor(coordinator)

        assert sensor._is_value_valid() is True
