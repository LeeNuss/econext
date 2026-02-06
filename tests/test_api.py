"""Tests for the econet_next API client."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.econet_next.api import (
    EconetApiError,
    EconetConnectionError,
    EconetNextApi,
)


class TestEconetNextApi:
    """Test the EconetNextApi class."""

    def test_init(self, mock_session: MagicMock) -> None:
        """Test API client initialization."""
        api = EconetNextApi(
            host="192.168.1.100",
            port=8000,
            session=mock_session,
        )

        assert api.host == "192.168.1.100"
        assert api.port == 8000
        assert api._base_url == "http://192.168.1.100:8000"

    def test_init_custom_port(self, mock_session: MagicMock) -> None:
        """Test API client with custom port."""
        api = EconetNextApi(
            host="192.168.1.100",
            port=9000,
            session=mock_session,
        )

        assert api._base_url == "http://192.168.1.100:9000"


class TestFetchAllParams:
    """Test the async_fetch_all_params method."""

    @pytest.mark.asyncio
    async def test_fetch_all_params_success(
        self,
        mock_session: MagicMock,
        gateway_api_response: dict,
    ) -> None:
        """Test successful fetch of all parameters."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=gateway_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_response)

        api = EconetNextApi(
            host="192.168.1.100",
            port=8000,
            session=mock_session,
        )

        result = await api.async_fetch_all_params()

        assert isinstance(result, dict)
        # Check that the result is keyed by index (string)
        assert "10" in result  # UID
        assert "374" in result  # Nazwa (device name)
        assert result["10"]["name"] == "UID"
        assert result["10"]["value"] == "2L7SDPN6KQ38CIH2401K01U"
        assert result["374"]["name"] == "Nazwa"
        assert result["374"]["value"] == "ecoMAX360i"

    @pytest.mark.asyncio
    async def test_fetch_all_params_transforms_fields(
        self,
        mock_session: MagicMock,
    ) -> None:
        """Test that gateway fields are correctly mapped."""
        gateway_response = {
            "timestamp": "2026-02-06T12:00:00",
            "parameters": {
                "TestParam": {
                    "index": 42,
                    "value": 100,
                    "type": 2,
                    "unit": 1,
                    "writable": True,
                    "min": 10.0,
                    "max": 200.0,
                }
            },
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=gateway_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_response)

        api = EconetNextApi(host="192.168.1.100", port=8000, session=mock_session)
        result = await api.async_fetch_all_params()

        assert "42" in result
        param = result["42"]
        assert param["value"] == 100
        assert param["name"] == "TestParam"
        assert param["minv"] == 10.0
        assert param["maxv"] == 200.0
        assert param["writable"] is True

    @pytest.mark.asyncio
    async def test_fetch_all_params_api_error(self, mock_session: MagicMock) -> None:
        """Test API error handling for non-200 status."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_response)

        api = EconetNextApi(host="192.168.1.100", port=8000, session=mock_session)

        with pytest.raises(EconetApiError, match="status 500"):
            await api.async_fetch_all_params()

    @pytest.mark.asyncio
    async def test_fetch_all_params_connection_error(self, mock_session: MagicMock) -> None:
        """Test connection error handling."""
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))

        api = EconetNextApi(host="192.168.1.100", port=8000, session=mock_session)

        with pytest.raises(EconetConnectionError, match="Connection error"):
            await api.async_fetch_all_params()

    @pytest.mark.asyncio
    async def test_fetch_builds_index_to_name_mapping(
        self,
        mock_session: MagicMock,
    ) -> None:
        """Test that fetching builds the index-to-name reverse mapping."""
        gateway_response = {
            "parameters": {
                "ParamA": {"index": 10, "value": "test"},
                "ParamB": {"index": 20, "value": 42},
            }
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=gateway_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_response)

        api = EconetNextApi(host="192.168.1.100", port=8000, session=mock_session)
        await api.async_fetch_all_params()

        assert api._index_to_name["10"] == "ParamA"
        assert api._index_to_name["20"] == "ParamB"


class TestSetParam:
    """Test the async_set_param method."""

    @pytest.mark.asyncio
    async def test_set_param_success(self, mock_session: MagicMock) -> None:
        """Test successful parameter set via POST."""
        # First, populate the index-to-name mapping
        fetch_response = AsyncMock()
        fetch_response.status = 200
        fetch_response.json = AsyncMock(
            return_value={
                "parameters": {
                    "dhwTarget": {"index": 103, "value": 40},
                }
            }
        )
        fetch_response.__aenter__ = AsyncMock(return_value=fetch_response)
        fetch_response.__aexit__ = AsyncMock(return_value=None)

        set_response = AsyncMock()
        set_response.status = 200
        set_response.__aenter__ = AsyncMock(return_value=set_response)
        set_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=fetch_response)
        mock_session.post = MagicMock(return_value=set_response)

        api = EconetNextApi(host="192.168.1.100", port=8000, session=mock_session)

        # Fetch first to build mapping
        await api.async_fetch_all_params()

        # Now set a param
        result = await api.async_set_param(103, 45)

        assert result is True
        # Verify POST was called with correct URL and JSON body
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "/api/parameters/dhwTarget" in call_args[0][0]
        assert call_args[1]["json"] == {"value": 45}

    @pytest.mark.asyncio
    async def test_set_param_unknown_index(self, mock_session: MagicMock) -> None:
        """Test setting a parameter with unknown index raises error."""
        api = EconetNextApi(host="192.168.1.100", port=8000, session=mock_session)

        with pytest.raises(EconetApiError, match="Unknown parameter index"):
            await api.async_set_param(99999, 45)

    @pytest.mark.asyncio
    async def test_set_param_api_error(self, mock_session: MagicMock) -> None:
        """Test API error when setting parameter."""
        api = EconetNextApi(host="192.168.1.100", port=8000, session=mock_session)
        api._index_to_name = {"103": "dhwTarget"}

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post = MagicMock(return_value=mock_response)

        with pytest.raises(EconetApiError, match="status 500"):
            await api.async_set_param(103, 45)


class TestTestConnection:
    """Test the async_test_connection method."""

    @pytest.mark.asyncio
    async def test_connection_returns_device_info(
        self,
        mock_session: MagicMock,
        gateway_api_response: dict,
    ) -> None:
        """Test that test_connection returns device info."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=gateway_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_response)

        api = EconetNextApi(host="192.168.1.100", port=8000, session=mock_session)

        result = await api.async_test_connection()

        assert "uid" in result
        assert "name" in result
        assert "param_count" in result
        assert result["uid"] == "2L7SDPN6KQ38CIH2401K01U"
        assert result["name"] == "ecoMAX360i"
        assert result["param_count"] > 0
