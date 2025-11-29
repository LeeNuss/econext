"""Climate platform for ecoNET Next integration."""

import logging
from dataclasses import dataclass
from enum import IntEnum

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


class CircuitWorkState(IntEnum):
    """Circuit work state values."""

    OFF = 0
    COMFORT = 1
    ECO = 2
    AUTO = 3


# Circuit configuration
@dataclass
class Circuit:
    """Configuration for a heating circuit."""

    # Core parameters (used by climate entity)
    active_param: str
    name_param: str
    work_state_param: str
    settings_param: str  # Bitmap for heating/cooling/pump-only settings
    thermostat_param: str
    comfort_param: str
    eco_param: str

    # Temperature sensors
    calc_temp_param: str
    room_temp_setpoint_param: str

    # Settings
    hysteresis_param: str
    max_temp_radiator_param: str
    max_temp_heat_param: str
    base_temp_param: str
    temp_reduction_param: str
    curve_multiplier_param: str
    curve_radiator_param: str
    curve_floor_param: str
    curve_fancoil_param: str
    curve_shift_param: str
    room_temp_correction_param: str
    type_settings_param: str

    # Cooling parameters
    min_setpoint_cooling_param: str
    max_setpoint_cooling_param: str
    cooling_base_temp_param: str


CIRCUITS = {
    1: Circuit(
        active_param="279",
        name_param="278",
        work_state_param="236",
        settings_param="231",
        thermostat_param="277",
        comfort_param="238",
        eco_param="239",
        calc_temp_param="237",
        room_temp_setpoint_param="42",
        hysteresis_param="240",
        max_temp_radiator_param="242",
        max_temp_heat_param="243",
        base_temp_param="261",
        temp_reduction_param="262",
        curve_multiplier_param="263",
        curve_radiator_param="273",
        curve_floor_param="274",
        curve_fancoil_param="586",
        curve_shift_param="275",
        room_temp_correction_param="280",
        type_settings_param="269",
        min_setpoint_cooling_param="903",
        max_setpoint_cooling_param="904",
        cooling_base_temp_param="739",
    ),
    2: Circuit(
        active_param="329",
        name_param="328",
        work_state_param="286",
        settings_param="281",
        thermostat_param="327",
        comfort_param="288",
        eco_param="289",
        calc_temp_param="287",
        room_temp_setpoint_param="92",
        hysteresis_param="290",
        max_temp_radiator_param="292",
        max_temp_heat_param="293",
        base_temp_param="311",
        temp_reduction_param="312",
        curve_multiplier_param="313",
        curve_radiator_param="323",
        curve_floor_param="324",
        curve_fancoil_param="587",
        curve_shift_param="325",
        room_temp_correction_param="330",
        type_settings_param="319",
        min_setpoint_cooling_param="787",
        max_setpoint_cooling_param="788",
        cooling_base_temp_param="789",
    ),
    3: Circuit(
        active_param="901",
        name_param="900",
        work_state_param="336",
        settings_param="331",
        thermostat_param="899",
        comfort_param="338",
        eco_param="339",
        calc_temp_param="337",
        room_temp_setpoint_param="93",
        hysteresis_param="340",
        max_temp_radiator_param="342",
        max_temp_heat_param="343",
        base_temp_param="361",
        temp_reduction_param="362",
        curve_multiplier_param="363",
        curve_radiator_param="373",
        curve_floor_param="374",
        curve_fancoil_param="588",
        curve_shift_param="375",
        room_temp_correction_param="380",
        type_settings_param="369",
        min_setpoint_cooling_param="837",
        max_setpoint_cooling_param="838",
        cooling_base_temp_param="839",
    ),
    4: Circuit(
        active_param="987",
        name_param="986",
        work_state_param="944",
        settings_param="940",
        thermostat_param="985",
        comfort_param="946",
        eco_param="947",
        calc_temp_param="945",
        room_temp_setpoint_param="94",
        hysteresis_param="948",
        max_temp_radiator_param="950",
        max_temp_heat_param="951",
        base_temp_param="969",
        temp_reduction_param="970",
        curve_multiplier_param="971",
        curve_radiator_param="981",
        curve_floor_param="982",
        curve_fancoil_param="589",
        curve_shift_param="983",
        room_temp_correction_param="988",
        type_settings_param="977",
        min_setpoint_cooling_param="905",
        max_setpoint_cooling_param="906",
        cooling_base_temp_param="990",
    ),
    5: Circuit(
        active_param="1038",
        name_param="1037",
        work_state_param="995",
        settings_param="991",
        thermostat_param="1036",
        comfort_param="997",
        eco_param="998",
        calc_temp_param="996",
        room_temp_setpoint_param="95",
        hysteresis_param="999",
        max_temp_radiator_param="1001",
        max_temp_heat_param="1002",
        base_temp_param="1020",
        temp_reduction_param="1021",
        curve_multiplier_param="1022",
        curve_radiator_param="1032",
        curve_floor_param="1033",
        curve_fancoil_param="590",
        curve_shift_param="1034",
        room_temp_correction_param="1039",
        type_settings_param="1028",
        min_setpoint_cooling_param="907",
        max_setpoint_cooling_param="908",
        cooling_base_temp_param="1041",
    ),
    6: Circuit(
        active_param="781",
        name_param="780",
        work_state_param="753",
        settings_param="749",
        thermostat_param="779",
        comfort_param="755",
        eco_param="756",
        calc_temp_param="754",
        room_temp_setpoint_param="96",
        hysteresis_param="757",
        max_temp_radiator_param="759",
        max_temp_heat_param="760",
        base_temp_param="768",
        temp_reduction_param="769",
        curve_multiplier_param="770",
        curve_radiator_param="774",
        curve_floor_param="775",
        curve_fancoil_param="591",
        curve_shift_param="776",
        room_temp_correction_param="782",
        type_settings_param="772",
        min_setpoint_cooling_param="909",
        max_setpoint_cooling_param="910",
        cooling_base_temp_param="784",
    ),
    7: Circuit(
        active_param="831",
        name_param="830",
        work_state_param="803",
        settings_param="799",
        thermostat_param="829",
        comfort_param="805",
        eco_param="806",
        calc_temp_param="804",
        room_temp_setpoint_param="97",
        hysteresis_param="807",
        max_temp_radiator_param="809",
        max_temp_heat_param="810",
        base_temp_param="818",
        temp_reduction_param="819",
        curve_multiplier_param="820",
        curve_radiator_param="824",
        curve_floor_param="825",
        curve_fancoil_param="592",
        curve_shift_param="826",
        room_temp_correction_param="832",
        type_settings_param="822",
        min_setpoint_cooling_param="911",
        max_setpoint_cooling_param="912",
        cooling_base_temp_param="834",
    ),
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
    for circuit_num, circuit in CIRCUITS.items():
        # Check if circuit is active
        active = coordinator.get_param(circuit.active_param)
        if active and active.get("value", 0) > 0:
            entities.append(
                CircuitClimate(
                    coordinator,
                    circuit_num,
                    circuit.name_param,
                    circuit.work_state_param,
                    circuit.settings_param,
                    circuit.thermostat_param,
                    circuit.comfort_param,
                    circuit.eco_param,
                )
            )
            _LOGGER.debug("Adding climate entity for Circuit %s", circuit_num)
        else:
            _LOGGER.debug(
                "Skipping Circuit %s - not active (param %s)",
                circuit_num,
                circuit.active_param,
            )

    async_add_entities(entities)


class CircuitClimate(EconetNextEntity, ClimateEntity):
    """Representation of a heating circuit climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
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
        settings_param: str,
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
        self._settings_param = settings_param
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

        # Track last preset mode to restore when switching back to HEAT
        self._last_preset: str | None = None

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return available HVAC modes based on heating/cooling enable settings and system operating mode."""
        modes = [HVACMode.OFF, HVACMode.AUTO]

        # Read settings bitmap
        settings_param = self.coordinator.get_param(self._settings_param)
        if not settings_param:
            # Default to HEAT mode if settings not available
            modes.append(HVACMode.HEAT)
            return modes

        settings_value = int(settings_param.get("value", 0))

        # Check bit 20: heating enable (inverted: 0=on, 1=off)
        heating_enabled = ((settings_value >> 20) & 1) == 0

        # Check bit 17: cooling enable (0=off, 1=on)
        cooling_enabled = ((settings_value >> 17) & 1) == 1

        # Get system operating mode (param 162: 1=summer, 2=winter, 3=auto)
        operating_mode_param = self.coordinator.get_param("162")
        operating_mode = int(operating_mode_param.get("value", 3)) if operating_mode_param else 3

        # Determine available modes based on operating mode and enabled features
        if operating_mode == 1:  # Summer mode - only cooling
            if cooling_enabled:
                modes.append(HVACMode.COOL)
        elif operating_mode == 2:  # Winter mode - only heating
            if heating_enabled:
                modes.append(HVACMode.HEAT)
        else:  # Auto mode (3) or unknown - both heating and cooling available
            if heating_enabled and cooling_enabled:
                modes.append(HVACMode.HEAT_COOL)
            if heating_enabled:
                modes.append(HVACMode.HEAT)
            if cooling_enabled:
                modes.append(HVACMode.COOL)

        return modes

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
        if work_state == CircuitWorkState.OFF:
            return HVACMode.OFF
        elif work_state == CircuitWorkState.AUTO:
            return HVACMode.AUTO
        else:
            return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action."""
        work_state = self._get_work_state()
        if work_state == CircuitWorkState.OFF:
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
        if work_state == CircuitWorkState.ECO:
            self._last_preset = PRESET_ECO
            return PRESET_ECO
        elif work_state == CircuitWorkState.COMFORT:
            self._last_preset = PRESET_COMFORT
            return PRESET_COMFORT
        elif work_state == CircuitWorkState.AUTO:
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
            work_state = CircuitWorkState.OFF
        elif hvac_mode == HVACMode.AUTO:
            work_state = CircuitWorkState.AUTO
        elif hvac_mode == HVACMode.HEAT:
            # When switching to HEAT, use last preset or default to COMFORT
            if self._last_preset == PRESET_ECO:
                work_state = CircuitWorkState.ECO
            else:
                # Default to COMFORT (also handles None case)
                work_state = CircuitWorkState.COMFORT
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
            work_state = CircuitWorkState.ECO
        elif preset_mode == PRESET_COMFORT:
            work_state = CircuitWorkState.COMFORT
        else:
            _LOGGER.error("Unsupported preset mode: %s", preset_mode)
            return

        # Update last preset
        self._last_preset = preset_mode

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
