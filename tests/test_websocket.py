"""Tests for the econext websocket API."""

from unittest.mock import MagicMock, patch

from custom_components.econext.websocket import (
    async_register_websocket_commands,
    websocket_info,
)


def test_info_reports_batch_writes() -> None:
    connection = MagicMock()

    websocket_info(MagicMock(), connection, {"id": 7, "type": "econext/info"})

    connection.send_result.assert_called_once_with(7, {"batch_writes": True})


def test_commands_registered_once() -> None:
    hass = MagicMock()
    hass.data = {}

    with patch("custom_components.econext.websocket.websocket_api.async_register_command") as register:
        async_register_websocket_commands(hass)
        async_register_websocket_commands(hass)

    register.assert_called_once_with(hass, websocket_info)
