"""Tests for the econext data coordinator."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.econext.api import (
    EconextApi,
    EconextApiError,
    EconextBatchRejectedError,
    EconextBatchUnsupportedError,
)
from custom_components.econext.coordinator import EconextCoordinator


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.loop = AsyncMock()
    return hass


@pytest.fixture
def mock_api() -> MagicMock:
    """Create a mock EconextApi."""
    return MagicMock(spec=EconextApi)


@pytest.fixture(autouse=True)
def patch_frame_helper():
    """Patch Home Assistant frame helper for all tests."""
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


class TestCoordinatorInit:
    """Test coordinator initialization."""

    def test_init(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test coordinator initialization."""
        coordinator = EconextCoordinator(mock_hass, mock_api)

        assert coordinator.api == mock_api
        assert coordinator.name == "econext"
        assert coordinator.update_interval.total_seconds() == 10


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

        coordinator = EconextCoordinator(mock_hass, mock_api)
        result = await coordinator._async_update_data()

        assert result == all_params_parsed
        mock_api.async_fetch_all_params.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_data_api_error(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test that API errors are wrapped in UpdateFailed."""
        mock_api.async_fetch_all_params = AsyncMock(side_effect=EconextApiError("Connection failed"))

        coordinator = EconextCoordinator(mock_hass, mock_api)

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
        coordinator = EconextCoordinator(mock_hass, mock_api)
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
        coordinator = EconextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        param = coordinator.get_param("99999")
        assert param is None

    def test_get_param_no_data(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test getting a parameter when data is None."""
        coordinator = EconextCoordinator(mock_hass, mock_api)
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
        coordinator = EconextCoordinator(mock_hass, mock_api)
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
        coordinator = EconextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        value = coordinator.get_param_value("99999")
        assert value is None

    def test_get_param_value_no_data(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test getting a parameter value when data is None."""
        coordinator = EconextCoordinator(mock_hass, mock_api)
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
        coordinator = EconextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        uid = coordinator.get_device_uid()
        assert uid == "2L7SDPN6KQ38CIH2401K01U"

    def test_get_device_uid_no_data(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test getting device UID when data is unavailable."""
        coordinator = EconextCoordinator(mock_hass, mock_api)
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
        coordinator = EconextCoordinator(mock_hass, mock_api)
        coordinator.data = all_params_parsed

        name = coordinator.get_device_name()
        assert name == "ecoMAX360i"

    def test_get_device_name_no_data(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        """Test getting device name when data is unavailable."""
        coordinator = EconextCoordinator(mock_hass, mock_api)
        coordinator.data = None

        name = coordinator.get_device_name()
        assert name == "ecoMAX360i"


class TestWriteCoalescing:
    """Writes requested together go to the gateway as one batch."""

    @staticmethod
    def _coordinator(mock_hass: MagicMock, mock_api: MagicMock) -> EconextCoordinator:
        coordinator = EconextCoordinator(mock_hass, mock_api)
        coordinator.data = {
            "1": {"name": "A", "value": 0},
            "2": {"name": "B", "value": 0},
            "3": {"name": "C", "value": 0},
        }
        coordinator.async_set_updated_data = MagicMock()
        return coordinator

    @pytest.mark.asyncio
    async def test_concurrent_writes_are_batched(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        mock_api.async_set_params = AsyncMock(return_value={"A": True, "B": True, "C": True})
        mock_api.async_set_param = AsyncMock()
        coordinator = self._coordinator(mock_hass, mock_api)

        results = await asyncio.gather(
            coordinator.async_set_param(1, 10),
            coordinator.async_set_param(2, 20),
            coordinator.async_set_param("3", 30),
        )

        assert results == [True, True, True]
        mock_api.async_set_params.assert_awaited_once_with({"A": 10, "B": 20, "C": 30})
        mock_api.async_set_param.assert_not_awaited()
        assert [coordinator.data[k]["value"] for k in ("1", "2", "3")] == [10, 20, 30]
        coordinator.async_set_updated_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_write_uses_single_endpoint(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        mock_api.async_set_params = AsyncMock()
        mock_api.async_set_param = AsyncMock(return_value=True)
        coordinator = self._coordinator(mock_hass, mock_api)

        assert await coordinator.async_set_param(1, 10) is True

        mock_api.async_set_param.assert_awaited_once_with("A", 10)
        mock_api.async_set_params.assert_not_awaited()
        assert coordinator.data["1"]["value"] == 10

    @pytest.mark.asyncio
    async def test_same_param_last_value_wins(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        mock_api.async_set_param = AsyncMock(return_value=True)
        coordinator = self._coordinator(mock_hass, mock_api)

        results = await asyncio.gather(
            coordinator.async_set_param(1, 10),
            coordinator.async_set_param(1, 11),
        )

        assert results == [True, True]
        mock_api.async_set_param.assert_awaited_once_with("A", 11)
        assert coordinator.data["1"]["value"] == 11

    @pytest.mark.asyncio
    async def test_unacked_write_raises_for_its_caller_only(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        mock_api.async_set_params = AsyncMock(return_value={"A": True, "B": False})
        coordinator = self._coordinator(mock_hass, mock_api)

        results = await asyncio.gather(
            coordinator.async_set_param(1, 10),
            coordinator.async_set_param(2, 20),
            return_exceptions=True,
        )

        assert results[0] is True
        assert isinstance(results[1], EconextApiError)
        assert coordinator.data["1"]["value"] == 10
        assert coordinator.data["2"]["value"] == 0

    @pytest.mark.asyncio
    async def test_old_gateway_falls_back_to_single_writes(
        self, mock_hass: MagicMock, mock_api: MagicMock
    ) -> None:
        mock_api.async_set_params = AsyncMock(side_effect=EconextBatchUnsupportedError("405"))
        mock_api.async_set_param = AsyncMock(return_value=True)
        coordinator = self._coordinator(mock_hass, mock_api)

        await asyncio.gather(coordinator.async_set_param(1, 10), coordinator.async_set_param(2, 20))
        await asyncio.gather(coordinator.async_set_param(1, 11), coordinator.async_set_param(2, 21))

        # Batch endpoint is probed once, then skipped.
        mock_api.async_set_params.assert_awaited_once()
        assert mock_api.async_set_param.await_count == 4

    @pytest.mark.asyncio
    async def test_rejected_batch_retries_singly(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        mock_api.async_set_params = AsyncMock(side_effect=EconextBatchRejectedError("400"))
        mock_api.async_set_param = AsyncMock(side_effect=[True, EconextApiError("status 400")])
        coordinator = self._coordinator(mock_hass, mock_api)

        results = await asyncio.gather(
            coordinator.async_set_param(1, 10),
            coordinator.async_set_param(2, 9999),
            return_exceptions=True,
        )

        assert results[0] is True
        assert isinstance(results[1], EconextApiError)
        assert coordinator._batch_supported is True

    @pytest.mark.asyncio
    async def test_write_during_inflight_batch_goes_in_next_batch(
        self, mock_hass: MagicMock, mock_api: MagicMock
    ) -> None:
        release = asyncio.Event()
        calls: list[dict] = []

        async def slow_set_params(values):
            calls.append(values)
            if len(calls) == 1:
                await release.wait()
            return dict.fromkeys(values, True)

        mock_api.async_set_params = AsyncMock(side_effect=slow_set_params)
        coordinator = self._coordinator(mock_hass, mock_api)

        first = asyncio.gather(coordinator.async_set_param(1, 10), coordinator.async_set_param(2, 20))
        while not calls:
            await asyncio.sleep(0.01)
        second = asyncio.gather(coordinator.async_set_param(1, 11), coordinator.async_set_param(3, 30))
        await asyncio.sleep(0.01)
        release.set()

        assert await first == [True, True]
        assert await second == [True, True]
        assert calls == [{"A": 10, "B": 20}, {"A": 11, "C": 30}]


class TestStartupParameters:
    """Setup must not settle for a partly loaded gateway."""

    @pytest.mark.asyncio
    async def test_empty_parameter_set_fails_update(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        mock_api.async_fetch_all_params = AsyncMock(return_value={})
        coordinator = EconextCoordinator(mock_hass, mock_api)

        with pytest.raises(UpdateFailed, match="no parameters"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_missing_uid_fails_first_update(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        mock_api.async_fetch_all_params = AsyncMock(return_value={"0": {"name": "PS", "value": "1.0"}})
        coordinator = EconextCoordinator(mock_hass, mock_api)

        with pytest.raises(UpdateFailed, match="UID"):
            await coordinator._async_update_data()

    @staticmethod
    def _params(count: int) -> dict:
        return {str(i): {"name": f"P{i}", "value": 0} for i in range(count)}

    def _coordinator(self, mock_hass: MagicMock, mock_api: MagicMock) -> EconextCoordinator:
        coordinator = EconextCoordinator(mock_hass, mock_api)
        coordinator.config_entry = MagicMock(entry_id="entry1")
        coordinator.data = self._params(100)
        coordinator.mark_entities_created()
        return coordinator

    def test_large_growth_reloads_once(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        coordinator = self._coordinator(mock_hass, mock_api)

        coordinator._check_late_parameters(500)
        coordinator._check_late_parameters(600)

        mock_hass.config_entries.async_schedule_reload.assert_called_once_with("entry1")

    def test_small_growth_does_not_reload(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        coordinator = self._coordinator(mock_hass, mock_api)

        coordinator._check_late_parameters(105)

        mock_hass.config_entries.async_schedule_reload.assert_not_called()

    def test_no_reload_before_entities_exist(self, mock_hass: MagicMock, mock_api: MagicMock) -> None:
        coordinator = EconextCoordinator(mock_hass, mock_api)
        coordinator.config_entry = MagicMock(entry_id="entry1")

        coordinator._check_late_parameters(500)

        mock_hass.config_entries.async_schedule_reload.assert_not_called()
