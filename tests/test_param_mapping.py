"""Check that every parameter index the integration uses points at the right controller parameter.

The names come from the controller's own parameter table (tests/fixtures/parameters.json,
a full dump from an ecoMAX360i). Circuits 6 and 7 use a different block layout from 1-5,
so offsets copied from one circuit to another land on the wrong parameter.
"""

import dataclasses
import json
import re
from pathlib import Path

import pytest

from custom_components.econext import const
from custom_components.econext.climate import CIRCUITS

FIXTURE = Path(__file__).parent / "fixtures" / "parameters.json"

# Circuit field -> controller name pattern, {n} is the circuit number.
CIRCUIT_FIELD_NAMES = {
    "active_param": r"Circuit{n}active",
    "name_param": r"Circuit{n}name",
    "work_state_param": r"Circuit{n}WorkState",
    "settings_param": r"Circuit{n}Settings",
    "thermostat_param": r"Circuit{n}thermostat(Temp)?",
    "comfort_param": r"Circuit{n}ComfortTemp",
    "eco_param": r"Circuit{n}EcoTemp",
    "calc_temp_param": r"Circuit{n}CalcTemp",
    "flow_temp_param": r"TempCircuit{n}",
    "room_temp_setpoint_param": r"Circuit{n}_romTempSet",
    "hysteresis_param": r"Circuit{n}DownHist",
    "max_temp_radiator_param": r"Circuit{n}MaxSetTemp(Rad)?",
    "max_temp_heat_param": r"Circuit{n}MaxTempHeat",
    "max_temp_heat_hysteresis_param": r"Circuit{n}MaxTempHeatHist",
    "fixed_temp_param": r"Circuit{n}BaseTemp",
    "temp_reduction_param": r"Circuit{n}TempReduction",
    "curve_multiplier_param": r"Circuit{n}Multiplier",
    "curve_radiator_param": r"Circuit{n}CurveRadiator",
    "curve_floor_param": r"Circuit{n}CurveFloor",
    "curve_fancoil_param": r"MixCirc{n}HeatCurveFanCoil",
    "curve_shift_param": r"Circuit{n}Curveshift",
    "room_temp_correction_param": r"Circuit{n}userCor",
    "type_settings_param": r"Circuit{n}TypeSettings",
    "min_setpoint_cooling_param": r"Circuit{n}MinSetPointCooling",
    "max_setpoint_cooling_param": r"Circuit{n}MaxSetPointCooling",
    "cooling_fixed_temp_param": r"Circuit{n}MixerCoolBaseTemp",
    "min_setpoint_cooling_limit_param": r"Circuit{n}inSetTempCoolingDownRange",
    "boost_time_left_param": r"Circuit_{n}_boost_time_left",
}
SCHEDULE_FIELD = re.compile(r"schedule_(\w+day)_(am|pm)")


@pytest.fixture(scope="module")
def names() -> dict[str, str]:
    with open(FIXTURE) as f:
        return {index: p["name"] for index, p in json.load(f).items()}


@pytest.mark.parametrize("number", sorted(CIRCUITS))
def test_circuit_params_point_at_their_circuit(number, names):
    circuit = CIRCUITS[number]
    wrong = []
    for field in dataclasses.fields(circuit):
        index = getattr(circuit, field.name)
        if index is None:  # parameter does not exist for this circuit
            continue
        name = names.get(index)
        if schedule := SCHEDULE_FIELD.fullmatch(field.name):
            day, half = schedule.groups()
            pattern = rf"Circuit{number}{day.capitalize()}{half.upper()}_?"
        else:
            assert field.name in CIRCUIT_FIELD_NAMES, f"no expected name for {field.name}"
            pattern = CIRCUIT_FIELD_NAMES[field.name].format(n=number)
        if name is None or not re.fullmatch(pattern, name):
            wrong.append(f"{field.name}={index} is {name!r}, expected {pattern}")
    assert not wrong, f"Circuit {number}:\n" + "\n".join(wrong)


def _descriptions():
    for attr, value in vars(const).items():
        if attr.isupper() and isinstance(value, tuple):
            for desc in value:
                param_id = getattr(desc, "param_id", None)
                if param_id:
                    yield attr, desc


@pytest.mark.parametrize(
    ("group", "desc"),
    list(_descriptions()),
    ids=lambda v: v if isinstance(v, str) else v.key,
)
def test_entity_param_exists(group, desc, names):
    assert desc.param_id in names, f"{group}.{desc.key} uses {desc.param_id}, not in the controller table"


def test_circuit_temperature_correction_is_the_heating_flow_offset(names):
    desc = next(d for d in const.CONTROLLER_NUMBERS if d.key == "circuit_temperature_correction")
    assert names[desc.param_id] == "hSMPTSIncreaseCirc"
    dhw = next(d for d in const.DHW_NUMBERS if d.key == "temperature_correction")
    assert names[dhw.param_id] == "HeatSourceTempInc"
