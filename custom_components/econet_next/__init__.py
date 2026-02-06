"""The ecoNET Next integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EconetConnectionError, EconetNextApi
from .const import DEFAULT_PORT, DOMAIN, PLATFORMS
from .coordinator import EconetNextCoordinator

_LOGGER = logging.getLogger(__name__)

type EconetNextConfigEntry = ConfigEntry[EconetNextCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EconetNextConfigEntry) -> bool:
    """Set up ecoNET Next from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API client
    session = async_get_clientsession(hass)
    api = EconetNextApi(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        session=session,
    )

    # Create coordinator
    coordinator = EconetNextCoordinator(hass, api)

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except EconetConnectionError as err:
        raise ConfigEntryNotReady(f"Connection failed: {err}") from err

    # Store coordinator
    entry.runtime_data = coordinator
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "ecoNET Next integration set up for %s (%s)",
        coordinator.get_device_name(),
        coordinator.get_device_uid(),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EconetNextConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
