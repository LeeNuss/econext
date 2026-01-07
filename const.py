"""Constants for the ecoNET Next integration."""

from dataclasses import dataclass
from enum import StrEnum

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
)

DOMAIN = "econet_next"

# Platforms to set up
PLATFORMS: list[str] = ["climate", "number", "select", "sensor", "switch"]

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Default values
DEFAULT_PORT = 8080

# API endpoints
API_ENDPOINT_ALL_PARAMS = "/econet/allParams"
API_ENDPOINT_NEW_PARAM = "/econet/newParam"

# Update interval in seconds
UPDATE_INTERVAL = 30

# Device info
MANUFACTURER = "Plum"

# Enum mappings
FLAP_VALVE_STATE_MAPPING: dict[int, str] = {
    0: "ch",  # Central Heating
    3: "dhw",  # Domestic Hot Water
}

FLAP_VALVE_STATE_OPTIONS: list[str] = ["ch", "dhw"]

# Operating mode - API parameter 162
OPERATING_MODE_MAPPING: dict[int, str] = {
    1: "summer",
    2: "winter",
    6: "auto",
}

OPERATING_MODE_OPTIONS: list[str] = list(OPERATING_MODE_MAPPING.values())


# Reverse mapping for setting values
OPERATING_MODE_REVERSE: dict[str, int] = {v: k for k, v in OPERATING_MODE_MAPPING.items()}

# Silent mode level - API parameter 1385
SILENT_MODE_LEVEL_MAPPING: dict[int, str] = {
    0: "level_1",
    2: "level_2",
}

SILENT_MODE_LEVEL_OPTIONS: list[str] = list(SILENT_MODE_LEVEL_MAPPING.values())

SILENT_MODE_LEVEL_REVERSE: dict[str, int] = {v: k for k, v in SILENT_MODE_LEVEL_MAPPING.items()}

# Silent mode schedule - API parameter 1386
SILENT_MODE_SCHEDULE_MAPPING: dict[int, str] = {
    0: "off",
    2: "schedule",
}

SILENT_MODE_SCHEDULE_OPTIONS: list[str] = list(SILENT_MODE_SCHEDULE_MAPPING.values())

SILENT_MODE_SCHEDULE_REVERSE: dict[str, int] = {v: k for k, v in SILENT_MODE_SCHEDULE_MAPPING.items()}

# DHW mode - API parameter 119
DHW_MODE_MAPPING: dict[int, str] = {
    0: "off",
    1: "on",
    2: "schedule",
}

DHW_MODE_OPTIONS: list[str] = list(DHW_MODE_MAPPING.values())
DHW_MODE_REVERSE: dict[str, int] = {v: k for k, v in DHW_MODE_MAPPING.items()}

# Legionella day - API parameter 137
LEGIONELLA_DAY_MAPPING: dict[int, str] = {
    0: "sunday",
    1: "monday",
    2: "tuesday",
    3: "wednesday",
    4: "thursday",
    5: "friday",
    6: "saturday",
}

LEGIONELLA_DAY_OPTIONS: list[str] = list(LEGIONELLA_DAY_MAPPING.values())
LEGIONELLA_DAY_REVERSE: dict[str, int] = {v: k for k, v in LEGIONELLA_DAY_MAPPING.items()}


class DeviceType(StrEnum):
    """Device types in the integration."""

    CONTROLLER = "controller"
    DHW = "dhw"
    BUFFER = "buffer"
    CIRCUIT = "circuit"
    HEATPUMP = "heatpump"


@dataclass(frozen=True)
class EconetSensorEntityDescription:
    """Describes an Econet sensor entity."""

    key: str  # Translation key
    param_id: str  # Parameter ID from API
    device_type: DeviceType = DeviceType.CONTROLLER
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    native_unit_of_measurement: str | None = None
    entity_category: EntityCategory | None = None
    icon: str | None = None
    precision: int | None = None
    options: list[str] | None = None  # For enum sensors
    value_map: dict[int, str] | None = None  # Map raw values to enum strings
    param_id_am: str | None = None  # For schedule diagnostic sensors - AM param
    param_id_pm: str | None = None  # For schedule diagnostic sensors - PM param


