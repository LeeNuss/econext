"""Data coordinator for ecoNET Next."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EconetApiError, EconetNextApi
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EconetNextCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator to manage data updates from ecoNET device."""

    def __init__(self, hass: HomeAssistant, api: EconetNextApi) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data from the API."""
        try:
            return await self.api.async_fetch_all_params()
        except EconetApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def get_param(self, param_id: str | int) -> dict[str, Any] | None:
        """Get a parameter by ID.

        Args:
            param_id: The parameter ID (string or int).

        Returns:
            The parameter dict or None if not found.

        """
        if self.data is None:
            return None
        return self.data.get(str(param_id))

    def get_param_value(self, param_id: str | int) -> Any:
        """Get a parameter value by ID.

        Args:
            param_id: The parameter ID (string or int).

        Returns:
            The parameter value or None if not found.

        """
        param = self.get_param(param_id)
        if param is None:
            return None
        return param.get("value")

    def get_device_uid(self) -> str:
        """Get the device UID."""
        return self.get_param_value(10) or "unknown"

    def get_device_name(self) -> str:
        """Get the device name."""
        return self.get_param_value(374) or "ecoMAX"

    async def async_set_param(self, param_id: str | int, value: Any) -> bool:
        """Set a parameter value on the device with optimistic local update.

        Calls the API to set the value, and on success updates the local cache
        immediately for instant UI feedback.

        Args:
            param_id: The parameter ID (string or int).
            value: The new value to set.

        Returns:
            True if successful.

        """
        # Convert param_id to int for API call
        result = await self.api.async_set_param(int(param_id), value)

        # On success, update local cache for instant UI feedback
        if result and self.data is not None:
            param_key = str(param_id)
            if param_key in self.data:
                self.data[param_key]["value"] = value
                self.async_set_updated_data(self.data)

        return result
