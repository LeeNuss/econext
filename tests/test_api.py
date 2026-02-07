"""Tests for the econext API client."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.econext.api import (
    EconextApiError,
    EconextConnectionError,
    EconextApi,
)


class TestEconextApi:
    """Test the EconextApi class."""

    def test_init(self, mock_session: MagicMock) -> None:
        """Test API client initialization."""
        api = EconextApi(
            host="192.168.1.100",
            port=8000,
            session=mock_session,
        )

        assert api.host == "192.168.1.100"
        assert api.port == 8000
        assert api._base_url == "http://192.168.1.100:8000"

    def test_init_custom_port(self, mock_session: MagicMock) -> None:
        """Test API client with custom port."""
        api = EconextApi(
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
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=gateway_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_response)

        api = EconextApi(
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
                "42": {
                    "index": 42,
                    "name": "TestParam",
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

        api = EconextApi(host="192.168.1.100", port=8000, session=mock_session)
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

        api = EconextApi(host="192.168.1.100", port=8000, session=mock_session)

        with pytest.raises(EconextApiError, match="status 500"):
            await api.async_fetch_all_params()

    @pytest.mark.asyncio
    async def test_fetch_all_params_connection_error(self, mock_session: MagicMock) -> None:
        """Test connection error handling."""
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))

        api = EconextApi(host="192.168.1.100", port=8000, session=mock_session)

        with pytest.raises(EconextConnectionError, match="Connection error"):
            await api.async_fetch_all_params()


class TestSetParam:
    """Test the async_set_param method."""

    @pytest.mark.asyncio
    async def test_set_param_success(self, mock_session: MagicMock) -> None:
        """Test successful parameter set via POST."""
        set_response = AsyncMock()
        set_response.status = 200
        set_response.__aenter__ = AsyncMock(return_value=set_response)
        set_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post = MagicMock(return_value=set_response)

        api = EconextApi(host="192.168.1.100", port=8000, session=mock_session)

        result = await api.async_set_param("dhwTarget", 45)

        assert result is True
        # Verify POST was called with correct URL and JSON body
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "/api/parameters/dhwTarget" in call_args[0][0]
        assert call_args[1]["json"] == {"value": 45}

    @pytest.mark.asyncio
    async def test_set_param_api_error(self, mock_session: MagicMock) -> None:
        """Test API error when setting parameter."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.post = MagicMock(return_value=mock_response)

        api = EconextApi(host="192.168.1.100", port=8000, session=mock_session)

        with pytest.raises(EconextApiError, match="status 500"):
            await api.async_set_param("dhwTarget", 45)


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

        api = EconextApi(host="192.168.1.100", port=8000, session=mock_session)

        result = await api.async_test_connection()

        assert "uid" in result
        assert "name" in result
        assert "param_count" in result
        assert result["uid"] == "2L7SDPN6KQ38CIH2401K01U"
        assert result["name"] == "ecoMAX360i"
        assert result["param_count"] > 0
