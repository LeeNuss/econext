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
PLATFORMS: list[str] = ["number", "select", "sensor", "switch"]

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


class DeviceType(StrEnum):
    """Device types in the integration."""

    CONTROLLER = "controller"
    DHW = "dhw"
    BUFFER = "buffer"
    HEATPUMP = "heatpump"
    CIRCUIT = "circuit"


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


# DHW switch entities
DHW_SWITCHES: tuple[EconetSwitchEntityDescription, ...] = (
    # Legionella protection
    EconetSwitchEntityDescription(
        key="legionella_start",
        param_id="135",
        device_type=DeviceType.DHW,
        icon="mdi:bacteria",
    ),
)
