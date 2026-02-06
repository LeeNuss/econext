"""Config flow for ecoNET Next integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import EconetConnectionError, EconetNextApi
from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class EconetNextConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ecoNET Next."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return EconetNextOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await self._async_validate_input(user_input)
            except EconetConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Set unique ID based on device UID
                await self.async_set_unique_id(info["uid"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["name"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            try:
                await self._async_validate_input(user_input)
            except EconetConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates=user_input,
                )

        # Pre-fill with current values
        current_data = reconfigure_entry.data
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_data.get(CONF_HOST, "")): str,
                    vol.Optional(CONF_PORT, default=current_data.get(CONF_PORT, DEFAULT_PORT)): int,
                }
            ),
            errors=errors,
        )

    async def _async_validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input and return device info."""
        session = async_get_clientsession(self.hass)
        api = EconetNextApi(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            session=session,
        )

        return await api.async_test_connection()


class EconetNextOptionsFlow(OptionsFlow):
    """Handle options flow for ecoNET Next."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        # For now, redirect to reconfigure since all settings are in data, not options
        return self.async_abort(reason="reconfigure_instead")
