"""Tests for the econet_next data coordinator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.econet_next.api import EconetApiError, EconetNextApi
from custom_components.econet_next.coordinator import EconetNextCoordinator


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.loop = AsyncMock()
    return hass


@pytest.fixture
def mock_api() -> MagicMock:
    """Create a mock EconetNextApi."""
    return MagicMock(spec=EconetNextApi)


@pytest.fixture(autouse=True)
def patch_frame_helper():
    """Patch Home Assistant frame helper for all tests."""
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


class TestCoordinatorInit:
    """Test coordinator initialization."""

    def test_init(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test coordinator initialization."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)

        assert coordinator.api == mock_api
        assert coordinator.name == "econet_next"
        assert coordinator.update_interval.total_seconds() == 30


class TestAsyncUpdateData:
    """Test the _async_update_data method."""

    @pytest.mark.asyncio
    async def test_update_data_success(
        self,
        mock_hass: MagicMock,
        mock_api: MagicMock,
        all_params_parsed: dict,
    ) -> None:
        """Test successful data update."""
        mock_api.async_fetch_all_params = AsyncMock(return_value=all_params_parsed)

        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        result = await coordinator._async_update_data()

        assert result == all_params_parsed
        mock_api.async_fetch_all_params.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_data_api_error(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test that API errors are wrapped in UpdateFailed."""
        mock_api.async_fetch_all_params = AsyncMock(side_effect=EconetApiError("Connection failed"))

        coordinator = EconetNextCoordinator(mock_hass, mock_api)

        with pytest.raises(UpdateFailed, match="Error fetching data"):
            await coordinator._async_update_data()


class TestGetParam:
    """Test the get_param method."""

    def test_get_param_exists(
        self,
        mock_hass: MagicMock,
        mock_api: MagicMock,
        all_params_parsed: dict,
    ) -> None:
        """Test getting an existing parameter."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        # Test with string ID
        param = coordinator.get_param("10")
        assert param is not None
        assert param["name"] == "UID"

        # Test with int ID
        param = coordinator.get_param(10)
        assert param is not None
        assert param["name"] == "UID"

    def test_get_param_not_exists(
        self,
        mock_hass: MagicMock,
        mock_api: MagicMock,
        all_params_parsed: dict,
    ) -> None:
        """Test getting a non-existent parameter."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        param = coordinator.get_param("99999")
        assert param is None

    def test_get_param_no_data(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test getting a parameter when data is None."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = None

        param = coordinator.get_param("10")
        assert param is None


class TestGetParamValue:
    """Test the get_param_value method."""

    def test_get_param_value_exists(
        self,
        mock_hass: MagicMock,
        mock_api: MagicMock,
        all_params_parsed: dict,
    ) -> None:
        """Test getting a parameter value."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        # UID parameter (id 10)
        value = coordinator.get_param_value(10)
        assert value == "2L7SDPN6KQ38CIH2401K01U"

        # Device name (id 374)
        value = coordinator.get_param_value(374)
        assert value == "ecoMAX360i"

    def test_get_param_value_not_exists(
        self,
        mock_hass: MagicMock,
        mock_api: MagicMock,
        all_params_parsed: dict,
    ) -> None:
        """Test getting a non-existent parameter value."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        value = coordinator.get_param_value("99999")
        assert value is None

    def test_get_param_value_no_data(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test getting a parameter value when data is None."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = None

        value = coordinator.get_param_value(10)
        assert value is None


class TestDeviceInfo:
    """Test device info helper methods."""

    def test_get_device_uid(
        self,
        mock_hass: MagicMock,
        mock_api: MagicMock,
        all_params_parsed: dict,
    ) -> None:
        """Test getting device UID."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        uid = coordinator.get_device_uid()
        assert uid == "2L7SDPN6KQ38CIH2401K01U"

    def test_get_device_uid_no_data(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test getting device UID when data is unavailable."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = None

        uid = coordinator.get_device_uid()
        assert uid == "unknown"

    def test_get_device_name(
        self,
        mock_hass: MagicMock,
        mock_api: MagicMock,
        all_params_parsed: dict,
    ) -> None:
        """Test getting device name."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        name = coordinator.get_device_name()
        assert name == "ecoMAX360i"

    def test_get_device_name_no_data(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test getting device name when data is unavailable."""
        coordinator = EconetNextCoordinator(mock_hass, mock_api)
        coordinator.data = None

        name = coordinator.get_device_name()
        assert name == "ecoMAX"
