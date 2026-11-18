"""Tests for the coordinator-side CoolingDriver against a fake coordinator.

Validates register reads/writes, the dry-run gate and the dew-safety gate
without a running Home Assistant.
"""

import pytest

from custom_components.econext.cooling.driver import CoolingDriver
from custom_components.econext.cooling.const import STATE_IDLE, STATE_RUNNING, STATE_STARTING
from custom_components.econext.climate import CIRCUITS
from homeassistant.util import dt as dt_util

C2 = CIRCUITS[2]


class _FakeState:
    def __init__(self, state: str) -> None:
        self.state = state


class _FakeStates:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._m = {k: _FakeState(v) for k, v in mapping.items()}

    def get(self, entity_id: str):
        return self._m.get(entity_id)


class _FakeHass:
    def __init__(self, states: dict[str, str]) -> None:
        self.states = _FakeStates(states)


class _FakeCoordinator:
    """Minimal stand-in exposing what CoolingDriver uses."""

    def __init__(self, params: dict, states: dict[str, str]) -> None:
        self.hass = _FakeHass(states)
        self._params = {str(k): v for k, v in params.items()}
        self.cooling_driver = None
        self.writes: list[tuple[str, float]] = []

    def get_param_value(self, pid):
        return self._params.get(str(pid))

    async def async_set_param(self, pid, value):
        self._params[str(pid)] = value
        self.writes.append((str(pid), value))
        return True


def _demand_params() -> dict:
    """A controller state that satisfies all idle->starting gates for circuit 2."""
    return {
        1350: 0,  # work_mode standby (SAFE)
        1365: 0,  # comp_hz
        1134: 25,  # flow_hp
        1135: 24,  # return
        162: 1,  # season summer (bit0)
        C2.settings_param: 1 << 17,  # cooling-enable bit set
        C2.thermostat_param: 24,  # demand: > setpoint + 0.5
        C2.room_temp_setpoint_param: 22,
        C2.cooling_fixed_temp_param: 20,  # current target
        473: 0,  # setup params already at spec
        499: 5,
        C2.min_setpoint_cooling_limit_param: 1,
        1440: 85,  # pump speeds already at cooling values
        1441: 100,
    }


def _driver(params: dict, dew: str | None = "14", dry_run: bool = False) -> tuple[CoolingDriver, _FakeCoordinator]:
    states = {"sensor.dew": dew} if dew is not None else {}
    coord = _FakeCoordinator(params, states)
    driver = CoolingDriver(coord, circuit=2, dew_point_entity="sensor.dew", oem_flow_entity=None)
    coord.cooling_driver = driver
    driver.tunables["dry_run"] = dry_run
    return driver, coord


async def test_dry_run_makes_no_writes_but_advances_state():
    driver, coord = _driver(_demand_params(), dry_run=True)
    await driver.async_tick(dt_util.now())

    assert coord.writes == []  # nothing written in dry-run
    assert driver.state.cycle_state == STATE_STARTING  # logic still ran
    assert driver.last_decision.target_write == driver.tunables["dip_target"]


async def test_live_start_writes_dip_target_floored_at_16():
    driver, coord = _driver(_demand_params(), dry_run=False)
    await driver.async_tick(dt_util.now())

    assert driver.state.cycle_state == STATE_STARTING
    # dip_target is 15 but the hard floor (MIN_TARGET_TEMP=16) caps the write;
    # never command the HP below 16.
    assert (str(C2.cooling_fixed_temp_param), 16.0) in coord.writes
    assert not any(w[0] == str(C2.cooling_fixed_temp_param) and w[1] < 16.0 for w in coord.writes)


async def test_setup_params_asserted_when_drifted():
    params = _demand_params()
    params[473] = 5  # drifted from required 0
    driver, coord = _driver(params, dry_run=False)
    await driver.async_tick(dt_util.now())

    assert ("473", 0) in coord.writes


async def test_min_setpoint_cooling_limit_asserted_on_the_cooling_circuit():
    params = _demand_params()
    params[C2.min_setpoint_cooling_limit_param] = 7  # factory value
    driver, coord = _driver(params, dry_run=False)
    await driver.async_tick(dt_util.now())

    assert (C2.min_setpoint_cooling_limit_param, 1) in coord.writes


