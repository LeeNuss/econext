"""Climate platform for ecoNEXT integration."""

import logging
from dataclasses import dataclass
from enum import IntEnum

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import PRESET_COMFORT, PRESET_ECO
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EconextCoordinator
from .entity import EconextEntity

_LOGGER = logging.getLogger(__name__)

# Custom preset for schedule mode
PRESET_SCHEDULE = "schedule"


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
    fixed_temp_param: str
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
    cooling_fixed_temp_param: str

    # Schedule parameters (AM/PM for each day of week)
    schedule_sunday_am: str
    schedule_sunday_pm: str
    schedule_monday_am: str
    schedule_monday_pm: str
    schedule_tuesday_am: str
    schedule_tuesday_pm: str
    schedule_wednesday_am: str
    schedule_wednesday_pm: str
    schedule_thursday_am: str
    schedule_thursday_pm: str
    schedule_friday_am: str
    schedule_friday_pm: str
    schedule_saturday_am: str
    schedule_saturday_pm: str


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
        fixed_temp_param="261",
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
        cooling_fixed_temp_param="739",
        schedule_sunday_am="247",
        schedule_sunday_pm="248",
        schedule_monday_am="249",
        schedule_monday_pm="250",
        schedule_tuesday_am="251",
        schedule_tuesday_pm="252",
        schedule_wednesday_am="253",
        schedule_wednesday_pm="254",
        schedule_thursday_am="255",
        schedule_thursday_pm="256",
        schedule_friday_am="257",
        schedule_friday_pm="258",
        schedule_saturday_am="259",
        schedule_saturday_pm="260",
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
        fixed_temp_param="311",
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
        cooling_fixed_temp_param="789",
        schedule_sunday_am="297",
        schedule_sunday_pm="298",
        schedule_monday_am="299",
        schedule_monday_pm="300",
        schedule_tuesday_am="301",
        schedule_tuesday_pm="302",
        schedule_wednesday_am="303",
        schedule_wednesday_pm="304",
        schedule_thursday_am="305",
        schedule_thursday_pm="306",
        schedule_friday_am="307",
        schedule_friday_pm="308",
        schedule_saturday_am="309",
        schedule_saturday_pm="310",
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
        fixed_temp_param="361",
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
        cooling_fixed_temp_param="839",
        schedule_sunday_am="881",
        schedule_sunday_pm="882",
        schedule_monday_am="883",
        schedule_monday_pm="884",
        schedule_tuesday_am="885",
        schedule_tuesday_pm="886",
        schedule_wednesday_am="887",
        schedule_wednesday_pm="888",
        schedule_thursday_am="889",
        schedule_thursday_pm="890",
        schedule_friday_am="891",
        schedule_friday_pm="892",
        schedule_saturday_am="893",
        schedule_saturday_pm="894",
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
        fixed_temp_param="969",
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
        cooling_fixed_temp_param="990",
        schedule_sunday_am="955",
        schedule_sunday_pm="956",
        schedule_monday_am="957",
        schedule_monday_pm="958",
        schedule_tuesday_am="959",
        schedule_tuesday_pm="960",
        schedule_wednesday_am="961",
        schedule_wednesday_pm="962",
        schedule_thursday_am="963",
        schedule_thursday_pm="964",
        schedule_friday_am="965",
        schedule_friday_pm="966",
        schedule_saturday_am="967",
        schedule_saturday_pm="968",
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
        fixed_temp_param="1020",
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
        cooling_fixed_temp_param="1041",
        schedule_sunday_am="1006",
        schedule_sunday_pm="1007",
        schedule_monday_am="1008",
        schedule_monday_pm="1009",
        schedule_tuesday_am="1010",
        schedule_tuesday_pm="1011",
        schedule_wednesday_am="1012",
        schedule_wednesday_pm="1013",
        schedule_thursday_am="1014",
        schedule_thursday_pm="1015",
        schedule_friday_am="1016",
        schedule_friday_pm="1017",
        schedule_saturday_am="1018",
        schedule_saturday_pm="1019",
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
        fixed_temp_param="768",
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
        cooling_fixed_temp_param="784",
        schedule_sunday_am="867",
        schedule_sunday_pm="868",
        schedule_monday_am="869",
        schedule_monday_pm="870",
        schedule_tuesday_am="871",
        schedule_tuesday_pm="872",
        schedule_wednesday_am="873",
        schedule_wednesday_pm="874",
        schedule_thursday_am="875",
        schedule_thursday_pm="876",
        schedule_friday_am="877",
        schedule_friday_pm="878",
        schedule_saturday_am="879",
        schedule_saturday_pm="880",
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
        fixed_temp_param="818",
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
        cooling_fixed_temp_param="834",
        schedule_sunday_am="845",
        schedule_sunday_pm="846",
        schedule_monday_am="847",
        schedule_monday_pm="848",
        schedule_tuesday_am="849",
        schedule_tuesday_pm="850",
        schedule_wednesday_am="851",
        schedule_wednesday_pm="852",
        schedule_thursday_am="853",
        schedule_thursday_pm="854",
        schedule_friday_am="855",
        schedule_friday_pm="856",
        schedule_saturday_am="857",
        schedule_saturday_pm="858",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ecoNEXT climate entities from a config entry."""
    coordinator: EconextCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

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
                    circuit.room_temp_setpoint_param,
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


class CircuitClimate(EconextEntity, ClimateEntity):
    """Representation of a heating circuit climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_preset_modes = [PRESET_ECO, PRESET_COMFORT, PRESET_SCHEDULE]
    _attr_min_temp = 10.0
    _attr_max_temp = 35.0
    _attr_target_temperature_step = 0.5

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE
        )

    def __init__(
        self,
        coordinator: EconextCoordinator,
        circuit_num: int,
        name_param: str,
        work_state_param: str,
        settings_param: str,
        thermostat_param: str,
        comfort_param: str,
        eco_param: str,
        room_temp_setpoint_param: str,
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
        self._room_temp_setpoint_param = room_temp_setpoint_param

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
        """Return available HVAC modes.

        OFF: circuit off
        AUTO: controller decides heating/cooling based on operating mode
        HEAT: force heating only
        COOL: force cooling only (requires cooling_support enabled globally)
        """
        modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT]

        # Only offer COOL if cooling_support (param 485) is globally enabled
        cooling_support_param = self.coordinator.get_param("485")
        if cooling_support_param and int(cooling_support_param.get("value", 0)):
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
        if preset == PRESET_SCHEDULE:
            # In schedule mode, return the active preset temperature
            # _last_preset is updated by _detect_active_preset() in preset_mode property
            active_preset = self._last_preset if self._last_preset in (PRESET_ECO, PRESET_COMFORT) else PRESET_COMFORT
            param_id = self._comfort_param if active_preset == PRESET_COMFORT else self._eco_param
            param = self.coordinator.get_param(param_id)
        elif preset == PRESET_COMFORT:
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
        """Return current HVAC mode based on work state and heating/cooling enable settings."""
        work_state = self._get_work_state()
        if work_state == CircuitWorkState.OFF:
            return HVACMode.OFF

        # Circuit is ON - determine mode from heating/cooling enable bits
        settings_param = self.coordinator.get_param(self._settings_param)
        if not settings_param:
            return HVACMode.HEAT  # Default fallback

        settings_value = int(settings_param.get("value", 0))

        # Check bit 20: heating enable (inverted: 0=on, 1=off)
        heating_enabled = ((settings_value >> 20) & 1) == 0

        # Check bit 17: cooling enable (0=off, 1=on)
        cooling_enabled = ((settings_value >> 17) & 1) == 1

        # Determine HVAC mode
        if heating_enabled and cooling_enabled:
            return HVACMode.AUTO
        elif heating_enabled:
            return HVACMode.HEAT
        elif cooling_enabled:
            return HVACMode.COOL
        else:
            return HVACMode.HEAT  # Default fallback

    # Per-circuit pump status params from the heat pump controller.
    # HPStatusCircPStat0 (1353) = circuit 1, HPStatusCircPStat1 (1354) = circuit 2, etc.
    _HP_CIRCUIT_PUMP_BASE = 1353

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action from heat pump controller state.

        Uses three HP status parameters instead of season/hysteresis logic:
        1. HPStatusCircPStat{N} -- per-circuit pump running (0=off, >0=on)
        2. HPStatusHdwHeatStat  -- DHW loading (circuits on standby)
        3. HPStatusWorkMode     -- heating (1) vs cooling (2) vs standby (0)
        """
        work_state = self._get_work_state()
        if work_state == CircuitWorkState.OFF:
            return HVACAction.OFF

        # Per-circuit pump status from HP controller
        pump_param = self.coordinator.get_param(
            str(self._HP_CIRCUIT_PUMP_BASE + self._circuit_num - 1)
        )
        if pump_param is not None and not int(pump_param.get("value", 0)):
            return HVACAction.IDLE

        # DHW loading means the heat source serves DHW, not circuits
        hdw_param = self.coordinator.get_param("1361")
        if hdw_param is not None and int(hdw_param.get("value", 0)) > 0:
            return HVACAction.IDLE

        # HP work mode: 0=standby, 1=heating, 2=cooling
        hp_mode_param = self.coordinator.get_param("1350")
        hp_mode = int(hp_mode_param.get("value", 0)) if hp_mode_param else 0
        if hp_mode == 2:
            return HVACAction.COOLING
        if hp_mode >= 1:
            return HVACAction.HEATING
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
            # Schedule mode - device follows schedule
            # Still detect active preset for display and temperature adjustment
            self._detect_active_preset()  # Updates _last_preset
            return PRESET_SCHEDULE
        return None

    def _detect_active_preset(self) -> str | None:
        """Detect which preset is currently active in AUTO mode by comparing setpoint."""
        # Get current room temperature setpoint (the target temp the system is using)
        setpoint_param = self.coordinator.get_param(self._room_temp_setpoint_param)
        if not setpoint_param:
            return None

        setpoint = setpoint_param.get("value")
        if setpoint is None:
            return None

        # Get eco and comfort temperatures
        eco_param = self.coordinator.get_param(self._eco_param)
        comfort_param = self.coordinator.get_param(self._comfort_param)

        if not eco_param or not comfort_param:
            return None

        eco_temp = eco_param.get("value")
        comfort_temp = comfort_param.get("value")

        if eco_temp is None or comfort_temp is None:
            return None

        # Compare setpoint to eco and comfort temps
        # Allow small tolerance for floating point comparison
        if abs(float(setpoint) - float(eco_temp)) < 0.1:
            self._last_preset = PRESET_ECO
            return PRESET_ECO
        elif abs(float(setpoint) - float(comfort_temp)) < 0.1:
            self._last_preset = PRESET_COMFORT
            return PRESET_COMFORT

        # If setpoint doesn't match either, return last known preset or default to comfort
        return self._last_preset if self._last_preset else PRESET_COMFORT

    def _get_work_state(self) -> int:
        """Get current work state value."""
        param = self.coordinator.get_param(self._work_state_param)
        if param:
            value = param.get("value")
            if value is not None:
                return int(value)
        return 0

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode by updating work state and heating/cooling enable bits."""
        if hvac_mode == HVACMode.OFF:
            # Turn off the circuit
            _LOGGER.debug("Setting Circuit %s to OFF", self._circuit_num)
            await self.coordinator.async_set_param(self._work_state_param, CircuitWorkState.OFF)
            return

        # For ON modes (HEAT/COOL/AUTO), update heating/cooling enable bits
        settings_param = self.coordinator.get_param(self._settings_param)
        if not settings_param:
            _LOGGER.error("Cannot set HVAC mode - settings parameter not found")
            return

        settings_value = int(settings_param.get("value", 0))

        # Determine desired heating/cooling state
        if hvac_mode == HVACMode.HEAT:
            heating_enabled = True
            cooling_enabled = False
        elif hvac_mode == HVACMode.COOL:
            heating_enabled = False
            cooling_enabled = True
        elif hvac_mode == HVACMode.AUTO:
            heating_enabled = True
            cooling_enabled = True
        else:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return

        # Update bit 20: heating enable (inverted: 0=on, 1=off)
        if heating_enabled:
            settings_value &= ~(1 << 20)  # Clear bit = ON
        else:
            settings_value |= 1 << 20  # Set bit = OFF

        # Update bit 17: cooling enable (0=off, 1=on)
        if cooling_enabled:
            settings_value |= 1 << 17  # Set bit = ON
        else:
            settings_value &= ~(1 << 17)  # Clear bit = OFF

        _LOGGER.debug(
            "Setting Circuit %s HVAC mode to %s (heating=%s, cooling=%s, settings=0x%X)",
            self._circuit_num,
            hvac_mode,
            heating_enabled,
            cooling_enabled,
            settings_value,
        )

        # Update settings parameter
        await self.coordinator.async_set_param(self._settings_param, settings_value)

        # Ensure circuit is turned on if it was off
        current_work_state = self._get_work_state()
        if current_work_state == CircuitWorkState.OFF:
            # Turn on with last preset or default to COMFORT
            if self._last_preset == PRESET_ECO:
                work_state = CircuitWorkState.ECO
            elif self._last_preset == PRESET_SCHEDULE:
                work_state = CircuitWorkState.AUTO
            else:
                work_state = CircuitWorkState.COMFORT
            _LOGGER.debug("Turning on Circuit %s with work_state=%s", self._circuit_num, work_state)
            await self.coordinator.async_set_param(self._work_state_param, work_state)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if preset_mode == PRESET_ECO:
            work_state = CircuitWorkState.ECO
        elif preset_mode == PRESET_COMFORT:
            work_state = CircuitWorkState.COMFORT
        elif preset_mode == PRESET_SCHEDULE:
            work_state = CircuitWorkState.AUTO
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
        """Set target temperature based on current preset."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # Determine which temperature parameter to update
        preset = self.preset_mode
        if preset == PRESET_SCHEDULE:
            # In schedule mode, update the currently active preset (eco or comfort)
            # _last_preset is updated by _detect_active_preset() in preset_mode property
            active_preset = self._last_preset if self._last_preset in (PRESET_ECO, PRESET_COMFORT) else PRESET_COMFORT
            param_id = self._comfort_param if active_preset == PRESET_COMFORT else self._eco_param
            _LOGGER.debug(
                "Setting Circuit %s %s temperature to %s°C (SCHEDULE mode, active: %s)",
                self._circuit_num,
                active_preset,
                temperature,
                active_preset,
            )
        elif preset == PRESET_COMFORT:
            param_id = self._comfort_param
            _LOGGER.debug(
                "Setting Circuit %s COMFORT temperature to %s°C",
                self._circuit_num,
                temperature,
            )
        elif preset == PRESET_ECO:
            param_id = self._eco_param
            _LOGGER.debug(
                "Setting Circuit %s ECO temperature to %s°C",
                self._circuit_num,
                temperature,
            )
        else:
            _LOGGER.warning(
                "Cannot set temperature - unable to determine active preset mode (preset=%s)",
                preset,
            )
            return

        await self.coordinator.async_set_param(param_id, float(temperature))
