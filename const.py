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
PLATFORMS: list[str] = ["sensor"]

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
    EconetSensorEntityDescription(
        key="work_state_1",
        param_id="161",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
    ),
    EconetSensorEntityDescription(
        key="work_state_2",
        param_id="162",
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
