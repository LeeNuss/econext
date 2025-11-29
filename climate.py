"""Climate platform for ecoNET Next integration."""

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import PRESET_COMFORT, PRESET_ECO
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EconetNextCoordinator
from .entity import EconetNextEntity

_LOGGER = logging.getLogger(__name__)

# Circuit configuration
# Circuit number: (active_param, name_param, work_state_param, thermostat_temp_param, comfort_temp_param, eco_temp_param)
CIRCUITS = {
    1: ("279", "278", "236", "277", "238", "239"),
    2: ("329", "328", "286", "327", "288", "289"),
    3: ("901", "900", "336", "899", "338", "339"),
    4: ("987", "986", "944", "985", "946", "947"),
    5: ("1038", "1037", "995", "1036", "997", "998"),
    6: ("781", "780", "753", "779", "755", "756"),
    7: ("831", "830", "803", "829", "805", "806"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNET Next climate entities from a config entry."""
    coordinator: EconetNextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[CircuitClimate] = []

    # Check each circuit
    for circuit_num, params in CIRCUITS.items():
        (
            active_param,
            name_param,
            work_state_param,
            thermostat_param,
            comfort_param,
            eco_param,
        ) = params

        # Check if circuit is active
        active = coordinator.get_param(active_param)
        if active and active.get("value") == 1:
            entities.append(
                CircuitClimate(
                    coordinator,
                    circuit_num,
                    name_param,
                    work_state_param,
                    thermostat_param,
                    comfort_param,
                    eco_param,
                )
            )
            _LOGGER.debug("Adding climate entity for Circuit %s", circuit_num)
        else:
            _LOGGER.debug(
                "Skipping Circuit %s - not active (param %s)",
                circuit_num,
                active_param,
            )

    async_add_entities(entities)


class CircuitClimate(EconetNextEntity, ClimateEntity):
    """Representation of a heating circuit climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
    _attr_preset_modes = [PRESET_ECO, PRESET_COMFORT]
    _attr_min_temp = 10.0
    _attr_max_temp = 35.0
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        coordinator: EconetNextCoordinator,
        circuit_num: int,
        name_param: str,
        work_state_param: str,
        thermostat_param: str,
        comfort_param: str,
        eco_param: str,
    ) -> None:
        """Initialize the climate entity."""
        # Use work_state_param as primary param for entity base
        super().__init__(coordinator, work_state_param, f"circuit_{circuit_num}")

        self._circuit_num = circuit_num
        self._name_param = name_param
        self._work_state_param = work_state_param
        self._thermostat_param = thermostat_param
        self._comfort_param = comfort_param
        self._eco_param = eco_param

        # Get custom circuit name from controller
        name_param_data = coordinator.get_param(name_param)
        circuit_name = (
            name_param_data.get("value", f"Circuit {circuit_num}").strip()
            if name_param_data
            else f"Circuit {circuit_num}"
        )
        self._attr_name = circuit_name
        self._attr_translation_key = "circuit"

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature from thermostat."""
        temp_param = self.coordinator.get_param(self._thermostat_param)
        if temp_param:
            temp = temp_param.get("value")
            if temp is not None and temp != 999.0:
                return float(temp)
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature based on current preset."""
        preset = self.preset_mode
        if preset == PRESET_COMFORT:
            param = self.coordinator.get_param(self._comfort_param)
        elif preset == PRESET_ECO:
            param = self.coordinator.get_param(self._eco_param)
        else:
            return None

        if param:
            temp = param.get("value")
            if temp is not None:
                return float(temp)
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        work_state = self._get_work_state()
        if work_state == 0:
            return HVACMode.OFF
        elif work_state == 3:
            return HVACMode.AUTO
        else:
            return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action."""
        work_state = self._get_work_state()
        if work_state == 0:
            return HVACAction.OFF

        # Check if currently heating (compare current vs target)
        current = self.current_temperature
        target = self.target_temperature
        if current is not None and target is not None:
            if current < target - 0.5:  # Allowing for hysteresis
                return HVACAction.HEATING
            else:
                return HVACAction.IDLE

        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        work_state = self._get_work_state()
        if work_state == 1:
            return PRESET_ECO
        elif work_state == 2:
            return PRESET_COMFORT
        elif work_state == 3:
            # Auto mode - return None or determine from schedule
            return None
        return None

    def _get_work_state(self) -> int:
        """Get current work state value."""
        param = self.coordinator.get_param(self._work_state_param)
        if param:
            value = param.get("value")
            if value is not None:
                return int(value)
        return 0

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            work_state = 0
        elif hvac_mode == HVACMode.AUTO:
            work_state = 3
        elif hvac_mode == HVACMode.HEAT:
            # When switching to HEAT, default to comfort mode
            work_state = 2
        else:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return

        _LOGGER.debug(
            "Setting Circuit %s HVAC mode to %s (work_state=%s)",
            self._circuit_num,
            hvac_mode,
            work_state,
        )
        await self.coordinator.async_set_param(self._work_state_param, work_state)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if preset_mode == PRESET_ECO:
            work_state = 1
        elif preset_mode == PRESET_COMFORT:
            work_state = 2
        else:
            _LOGGER.error("Unsupported preset mode: %s", preset_mode)
            return

        _LOGGER.debug(
            "Setting Circuit %s preset to %s (work_state=%s)",
            self._circuit_num,
            preset_mode,
            work_state,
        )
        await self.coordinator.async_set_param(self._work_state_param, work_state)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # Set the temperature based on current preset
        preset = self.preset_mode
        if preset == PRESET_COMFORT:
            param_id = self._comfort_param
        elif preset == PRESET_ECO:
            param_id = self._eco_param
        else:
            _LOGGER.warning(
                "Cannot set temperature in mode %s. Switch to ECO or COMFORT first.",
                self.hvac_mode,
            )
            return

        _LOGGER.debug(
            "Setting Circuit %s %s temperature to %s°C",
            self._circuit_num,
            preset,
            temperature,
        )
        await self.coordinator.async_set_param(param_id, float(temperature))