async def test_preempt_tracked_even_when_dew_missing():
    # Even with no dew reading (state machine skipped), hp_quiet tracking must
    # still advance so it doesn't go stale across a dew gap.
    params = _demand_params()
    params[1350] = 1  # work_mode heating (a PREEMPT mode)
    driver, coord = _driver(params, dew="unavailable", dry_run=True)
    assert driver.state.last_preempt_active_at is None
    await driver.async_tick(dt_util.now())

    assert driver.state.last_preempt_active_at is not None  # tracked despite dew gap
    assert coord.writes == []  # still no writes (idle + dry-run)
    assert driver.state.cycle_state == STATE_IDLE


async def test_no_dew_keeps_idle_and_silent():
    driver, coord = _driver(_demand_params(), dew="unavailable", dry_run=False)
    await driver.async_tick(dt_util.now())

    assert coord.writes == []
    assert driver.state.cycle_state == STATE_IDLE


async def test_dew_lost_mid_cycle_forces_cooldown():
    driver, coord = _driver(_demand_params(), dew="unavailable", dry_run=False)
    driver.state.cycle_state = STATE_RUNNING
    await driver.async_tick(dt_util.now())

    assert (str(C2.cooling_fixed_temp_param), driver.tunables["cooldown_target"]) in coord.writes
    assert driver.state.cycle_state == STATE_IDLE


async def test_dry_run_suppresses_cooldown_write_on_dew_loss():
    # Condition 1: even the dew-loss forced cooldown must not write in dry-run.
    driver, coord = _driver(_demand_params(), dew="unavailable", dry_run=True)
    driver.state.cycle_state = STATE_RUNNING
    await driver.async_tick(dt_util.now())

    assert coord.writes == []


async def test_dry_run_suppresses_pump_speed_writes_on_start():
    # Condition 1: pump speeds (1440/1441) must not be written in dry-run even
    # when they have drifted and a cycle starts.
    params = _demand_params()
    params[1440] = 45  # drifted (heating value)
    params[1441] = 70
    driver, coord = _driver(params, dry_run=True)
    await driver.async_tick(dt_util.now())

    assert driver.state.cycle_state == STATE_STARTING
    assert coord.writes == []


class _FakeStore:
    """Minimal Store stand-in capturing the delay-saved snapshot."""

    def __init__(self, initial: dict | None = None) -> None:
        self._data = initial
        self.saved: dict | None = None

    async def async_load(self):
        return self._data

    def async_delay_save(self, data_func, delay):
        self.saved = data_func()


async def test_state_persisted_on_finalize():
    from custom_components.econext.cooling.const import STATE_COOLDOWN

    params = _demand_params()
    params[1365] = 0  # comp off -> cooldown finalizes to idle
    driver, coord = _driver(params, dry_run=True)
    driver._store = _FakeStore()
    driver.state.cycle_state = STATE_COOLDOWN
    driver.state.running_comp_on_seconds = 600.0
    await driver.async_tick(dt_util.now())

    assert driver._store.saved is not None
    assert driver._store.saved["cycle_state"] == STATE_IDLE
    assert driver._store.saved["last_running_minutes"] == 10.0  # 600s / 60


async def test_state_restored_on_load():
    driver, coord = _driver(_demand_params(), dry_run=True)
    driver._store = _FakeStore(
        {
            "cycle_state": "running",
            "last_running_minutes": 18.0,
            "last_cycle_end": "2026-05-28T19:00:00+00:00",
        }
    )
    await driver.async_load()

    assert driver.state.cycle_state == "running"
    assert driver.state.last_running_minutes == 18.0
    assert driver.state.last_cycle_end is not None


async def test_room_setpoint_is_sticky_across_param_gap():
    # A momentary gateway gap on register 92 must NOT drop room_target to the
    # fixed 22.0 default and fabricate demand; it should hold the last value.
    params = _demand_params()
    params[C2.room_temp_setpoint_param] = 24  # distinct from the 22.0 static default
    driver, coord = _driver(params, dry_run=True)
    # First tick caches 92 = 24.0.
    await driver.async_tick(dt_util.now())
    assert driver._last_known[str(C2.room_temp_setpoint_param)] == 24.0
    # Now 92 drops out of the gateway response.
    coord._params.pop(str(C2.room_temp_setpoint_param))
    cfg = driver._build_config()
    assert cfg.room_target == 24.0  # held last value, not the 22.0 default


async def test_oem_flow_falls_back_to_hp_flow():
    driver, coord = _driver(_demand_params(), dry_run=True)
    await driver.async_tick(dt_util.now())
    # flow_oem absent -> uses flow_hp (25); dew 14 -> flow_below_dew = 11
    assert driver.last_sensors.flow_oem == 25
    assert driver.last_sensors.flow_below_dew == pytest.approx(11.0)
