"""Constants for the ecoNEXT integration."""

from dataclasses import dataclass
from enum import StrEnum

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
)

DOMAIN = "econext"

# Platforms to set up
PLATFORMS: list[str] = [
    "binary_sensor",
    "button",
    "climate",
    "number",
    "select",
    "sensor",
    "switch",
]

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"

# Default values
DEFAULT_PORT = 8000

# API endpoints
API_ENDPOINT_PARAMETERS = "/api/parameters"
API_ENDPOINT_ALARMS = "/api/alarms"

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

# Current active mode - API parameter 161 (read-only, shows actual mode when in auto)
ACTIVE_MODE_MAPPING: dict[int, str] = {
    1: "summer",
    2: "winter",
}

ACTIVE_MODE_OPTIONS: list[str] = list(ACTIVE_MODE_MAPPING.values())

# Active preset mode - for circuits in schedule mode (read-only, computed)
ACTIVE_PRESET_MODE_OPTIONS: list[str] = ["eco", "comfort"]

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

# Heat pump work mode - API parameter 1133
HEATPUMP_WORK_MODE_MAPPING: dict[int, str] = {
    0: "off",
    1: "on",
    2: "schedule",
}

HEATPUMP_WORK_MODE_OPTIONS: list[str] = list(HEATPUMP_WORK_MODE_MAPPING.values())

HEATPUMP_WORK_MODE_REVERSE: dict[str, int] = {v: k for k, v in HEATPUMP_WORK_MODE_MAPPING.items()}

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

# Alarm code to description mapping
ALARM_CODE_NAMES: dict[int, str] = {
    10: "Antifreeze",
    148: "Water flow failure",
}


def get_alarm_name(code: int) -> str:
    """Get human-readable alarm name, falling back to code number."""
    return ALARM_CODE_NAMES.get(code, f"Alarm code {code} (UNKNOWN)")


class DeviceType(StrEnum):
    """Device types in the integration."""

    CONTROLLER = "controller"
    DHW = "dhw"
    BUFFER = "buffer"
    CIRCUIT = "circuit"
    HEATPUMP = "heatpump"


@dataclass(frozen=True)
class EconextSensorEntityDescription:
    """Describes an Econext sensor entity."""

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
class EconextNumberEntityDescription:
    """Describes an Econext number entity."""

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
class EconextSelectEntityDescription:
    """Describes an Econext select entity."""

    key: str  # Translation key
    param_id: str  # Parameter ID from API
    device_type: DeviceType = DeviceType.CONTROLLER
    entity_category: EntityCategory | None = None
    icon: str | None = None
    options: list[str] = None  # Available options
    value_map: dict[int, str] = None  # Map API values to option strings
    reverse_map: dict[str, int] = None  # Map option strings to API values


@dataclass(frozen=True)
class EconextSwitchEntityDescription:
    """Describes an Econext switch entity."""

    key: str  # Translation key
    param_id: str  # Parameter ID from API
    device_type: DeviceType = DeviceType.CONTROLLER
    entity_category: EntityCategory | None = None
    icon: str | None = None
    bit_position: int | None = None  # For bitmap-based switches
    invert_logic: bool = False  # If True, bit=0 means ON, bit=1 means OFF


@dataclass(frozen=True)
class EconextButtonEntityDescription:
    """Describes an Econext button entity."""

    key: str  # Translation key
    param_id: str  # Parameter ID from API
    device_type: DeviceType = DeviceType.CONTROLLER
    entity_category: EntityCategory | None = None
    icon: str | None = None