@dataclass(frozen=True)
class EconetNumberEntityDescription:
    """Describes an Econet number entity."""

    key: str  # Translation key
    param_id: str  # Parameter ID from API
    device_type: DeviceType = DeviceType.CONTROLLER
    native_unit_of_measurement: str | None = None
    entity_category: EntityCategory | None = None
    icon: str | None = None
    native_min_value: float | None = None  # Static min value
    native_max_value: float | None = None  # Static max value
    native_step: float = 1.0
    min_value_param_id: str | None = None  # Dynamic min from another param's value
    max_value_param_id: str | None = None  # Dynamic max from another param's value


@dataclass(frozen=True)
class EconetSelectEntityDescription:
    """Describes an Econet select entity."""

    key: str  # Translation key
    param_id: str  # Parameter ID from API
    device_type: DeviceType = DeviceType.CONTROLLER
    entity_category: EntityCategory | None = None
    icon: str | None = None
    options: list[str] = None  # Available options
    value_map: dict[int, str] = None  # Map API values to option strings
    reverse_map: dict[str, int] = None  # Map option strings to API values


@dataclass(frozen=True)
class EconetSwitchEntityDescription:
    """Describes an Econet switch entity."""

    key: str  # Translation key
    param_id: str  # Parameter ID from API
    device_type: DeviceType = DeviceType.CONTROLLER
    entity_category: EntityCategory | None = None
    icon: str | None = None
    bit_position: int | None = None  # For bitmap-based switches
    invert_logic: bool = False  # If True, bit=0 means ON, bit=1 means OFF


