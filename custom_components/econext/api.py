"""API client for ecoNEXT (GM3 Gateway)."""

import logging
from typing import Any

import aiohttp

from .const import API_ENDPOINT_ALARMS, API_ENDPOINT_PARAMETERS

_LOGGER = logging.getLogger(__name__)


class EconextApiError(Exception):
    """Base exception for API errors."""


class EconextConnectionError(EconextApiError):
    """Connection error."""


class EconextApi:
    """API client for the econext-gateway.

    The gateway returns parameters keyed by name with an index field.
    This client transforms the response to be keyed by index (as string)
    so existing entity descriptions that use numeric param_id still work.
    """

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._session = session
        self._base_url = f"http://{host}:{port}"
        # Reverse mapping: index string -> param name (for set operations)
        self._index_to_name: dict[str, str] = {}

    @property
    def host(self) -> str:
        """Return the host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the port."""
        return self._port

    async def async_fetch_all_params(self) -> dict[str, dict[str, Any]]:
        """Fetch all parameters from the gateway.

        The gateway returns:
            {"timestamp": "...", "parameters": {"ParamName": {"index": 0, "value": 42, ...}}}

        We transform this to match the format the integration expects:
            {"0": {"value": 42, "name": "ParamName", "minv": 20.0, "maxv": 80.0, ...}}

        Returns:
            Dictionary of parameters keyed by index (as string).

        """
        url = f"{self._base_url}{API_ENDPOINT_PARAMETERS}"
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with self._session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    raise EconextApiError(f"API returned status {response.status}")

                data = await response.json()

        except aiohttp.ClientError as err:
            raise EconextConnectionError(f"Connection error: {err}") from err

        # Gateway wraps params in "parameters" key
        gateway_params = data.get("parameters", data)

        # Transform: name-keyed -> index-keyed
        params: dict[str, dict[str, Any]] = {}
        index_to_name: dict[str, str] = {}

        for name, param_data in gateway_params.items():
            index = param_data.get("index")
            if index is None:
                continue

            index_str = str(index)
            index_to_name[index_str] = name

            # Map gateway fields to the format the integration uses
            params[index_str] = {
                "value": param_data.get("value"),
                "name": name,
                "minv": param_data.get("min"),
                "maxv": param_data.get("max"),
                "writable": param_data.get("writable", False),
                "type": param_data.get("type"),
                "unit": param_data.get("unit"),
            }

        # Update the reverse mapping for set operations
        self._index_to_name = index_to_name

        _LOGGER.debug("Fetched %d parameters from gateway", len(params))
        return params

    async def async_fetch_alarms(self) -> list[dict[str, Any]]:
        """Fetch alarm history from the gateway.

        Returns:
            List of alarm dicts with keys: index, code, from_date, to_date.
            to_date is None for active (unresolved) alarms.

        """
        url = f"{self._base_url}{API_ENDPOINT_ALARMS}"
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with self._session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    raise EconextApiError(f"Alarms API returned status {response.status}")

                data = await response.json()

        except aiohttp.ClientError as err:
            raise EconextConnectionError(f"Connection error fetching alarms: {err}") from err

        alarms = data.get("alarms", [])
        _LOGGER.debug("Fetched %d alarms from gateway", len(alarms))
        return alarms

    async def async_set_param(self, param_id: str | int, value: Any) -> bool:
        """Set a parameter value on the device.

        Args:
            param_id: The parameter index (used to look up the param name).
            value: The new value.

        Returns:
            True if successful.

        """
        index_str = str(param_id)
        param_name = self._index_to_name.get(index_str)
        if param_name is None:
            raise EconextApiError(f"Unknown parameter index {param_id} - no name mapping found")

        url = f"{self._base_url}{API_ENDPOINT_PARAMETERS}/{param_name}"
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with self._session.post(url, json={"value": value}, timeout=timeout) as response:
                if response.status != 200:
                    raise EconextApiError(f"API returned status {response.status}")

                _LOGGER.debug("Set param %s (%s) to %s", param_name, param_id, value)
                return True

        except aiohttp.ClientError as err:
            raise EconextConnectionError(f"Connection error: {err}") from err

    async def async_test_connection(self) -> dict[str, Any]:
        """Test the connection and return device info.

        Returns:
            Dictionary with basic device info (UID, name, etc.)

        """
        params = await self.async_fetch_all_params()

        # Extract device info from params (same indexes as original)
        uid = params.get("10", {}).get("value", "unknown")
        name = params.get("374", {}).get("value", "ecoMAX")

        return {
            "uid": uid,
            "name": name,
            "param_count": len(params),
        }