# Controller sensors - read only
CONTROLLER_SENSORS: tuple[EconextSensorEntityDescription, ...] = (
    # System information (diagnostic)
    EconextSensorEntityDescription(
        key="software_version",
        param_id="0",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
    ),
    EconextSensorEntityDescription(
        key="hardware_version",
        param_id="1",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
    ),
    EconextSensorEntityDescription(
        key="uid",
        param_id="10",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    EconextSensorEntityDescription(
        key="device_name",
        param_id="374",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:label-outline",
    ),
    EconextSensorEntityDescription(
        key="compilation_date",
        param_id="13",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar",
    ),
    EconextSensorEntityDescription(
        key="reset_counter",
        param_id="14",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
    ),
    # System state sensors
    EconextSensorEntityDescription(
        key="outdoor_temperature",
        param_id="68",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        precision=1,
    ),
    EconextSensorEntityDescription(
        key="flap_valve_state",
        param_id="83",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:valve",
        options=FLAP_VALVE_STATE_OPTIONS,
        value_map=FLAP_VALVE_STATE_MAPPING,
    ),
    # Network info (diagnostic)
    EconextSensorEntityDescription(
        key="wifi_ssid",
        param_id="377",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi",
    ),
    EconextSensorEntityDescription(
        key="wifi_signal_strength",
        param_id="380",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi-strength-3",
    ),
    EconextSensorEntityDescription(
        key="wifi_ip_address",
        param_id="860",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network",
    ),
    EconextSensorEntityDescription(
        key="lan_ip_address",
        param_id="863",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network",
    ),
    # I/O state sensors (diagnostic)
    EconextSensorEntityDescription(
        key="outputs",
        param_id="81",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:export",
    ),
    EconextSensorEntityDescription(
        key="inputs",
        param_id="82",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:import",
    ),
    # Work state sensors (diagnostic)
    # Note: work_state_2 (param 162) is exposed as operating_mode select entity
    EconextSensorEntityDescription(
        key="active_operating_mode",
        param_id="161",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sun-snowflake",
        options=ACTIVE_MODE_OPTIONS,
        value_map=ACTIVE_MODE_MAPPING,
    ),
    EconextSensorEntityDescription(
        key="work_state_3",
        param_id="163",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
    ),
    EconextSensorEntityDescription(
        key="work_state_4",
        param_id="164",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
    ),
)


# Controller number entities - editable global settings
CONTROLLER_NUMBERS: tuple[EconextNumberEntityDescription, ...] = (
    # Summer mode settings - limits are automatically read from allParams (minv/maxv/minvDP/maxvDP)
    EconextNumberEntityDescription(
        key="summer_mode_on",
        param_id="702",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:weather-sunny",
        native_min_value=22,  # Fallback only
        native_max_value=30,  # Fallback only
    ),
    EconextNumberEntityDescription(
        key="summer_mode_off",
        param_id="703",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:weather-sunny-off",
        native_min_value=0,  # Fallback only
        native_max_value=24,  # Fallback only
    ),
)


# Controller select entities - editable mode settings
CONTROLLER_SELECTS: tuple[EconextSelectEntityDescription, ...] = (
    EconextSelectEntityDescription(
        key="operating_mode",
        param_id="162",
        icon="mdi:sun-snowflake-variant",
        options=OPERATING_MODE_OPTIONS,
        value_map=OPERATING_MODE_MAPPING,
        reverse_map=OPERATING_MODE_REVERSE,
    ),
)


# Controller switch entities - boolean settings
CONTROLLER_SWITCHES: tuple[EconextSwitchEntityDescription, ...] = (
    # Cooling support toggle - enables cooling mode in addition to heating
    EconextSwitchEntityDescription(
        key="cooling_support",
        param_id="485",
        icon="mdi:snowflake",
    ),
)


# ============================================================================
# Heat Pump Device
# ============================================================================

# Heat pump sensors - read only
HEATPUMP_SENSORS: tuple[EconextSensorEntityDescription, ...] = (
    EconextSensorEntityDescription(
        key="system_pressure",
        param_id="1208",
        device_type=DeviceType.HEATPUMP,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="bar",
        icon="mdi:gauge",
        precision=1,
    ),
    EconextSensorEntityDescription(
        key="pump_speed",
        param_id="1209",
        device_type=DeviceType.HEATPUMP,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:pump",
        precision=0,
    ),
    EconextSensorEntityDescription(
        key="compressor_frequency",
        param_id="1365",
        device_type=DeviceType.HEATPUMP,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="Hz",
        icon="mdi:sine-wave",
        precision=0,
    ),
    EconextSensorEntityDescription(
        key="water_flow_rate",
        param_id="612",
        device_type=DeviceType.HEATPUMP,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L/min",
        icon="mdi:water-pump",
        precision=1,
    ),
    EconextSensorEntityDescription(
        key="fan_speed",
        param_id="1366",
        device_type=DeviceType.HEATPUMP,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="rpm",
        icon="mdi:fan",
        precision=1,
    ),
    EconextSensorEntityDescription(
        key="target_temperature",
        param_id="523",
        device_type=DeviceType.HEATPUMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-auto",
        precision=0,
    ),
)


# Heat pump number entities - adjustable values
HEATPUMP_NUMBERS: tuple[EconextNumberEntityDescription, ...] = (
    EconextNumberEntityDescription(
        key="purge_pwm_speed",
        param_id="1370",
        device_type=DeviceType.HEATPUMP,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:pump",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
    ),
    EconextNumberEntityDescription(
        key="standby_pump_speed",
        param_id="1439",
        device_type=DeviceType.HEATPUMP,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:pump",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
    ),
    EconextNumberEntityDescription(
        key="min_pump_speed",
        param_id="1440",
        device_type=DeviceType.HEATPUMP,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:pump",
        native_min_value=31,
        native_max_value=100,
        native_step=1,
    ),
    EconextNumberEntityDescription(
        key="max_pump_speed",
        param_id="1441",
        device_type=DeviceType.HEATPUMP,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:pump",
        native_min_value=50,
        native_max_value=100,
        native_step=1,
    ),
    EconextNumberEntityDescription(
        key="fan_speed_0",
        param_id="1443",
        device_type=DeviceType.HEATPUMP,
        native_unit_of_measurement="RPM",
        icon="mdi:fan",
        native_min_value=0,
        native_max_value=1000,
        native_step=10,
    ),
    EconextNumberEntityDescription(
        key="fan_speed_1",
        param_id="1444",
        device_type=DeviceType.HEATPUMP,
        native_unit_of_measurement="RPM",
        icon="mdi:fan",
        native_min_value=0,
        native_max_value=1000,
        native_step=10,
    ),
    EconextNumberEntityDescription(
        key="fan_speed_2",
        param_id="1445",
        device_type=DeviceType.HEATPUMP,
        native_unit_of_measurement="RPM",
        icon="mdi:fan",
        native_min_value=0,
        native_max_value=1000,
        native_step=10,
    ),
    EconextNumberEntityDescription(
        key="fan_speed_3",
        param_id="1446",
        device_type=DeviceType.HEATPUMP,
        native_unit_of_measurement="RPM",
        icon="mdi:fan",
        native_min_value=0,
        native_max_value=1000,
        native_step=10,
    ),
)


# Heat pump select entities - editable mode settings
HEATPUMP_SELECTS: tuple[EconextSelectEntityDescription, ...] = (
    EconextSelectEntityDescription(
        key="work_mode",
        param_id="1133",
        device_type=DeviceType.HEATPUMP,
        icon="mdi:power",
        options=HEATPUMP_WORK_MODE_OPTIONS,
        value_map=HEATPUMP_WORK_MODE_MAPPING,
        reverse_map=HEATPUMP_WORK_MODE_REVERSE,
    ),
    EconextSelectEntityDescription(
        key="silent_mode_level",
        param_id="1385",
        device_type=DeviceType.HEATPUMP,
        icon="mdi:volume-low",
        options=SILENT_MODE_LEVEL_OPTIONS,
        value_map=SILENT_MODE_LEVEL_MAPPING,
        reverse_map=SILENT_MODE_LEVEL_REVERSE,
    ),
    EconextSelectEntityDescription(
        key="silent_mode_schedule",
        param_id="1386",
        device_type=DeviceType.HEATPUMP,
        icon="mdi:calendar-clock",
        options=SILENT_MODE_SCHEDULE_OPTIONS,
        value_map=SILENT_MODE_SCHEDULE_MAPPING,
        reverse_map=SILENT_MODE_SCHEDULE_REVERSE,
    ),
)


# Heat pump button entities - actions
HEATPUMP_BUTTONS: tuple[EconextButtonEntityDescription, ...] = (
    EconextButtonEntityDescription(
        key="reboot",
        param_id="1369",
        device_type=DeviceType.HEATPUMP,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:restart",
    ),
)


# Heat pump switch entities
HEATPUMP_SWITCHES: tuple[EconextSwitchEntityDescription, ...] = (
    # Manual defrost - bit 0 of AXEN_REGISTER_2103_RW
    EconextSwitchEntityDescription(
        key="manual_defrost",
        param_id="1271",
        device_type=DeviceType.HEATPUMP,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:snowflake-melt",
        bit_position=0,
        invert_logic=False,  # 1 = enabled, 0 = disabled
    ),
    # Purge function - bit 14 of AXEN_REGISTER_2103_RW
    EconextSwitchEntityDescription(
        key="purge_enable",
        param_id="1271",
        device_type=DeviceType.HEATPUMP,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:air-purifier",
        bit_position=14,
        invert_logic=False,  # 1 = enabled, 0 = disabled
    ),
)


# Silent mode schedule entities - bitfield for 30-minute time slots
# Generated programmatically to reduce repetition
_SILENT_MODE_SCHEDULE_DAYS = [
    ("sunday", 1387, 1388),
    ("monday", 1389, 1390),
    ("tuesday", 1391, 1392),
    ("wednesday", 1393, 1394),
    ("thursday", 1395, 1396),
    ("friday", 1397, 1398),
    ("saturday", 1399, 1400),
]

SILENT_MODE_SCHEDULE_NUMBERS: tuple[EconextNumberEntityDescription, ...] = tuple(
    EconextNumberEntityDescription(
        key=f"silent_mode_schedule_{day}_{period}",
        param_id=str(param_id),
        device_type=DeviceType.HEATPUMP,
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=4294967295,
        native_step=1,
    )
    for day, am_id, pm_id in _SILENT_MODE_SCHEDULE_DAYS
    for period, param_id in [("am", am_id), ("pm", pm_id)]
)


# Silent mode schedule diagnostic sensors - decoded time ranges (one per day, combines AM/PM)
SILENT_MODE_SCHEDULE_DIAGNOSTIC_SENSORS: tuple[EconextSensorEntityDescription, ...] = tuple(
    EconextSensorEntityDescription(
        key=f"silent_mode_schedule_{day}_decoded",
        param_id=str(am_id),  # Use AM param as primary param_id
        param_id_am=str(am_id),
        param_id_pm=str(pm_id),
        device_type=DeviceType.HEATPUMP,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    for day, am_id, pm_id in _SILENT_MODE_SCHEDULE_DAYS
)


# Heat pump schedule entities - bitfield for 30-minute time slots
# Generated programmatically to reduce repetition
_HEATPUMP_SCHEDULE_DAYS = [
    ("sunday", 926, 927),
    ("monday", 928, 929),
    ("tuesday", 930, 931),
    ("wednesday", 932, 933),
    ("thursday", 934, 935),
    ("friday", 936, 937),
    ("saturday", 938, 939),
]

HEATPUMP_SCHEDULE_NUMBERS: tuple[EconextNumberEntityDescription, ...] = tuple(
    EconextNumberEntityDescription(
        key=f"heatpump_schedule_{day}_{period}",
        param_id=str(param_id),
        device_type=DeviceType.HEATPUMP,
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=4294967295,
        native_step=1,
    )
    for day, am_id, pm_id in _HEATPUMP_SCHEDULE_DAYS
    for period, param_id in [("am", am_id), ("pm", pm_id)]
)


# Heat pump schedule diagnostic sensors - decoded time ranges (one per day, combines AM/PM)
HEATPUMP_SCHEDULE_DIAGNOSTIC_SENSORS: tuple[EconextSensorEntityDescription, ...] = tuple(
    EconextSensorEntityDescription(
        key=f"heatpump_schedule_{day}_decoded",
        param_id=str(am_id),  # Use AM param as primary param_id
        param_id_am=str(am_id),
        param_id_pm=str(pm_id),
        device_type=DeviceType.HEATPUMP,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    for day, am_id, pm_id in _HEATPUMP_SCHEDULE_DAYS
)


# ============================================================================
# DHW (Domestic Hot Water) Device
# ============================================================================

# DHW sensors - read only
DHW_SENSORS: tuple[EconextSensorEntityDescription, ...] = (
    # Temperature sensors
    EconextSensorEntityDescription(
        key="temperature",
        param_id="61",
        device_type=DeviceType.DHW,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        precision=1,
    ),
    EconextSensorEntityDescription(
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
    EconextSensorEntityDescription(
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
DHW_NUMBERS: tuple[EconextNumberEntityDescription, ...] = (
    # DHW target temperature
    EconextNumberEntityDescription(
        key="target_temperature",
        param_id="103",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        native_min_value=35,
        native_max_value=65,
    ),
    # DHW hysteresis
    EconextNumberEntityDescription(
        key="hysteresis",
        param_id="104",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-lines",
        native_min_value=5,
        native_max_value=18,
    ),
    # DHW max temperature
    EconextNumberEntityDescription(
        key="max_temperature",
        param_id="108",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        native_min_value=0,
        native_max_value=75,
    ),
    # DHW max temp hysteresis
    EconextNumberEntityDescription(
        key="max_temp_hysteresis",
        param_id="112",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-lines",
        native_min_value=0,
        native_max_value=10,
    ),
    # DHW load time
    EconextNumberEntityDescription(
        key="load_time",
        param_id="113",
        device_type=DeviceType.DHW,
        icon="mdi:timer",
        native_min_value=0,
        native_max_value=50,
    ),
    # Legionella settings
    EconextNumberEntityDescription(
        key="legionella_temperature",
        param_id="136",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:bacteria",
        native_min_value=60,
        native_max_value=80,
    ),
    EconextNumberEntityDescription(
        key="legionella_hour",
        param_id="138",
        device_type=DeviceType.DHW,
        icon="mdi:clock",
        native_min_value=0,
        native_max_value=23,
    ),
    # DHW temperature correction
    EconextNumberEntityDescription(
        key="temperature_correction",
        param_id="481",
        device_type=DeviceType.DHW,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-plus",
        native_min_value=0,
        native_max_value=20,
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

DHW_SCHEDULE_NUMBERS: tuple[EconextNumberEntityDescription, ...] = tuple(
    EconextNumberEntityDescription(
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
DHW_SCHEDULE_DIAGNOSTIC_SENSORS: tuple[EconextSensorEntityDescription, ...] = tuple(
    EconextSensorEntityDescription(
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
DHW_SWITCHES: tuple[EconextSwitchEntityDescription, ...] = (
    # Boost - start/stop immediate DHW heating
    EconextSwitchEntityDescription(
        key="boost",
        param_id="115",
        device_type=DeviceType.DHW,
        icon="mdi:rocket-launch",
    ),
    # Legionella protection
    EconextSwitchEntityDescription(
        key="legionella_start",
        param_id="135",
        device_type=DeviceType.DHW,
        icon="mdi:bacteria",
    ),
)


# DHW select entities
DHW_SELECTS: tuple[EconextSelectEntityDescription, ...] = (
    # DHW mode (off/on/schedule)
    EconextSelectEntityDescription(
        key="mode",
        param_id="119",
        device_type=DeviceType.DHW,
        icon="mdi:water-boiler",
        options=DHW_MODE_OPTIONS,
        value_map=DHW_MODE_MAPPING,
        reverse_map=DHW_MODE_REVERSE,
    ),
    # Legionella protection day
    EconextSelectEntityDescription(
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
CIRCUIT_SENSORS: tuple[EconextSensorEntityDescription, ...] = (
    # Room thermostat temperature
    EconextSensorEntityDescription(
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
    EconextSensorEntityDescription(
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
    EconextSensorEntityDescription(
        key="room_temp_setpoint",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:target",
        precision=1,
    ),
    # Active preset mode (eco/comfort) - computed by comparing setpoint to eco/comfort temps
    EconextSensorEntityDescription(
        key="active_preset_mode",
        param_id="",  # Set dynamically - uses room_temp_setpoint as primary param
        device_type=DeviceType.CIRCUIT,
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-clock",
        options=ACTIVE_PRESET_MODE_OPTIONS,
    ),
)


# Circuit number entities - editable settings
CIRCUIT_NUMBERS: tuple[EconextNumberEntityDescription, ...] = (
    # Comfort temperature
    EconextNumberEntityDescription(
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
    EconextNumberEntityDescription(
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
    EconextNumberEntityDescription(
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
    EconextNumberEntityDescription(
        key="max_temp_radiator",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        native_min_value=0,
        native_max_value=75,
    ),
    # Max heating temperature
    EconextNumberEntityDescription(
        key="max_temp_heat",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        native_min_value=30,
        native_max_value=55,
    ),
    # Fixed temperature
    EconextNumberEntityDescription(
        key="fixed_temp",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        native_min_value=24,
        native_max_value=75,
    ),
    # Temperature reduction
    EconextNumberEntityDescription(
        key="temp_reduction",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-minus",
        native_min_value=0,
        native_max_value=20,
    ),
    # Heating curve - dynamically uses radiator, floor, or fan coil param based on circuit type
    EconextNumberEntityDescription(
        key="heating_curve",
        param_id="",  # Set dynamically per circuit type
        device_type=DeviceType.CIRCUIT,
        icon="mdi:chart-line",
        native_min_value=0.0,
        native_max_value=4.0,
        native_step=0.1,
    ),
    # Curve shift
    EconextNumberEntityDescription(
        key="curve_shift",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        icon="mdi:arrow-up-down",
        native_min_value=-20,
        native_max_value=20,
    ),
    # Curve multiplier
    EconextNumberEntityDescription(
        key="curve_multiplier",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        icon="mdi:arrow-left-right",
        native_min_value=-20,
        native_max_value=20,
    ),
    # Room temperature correction
    EconextNumberEntityDescription(
        key="room_temp_correction",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:tune",
        native_min_value=-10,
        native_max_value=10,
    ),
    # Cooling min setpoint temperature
    EconextNumberEntityDescription(
        key="min_setpoint_cooling",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:snowflake-thermometer",
        native_min_value=0,
        native_max_value=30,
    ),
    # Cooling max setpoint temperature
    EconextNumberEntityDescription(
        key="max_setpoint_cooling",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:snowflake-thermometer",
        native_min_value=0,
        native_max_value=30,
    ),
    # Cooling fixed temperature
    EconextNumberEntityDescription(
        key="cooling_fixed_temp",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:snowflake",
        native_min_value=0,
        native_max_value=30,
    ),
)


# Circuit select entities - editable mode selections
CIRCUIT_SELECTS: tuple[EconextSelectEntityDescription, ...] = (
    # Circuit type (radiator, UFH, or fan coil)
    EconextSelectEntityDescription(
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
CIRCUIT_SWITCHES: tuple[EconextSwitchEntityDescription, ...] = (
    # Heating enable (bit 20, inverted: 0=on, 1=off)
    EconextSwitchEntityDescription(
        key="heating_enable",
        param_id="",  # Set dynamically per circuit (CircuitXSettings)
        device_type=DeviceType.CIRCUIT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:radiator",
        bit_position=20,
        invert_logic=True,  # Bit 0 = heating ON
    ),
    # Cooling enable (bit 17)
    EconextSwitchEntityDescription(
        key="cooling_enable",
        param_id="",  # Set dynamically per circuit (CircuitXSettings)
        device_type=DeviceType.CIRCUIT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:snowflake",
        bit_position=17,
        invert_logic=False,  # Bit 1 = cooling ON
    ),
    # Pump only mode (bit 13)
    EconextSwitchEntityDescription(
        key="pump_only_mode",
        param_id="",  # Set dynamically per circuit (CircuitXSettings)
        device_type=DeviceType.CIRCUIT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:pump",
        bit_position=13,
        invert_logic=False,  # Bit 1 = pump only ON
    ),
    # Pump blockage (bit 10)
    EconextSwitchEntityDescription(
        key="pump_blockage",
        param_id="",  # Set dynamically per circuit (CircuitXSettings)
        device_type=DeviceType.CIRCUIT,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:pump-off",
        bit_position=10,
        invert_logic=False,  # Bit 1 = blockage ON
    ),
)


# Circuit schedule entities - bitfield for 30-minute time slots
# These are template descriptions - param_id is set dynamically per circuit
_CIRCUIT_SCHEDULE_DAYS = [
    ("sunday", "am", "pm"),
    ("monday", "am", "pm"),
    ("tuesday", "am", "pm"),
    ("wednesday", "am", "pm"),
    ("thursday", "am", "pm"),
    ("friday", "am", "pm"),
    ("saturday", "am", "pm"),
]

CIRCUIT_SCHEDULE_NUMBERS: tuple[EconextNumberEntityDescription, ...] = tuple(
    EconextNumberEntityDescription(
        key=f"schedule_{day}_{period}",
        param_id="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=4294967295,
        native_step=1,
    )
    for day, am_period, pm_period in _CIRCUIT_SCHEDULE_DAYS
    for period in [am_period, pm_period]
)


# Circuit schedule diagnostic sensors - decoded time ranges (one per day, combines AM/PM)
# These are template descriptions - param_id_am and param_id_pm are set dynamically per circuit
CIRCUIT_SCHEDULE_DIAGNOSTIC_SENSORS: tuple[EconextSensorEntityDescription, ...] = tuple(
    EconextSensorEntityDescription(
        key=f"schedule_{day}_decoded",
        param_id="",  # Set dynamically per circuit
        param_id_am="",  # Set dynamically per circuit
        param_id_pm="",  # Set dynamically per circuit
        device_type=DeviceType.CIRCUIT,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    for day, _, _ in _CIRCUIT_SCHEDULE_DAYS
)