# Controller sensors - read only
CONTROLLER_SENSORS: tuple[EconetSensorEntityDescription, ...] = (
    # System information (diagnostic)
    EconetSensorEntityDescription(
        key="software_version",
        param_id="0",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
    ),
    EconetSensorEntityDescription(
        key="hardware_version",
        param_id="1",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
    ),
    EconetSensorEntityDescription(
        key="uid",
        param_id="10",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    EconetSensorEntityDescription(
        key="device_name",
        param_id="374",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:label-outline",
    ),
    EconetSensorEntityDescription(
        key="compilation_date",
        param_id="13",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar",
    ),
    EconetSensorEntityDescription(
        key="reset_counter",
        param_id="14",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
    ),
    # System state sensors
    EconetSensorEntityDescription(
        key="outdoor_temperature",
        param_id="68",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        precision=1,
    ),
    EconetSensorEntityDescription(
        key="flap_valve_state",
        param_id="83",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:valve",
        options=FLAP_VALVE_STATE_OPTIONS,
        value_map=FLAP_VALVE_STATE_MAPPING,
    ),
    # Network info (diagnostic)
    EconetSensorEntityDescription(
        key="wifi_ssid",
        param_id="377",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi",
    ),
    EconetSensorEntityDescription(
        key="wifi_signal_strength",
        param_id="380",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi-strength-3",
    ),
    EconetSensorEntityDescription(
        key="wifi_ip_address",
        param_id="860",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network",
    ),
    EconetSensorEntityDescription(
        key="lan_ip_address",
        param_id="863",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network",
    ),
    # I/O state sensors (diagnostic)
    EconetSensorEntityDescription(
        key="outputs",
        param_id="81",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:export",
    ),
    EconetSensorEntityDescription(
        key="inputs",
        param_id="82",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:import",
    ),
    # Work state sensors (diagnostic)
    # Note: work_state_2 (param 162) is exposed as operating_mode select entity
    EconetSensorEntityDescription(
        key="work_state_1",
        param_id="161",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
    ),
    EconetSensorEntityDescription(
        key="work_state_3",
        param_id="163",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
    ),
    EconetSensorEntityDescription(
        key="work_state_4",
        param_id="164",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
    ),
    # Alarm sensors (diagnostic)
    EconetSensorEntityDescription(
        key="alarm_bits_1",
        param_id="1042",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
    ),
    EconetSensorEntityDescription(
        key="alarm_bits_2",
        param_id="1043",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
    ),
    EconetSensorEntityDescription(
        key="alarm_bits_3",
        param_id="1044",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
    ),
    EconetSensorEntityDescription(
        key="alarm_bits_4",
        param_id="1045",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
    ),
    EconetSensorEntityDescription(
        key="alarm_bits_5",
        param_id="1046",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
    ),
)


# Controller number entities - editable global settings
CONTROLLER_NUMBERS: tuple[EconetNumberEntityDescription, ...] = (
    # Summer mode settings - limits are automatically read from allParams (minv/maxv/minvDP/maxvDP)
    EconetNumberEntityDescription(
        key="summer_mode_on",
        param_id="702",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:weather-sunny",
        native_min_value=22,  # Fallback only
        native_max_value=30,  # Fallback only
    ),
    EconetNumberEntityDescription(
        key="summer_mode_off",
        param_id="703",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:weather-sunny-off",
        native_min_value=0,  # Fallback only
        native_max_value=24,  # Fallback only
    ),
)


# Controller select entities - editable mode settings
CONTROLLER_SELECTS: tuple[EconetSelectEntityDescription, ...] = (
    EconetSelectEntityDescription(
        key="operating_mode",
        param_id="162",
        icon="mdi:sun-snowflake-variant",
        options=OPERATING_MODE_OPTIONS,
        value_map=OPERATING_MODE_MAPPING,
        reverse_map=OPERATING_MODE_REVERSE,
    ),
    EconetSelectEntityDescription(
        key="silent_mode_level",
        param_id="1385",
        icon="mdi:volume-low",
        options=SILENT_MODE_LEVEL_OPTIONS,
        value_map=SILENT_MODE_LEVEL_MAPPING,
        reverse_map=SILENT_MODE_LEVEL_REVERSE,
    ),
    EconetSelectEntityDescription(
        key="silent_mode_schedule",
        param_id="1386",
        icon="mdi:calendar-clock",
        options=SILENT_MODE_SCHEDULE_OPTIONS,
        value_map=SILENT_MODE_SCHEDULE_MAPPING,
        reverse_map=SILENT_MODE_SCHEDULE_REVERSE,
    ),
)


# Controller switch entities - boolean settings
CONTROLLER_SWITCHES: tuple[EconetSwitchEntityDescription, ...] = (
    # Cooling support toggle - enables cooling mode in addition to heating
    EconetSwitchEntityDescription(
        key="cooling_support",
        param_id="485",
        icon="mdi:snowflake",
    ),
)


# ============================================================================
# DHW (Domestic Hot Water) Device
# ============================================================================

# DHW sensors - read only
DHW_SENSORS: tuple[EconetSensorEntityDescription, ...] = (
    # Temperature sensors
    EconetSensorEntityDescription(
        key="temperature",
        param_id="61",
        device_type=DeviceType.DHW,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        precision=1,
    ),
    EconetSensorEntityDescription(
        key="setpoint_calculated",
        param_id="134",
        device_type=DeviceType.DHW,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-auto",
        precision=0,
    ),
    # Boost time remaining
    EconetSensorEntityDescription(
        key="boost_time_remaining",
        param_id="1431",
        device_type=DeviceType.DHW,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="min",
        icon="mdi:timer-sand",
        precision=0,
    ),
)


# DHW number entities - editable settings
DHW_NUMBERS: tuple[EconetNumberEntityDescription, ...] = (
    # DHW target temperature
    EconetNumberEntityDescription(
        key="target_temperature",
        param_id="103",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        native_min_value=35,
        native_max_value=65,
    ),
    # DHW hysteresis
    EconetNumberEntityDescription(
        key="hysteresis",
        param_id="104",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-lines",
        native_min_value=5,
        native_max_value=18,
    ),
    # DHW max temperature
    EconetNumberEntityDescription(
        key="max_temperature",
        param_id="108",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        native_min_value=0,
        native_max_value=75,
    ),
    # DHW max temp hysteresis
    EconetNumberEntityDescription(
        key="max_temp_hysteresis",
        param_id="112",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-lines",
        native_min_value=0,
        native_max_value=10,
    ),
    # DHW load time
    EconetNumberEntityDescription(
        key="load_time",
        param_id="113",
        device_type=DeviceType.DHW,
        icon="mdi:timer",
        native_min_value=0,
        native_max_value=50,
    ),
    # Legionella settings
    EconetNumberEntityDescription(
        key="legionella_temperature",
        param_id="136",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:bacteria",
        native_min_value=60,
        native_max_value=80,
    ),
    EconetNumberEntityDescription(
        key="legionella_hour",
        param_id="138",
        device_type=DeviceType.DHW,
        icon="mdi:clock",
        native_min_value=0,
        native_max_value=23,
    ),
)


# DHW schedule entities - bitfield for 30-minute time slots
# Generated programmatically to reduce repetition
_DHW_SCHEDULE_DAYS = [
    ("sunday", 120, 121),
    ("monday", 122, 123),
    ("tuesday", 124, 125),
    ("wednesday", 126, 127),
    ("thursday", 128, 129),
    ("friday", 130, 131),
    ("saturday", 132, 133),
]

DHW_SCHEDULE_NUMBERS: tuple[EconetNumberEntityDescription, ...] = tuple(
    EconetNumberEntityDescription(
        key=f"hdw_schedule_{day}_{period}",
        param_id=str(param_id),
        device_type=DeviceType.DHW,
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=4294967295,
        native_step=1,
    )
    for day, am_id, pm_id in _DHW_SCHEDULE_DAYS
    for period, param_id in [("am", am_id), ("pm", pm_id)]
)


# DHW schedule diagnostic sensors - decoded time ranges (one per day, combines AM/PM)
DHW_SCHEDULE_DIAGNOSTIC_SENSORS: tuple[EconetSensorEntityDescription, ...] = tuple(
    EconetSensorEntityDescription(
        key=f"hdw_schedule_{day}_decoded",
        param_id=str(am_id),  # Use AM param as primary param_id
        param_id_am=str(am_id),
        param_id_pm=str(pm_id),
        device_type=DeviceType.DHW,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    for day, am_id, pm_id in _DHW_SCHEDULE_DAYS
)


# DHW switch entities
DHW_SWITCHES: tuple[EconetSwitchEntityDescription, ...] = (
    # Boost - start/stop immediate DHW heating
    EconetSwitchEntityDescription(
        key="boost",
        param_id="115",
        device_type=DeviceType.DHW,
        icon="mdi:rocket-launch",
    ),
    # Legionella protection
    EconetSwitchEntityDescription(
        key="legionella_start",
        param_id="135",
        device_type=DeviceType.DHW,
        icon="mdi:bacteria",
    ),
)


# DHW select entities
DHW_SELECTS: tuple[EconetSelectEntityDescription, ...] = (
    # DHW mode (off/on/schedule)
    EconetSelectEntityDescription(
        key="mode",
        param_id="119",
        device_type=DeviceType.DHW,
        icon="mdi:water-boiler",
        options=DHW_MODE_OPTIONS,
        value_map=DHW_MODE_MAPPING,
        reverse_map=DHW_MODE_REVERSE,
    ),
    # Legionella protection day
    EconetSelectEntityDescription(
        key="legionella_day",
        param_id="137",
        device_type=DeviceType.DHW,
        icon="mdi:calendar",
        options=LEGIONELLA_DAY_OPTIONS,
        value_map=LEGIONELLA_DAY_MAPPING,
        reverse_map=LEGIONELLA_DAY_REVERSE,
    ),
)


# ============================================================================
# Circuit (Heating Zones) Devices - Circuits 1-7
# ============================================================================

# Circuit type mapping (CircuitXTypeSettings parameter)
CIRCUIT_TYPE_MAPPING = {
    1: "radiator",
    2: "ufh",  # Underfloor heating
    3: "fan_coil",
}

CIRCUIT_TYPE_OPTIONS = list(CIRCUIT_TYPE_MAPPING.values())

CIRCUIT_TYPE_REVERSE = {value: key for key, value in CIRCUIT_TYPE_MAPPING.items()}

# Circuit sensors - read only temperature sensors
# Note: These use a function-based approach since each circuit has the same pattern
# Circuit-specific param IDs are defined in climate.py CIRCUITS dict

# Circuit temperature sensors (per circuit)
CIRCUIT_SENSORS: tuple[EconetSensorEntityDescription, ...] = (
    # Room thermostat temperature
    EconetSensorEntityDescription(
        key="thermostat_temp",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        precision=1,
    ),
    # Calculated target temperature
    EconetSensorEntityDescription(
        key="calc_temp",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-auto",
        precision=1,
    ),
    # Room temperature setpoint
    EconetSensorEntityDescription(
        key="room_temp_setpoint",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:target",
        precision=1,
    ),
)


# Circuit number entities - editable settings
CIRCUIT_NUMBERS: tuple[EconetNumberEntityDescription, ...] = (
    # Comfort temperature
    EconetNumberEntityDescription(
        key="comfort_temp",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:sun-thermometer",
        native_min_value=10.0,
        native_max_value=35.0,
        native_step=0.5,
    ),
    # Eco temperature
    EconetNumberEntityDescription(
        key="eco_temp",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:leaf",
        native_min_value=10.0,
        native_max_value=35.0,
        native_step=0.5,
    ),
    # Temperature hysteresis
    EconetNumberEntityDescription(
        key="hysteresis",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-lines",
        native_min_value=0.0,
        native_max_value=5.0,
        native_step=0.5,
    ),
    # Max radiator temperature
    EconetNumberEntityDescription(
        key="max_temp_radiator",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        native_min_value=0,
        native_max_value=75,
    ),
    # Max heating temperature
    EconetNumberEntityDescription(
        key="max_temp_heat",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        native_min_value=30,
        native_max_value=55,
    ),
    # Base temperature
    EconetNumberEntityDescription(
        key="base_temp",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        native_min_value=24,
        native_max_value=75,
    ),
    # Temperature reduction
    EconetNumberEntityDescription(
        key="temp_reduction",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-minus",
        native_min_value=0,
        native_max_value=20,
    ),
    # Heating curve - dynamically uses radiator, floor, or fan coil param based on circuit type
    EconetNumberEntityDescription(
        key="heating_curve",
        param_id="",  # Set dynamically per circuit type
        device_type=DeviceType.CIRCUIT,
        icon="mdi:chart-line",
        native_min_value=0.0,
        native_max_value=4.0,
        native_step=0.1,
    ),
    # Curve shift
    EconetNumberEntityDescription(
        key="curve_shift",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        icon="mdi:arrow-up-down",
        native_min_value=-20,
        native_max_value=20,
    ),
    # Room temperature correction
    EconetNumberEntityDescription(
        key="room_temp_correction",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:tune",
        native_min_value=-10,
        native_max_value=10,
    ),
    # Cooling min setpoint temperature
    EconetNumberEntityDescription(
        key="min_setpoint_cooling",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:snowflake-thermometer",
        native_min_value=0,
        native_max_value=30,
    ),
    # Cooling max setpoint temperature
    EconetNumberEntityDescription(
        key="max_setpoint_cooling",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:snowflake-thermometer",
        native_min_value=0,
        native_max_value=30,
    ),
    # Cooling base temperature
    EconetNumberEntityDescription(
        key="cooling_base_temp",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:snowflake",
        native_min_value=0,
        native_max_value=30,
    ),
)


# Circuit select entities - editable mode selections
CIRCUIT_SELECTS: tuple[EconetSelectEntityDescription, ...] = (
    # Circuit type (radiator, UFH, or fan coil)
    EconetSelectEntityDescription(
        key="circuit_type",
        param_id="",  # Set dynamically per circuit (CircuitXTypeSettings)
        device_type=DeviceType.CIRCUIT,
        icon="mdi:heating-coil",
        options=CIRCUIT_TYPE_OPTIONS,
        value_map=CIRCUIT_TYPE_MAPPING,
        reverse_map=CIRCUIT_TYPE_REVERSE,
    ),
)


# Circuit switch entities - bitmap-based settings
CIRCUIT_SWITCHES: tuple[EconetSwitchEntityDescription, ...] = (
    # Heating enable (bit 20, inverted: 0=on, 1=off)
    EconetSwitchEntityDescription(
        key="heating_enable",
        param_id="",  # Set dynamically per circuit (CircuitXSettings)
        device_type=DeviceType.CIRCUIT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:radiator",
        bit_position=20,
        invert_logic=True,  # Bit 0 = heating ON
    ),
    # Cooling enable (bit 17)
    EconetSwitchEntityDescription(
        key="cooling_enable",
        param_id="",  # Set dynamically per circuit (CircuitXSettings)
        device_type=DeviceType.CIRCUIT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:snowflake",
        bit_position=17,
        invert_logic=False,  # Bit 1 = cooling ON
    ),
    # Pump only mode (bit 13)
    EconetSwitchEntityDescription(
        key="pump_only_mode",
        param_id="",  # Set dynamically per circuit (CircuitXSettings)
        device_type=DeviceType.CIRCUIT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:pump",
        bit_position=13,
        invert_logic=False,  # Bit 1 = pump only ON
    ),
    # Pump blockage (bit 10)
    EconetSwitchEntityDescription(
        key="pump_blockage",
        param_id="",  # Set dynamically per circuit (CircuitXSettings)
        device_type=DeviceType.CIRCUIT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:pump-off",
        bit_position=10,
        invert_logic=False,  # Bit 1 = blockage ON
    ),
)
