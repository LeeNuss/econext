"""Websocket API for the ecoNEXT integration.

Lets frontend cards ask what this integration supports instead of guessing
from version numbers. An older integration without this module answers
`econext/info` with an unknown-command error, which a card should read as
"no capabilities".
"""

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

_REGISTERED = f"{DOMAIN}_websocket_registered"


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register the websocket commands once per Home Assistant instance."""
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True
    websocket_api.async_register_command(hass, websocket_info)


@websocket_api.websocket_command({vol.Required("type"): "econext/info"})
@callback
def websocket_info(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Report integration capabilities.

    batch_writes: number.set_value calls that arrive together are coalesced
    into one gateway write (one bus token hold), so callers should send them
    concurrently. Without it, concurrent writes each wait for their own bus
    token and the tail can hit the HTTP timeout, so callers should send them
    one at a time.
    """
    connection.send_result(msg["id"], {"batch_writes": True})
