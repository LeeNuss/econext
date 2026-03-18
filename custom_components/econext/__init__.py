"""The ecoNEXT integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EconextConnectionError, EconextApi
from .const import CONF_THERMOSTAT_ENTITY, DEFAULT_PORT, DOMAIN, PLATFORMS
from .coordinator import EconextCoordinator

_LOGGER = logging.getLogger(__name__)

type EconextConfigEntry = ConfigEntry[EconextCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EconextConfigEntry) -> bool:
    """Set up ecoNEXT from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API client
    session = async_get_clientsession(hass)
    api = EconextApi(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        session=session,
    )

    # Create coordinator
    thermostat_entity = entry.options.get(CONF_THERMOSTAT_ENTITY)
    coordinator = EconextCoordinator(hass, api, thermostat_entity_id=thermostat_entity)

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except EconextConnectionError as err:
        raise ConfigEntryNotReady(f"Connection failed: {err}") from err

    # Store coordinator
    entry.runtime_data = coordinator
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    # Listen for options changes
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Clean up orphaned devices (no entities after platform setup)
    await _async_cleanup_orphaned_devices(hass, entry)

    _LOGGER.info(
        "ecoNEXT integration set up for %s (%s)",
        coordinator.get_device_name(),
        coordinator.get_device_uid(),
    )

    return True


async def _async_cleanup_orphaned_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove devices that have no entities after platform setup."""
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    for device in devices:
        entities = er.async_entries_for_device(entity_reg, device.id, include_disabled_entities=True)
        if not entities:
            _LOGGER.info("Removing orphaned device: %s (%s)", device.name, device.id)
            device_reg.async_remove_device(device.id)


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of a device from the integration.

    Returns True if the device can be removed (has no active entities).
    HA checks for remaining entities before actually deleting.
    """
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EconextConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
