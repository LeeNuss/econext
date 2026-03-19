"""Config flow for ecoNEXT integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import EconextConnectionError, EconextApi
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import CONF_THERMOSTAT_ENTITY, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class EconextConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ecoNEXT."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return EconextOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await self._async_validate_input(user_input)
            except EconextConnectionError:
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
            # Split into data (connection) and options (thermostat)
            thermostat_entity = user_input.pop(CONF_THERMOSTAT_ENTITY, None)

            try:
                await self._async_validate_input(user_input)
            except EconextConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Save thermostat entity in options
                new_options = dict(reconfigure_entry.options)
                if thermostat_entity:
                    new_options[CONF_THERMOSTAT_ENTITY] = thermostat_entity
                elif CONF_THERMOSTAT_ENTITY in new_options:
                    del new_options[CONF_THERMOSTAT_ENTITY]
                self.hass.config_entries.async_update_entry(
                    reconfigure_entry, options=new_options,
                )

                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates=user_input,
                )

        # Pre-fill with current values
        current_data = reconfigure_entry.data
        current_options = reconfigure_entry.options
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_data.get(CONF_HOST, "")): str,
                    vol.Optional(CONF_PORT, default=current_data.get(CONF_PORT, DEFAULT_PORT)): int,
                    vol.Optional(
                        CONF_THERMOSTAT_ENTITY,
                        default=current_options.get(CONF_THERMOSTAT_ENTITY, ""),
                    ): EntitySelector(
                        EntitySelectorConfig(domain="sensor", device_class="temperature"),
                    ),
                }
            ),
            errors=errors,
        )

    async def _async_validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input and return device info."""
        session = async_get_clientsession(self.hass)
        api = EconextApi(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            session=session,
        )

        return await api.async_test_connection()


class EconextOptionsFlow(OptionsFlow):
    """Handle options flow for ecoNEXT."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Remove empty strings so clearing the entity selector actually clears it
            clean = {k: v for k, v in user_input.items() if v}
            return self.async_create_entry(title="", data=clean)

        current = self._config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_THERMOSTAT_ENTITY,
                        default=current.get(CONF_THERMOSTAT_ENTITY, ""),
                    ): EntitySelector(
                        EntitySelectorConfig(domain="sensor", device_class="temperature"),
                    ),
                }
            ),
        )
