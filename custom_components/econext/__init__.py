"""The ecoNEXT integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import EconextConnectionError, EconextApi
from .const import (
    CONF_COOLING_CIRCUIT,
    CONF_COOLING_ENABLED,
    CONF_DEW_POINT_ENTITY,
    CONF_OEM_FLOW_ENTITY,
    CONF_THERMOSTAT_ENTITY,
    DEFAULT_COOLING_CIRCUIT,
    DEFAULT_PORT,
    DOMAIN,
    MANUFACTURER,
    PLATFORMS,
)
from .cooling.driver import CoolingDriver
from .cooling.migrate import async_ensure_fan_coil, async_migrate_heating_curve_unique_ids
from .coordinator import EconextCoordinator

_LOGGER = logging.getLogger(__name__)

COOLING_STORAGE_VERSION = 1

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

    # Optional cooling controller — enabled and dew-point sensor configured.
    if entry.options.get(CONF_COOLING_ENABLED) and entry.options.get(CONF_DEW_POINT_ENTITY):
        store = Store(hass, COOLING_STORAGE_VERSION, f"{DOMAIN}_cooling_{entry.entry_id}")
        coordinator.cooling_driver = CoolingDriver(
            coordinator,
            circuit=int(entry.options.get(CONF_COOLING_CIRCUIT, DEFAULT_COOLING_CIRCUIT)),
            dew_point_entity=entry.options.get(CONF_DEW_POINT_ENTITY),
            oem_flow_entity=entry.options.get(CONF_OEM_FLOW_ENTITY),
            store=store,
        )
        if not coordinator.cooling_driver.available:
            _LOGGER.warning(
                "Cooling enabled but circuit %s has no cooling registers; disabling",
                entry.options.get(CONF_COOLING_CIRCUIT, DEFAULT_COOLING_CIRCUIT),
            )
            coordinator.cooling_driver = None
        else:
            await coordinator.cooling_driver.async_load()
            # Idempotently switch the controlled circuit to fan_coil so the HP
            # runs the right control law; carries the existing heating curve
            # value over to the fan_coil curve register first.
            try:
                await async_ensure_fan_coil(coordinator, coordinator.cooling_driver.circuit)
            except Exception:  # noqa: BLE001 - never break entry setup
                _LOGGER.exception("Cooling: fan_coil migration failed")

    # Store coordinator
    entry.runtime_data = coordinator
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    # Listen for options changes
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    # Rename legacy param-id-based heating_curve unique_ids before platforms
    # re-create entities under the new stable form.
    async_migrate_heating_curve_unique_ids(hass, entry)

    # Register the main controller device before the platforms load, so
    # sub-devices can link to it by device id regardless of entity order.
    main_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.get_device_uid())},
        name=coordinator.get_device_name(),
        manufacturer=MANUFACTURER,
        model="ecoMAX360i",
    )
    coordinator.main_device_id = main_device.id

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
    coordinator: EconextCoordinator = entry.runtime_data
    uid = coordinator.get_device_uid()

    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    for device in devices:
        entities = er.async_entries_for_device(entity_reg, device.id, include_disabled_entities=True)
        if not entities:
            _LOGGER.info("Removing orphaned device: %s (%s)", device.name, device.id)
            device_reg.async_remove_device(device.id)
            continue

        # Remove virtual thermostat device if thermostat is not configured
        if not entry.options.get(CONF_THERMOSTAT_ENTITY):
            vt_identifier = (DOMAIN, f"{uid}_virtual_thermostat")
            if vt_identifier in device.identifiers:
                _LOGGER.info("Removing virtual thermostat device (thermostat not configured)")
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
