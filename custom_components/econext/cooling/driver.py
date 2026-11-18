"""Coordinator-side driver for the cooling controller.

Owns the persistent `CoolingState`, the `ScheduleDetector` and the live
tunables, and runs one `state_machine.tick()` per coordinator refresh
(10s). Reads every signal the state machine needs from the econext
register cache via `coordinator.get_param_value(id)` plus two external HA
sensors (dew point, optional OEM flow), and applies the resulting
`Decision` through `coordinator.async_set_param(id, value)`.

Pure logic lives in the sibling modules; this module is the only one that
touches Home Assistant / the coordinator.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.storage import Store
from homeassistant.util.dt import parse_datetime

from ..climate import CIRCUITS
from ..const import HP_STATUS_WORK_MODE_MAPPING, decode_current_season
from .const import (
    COOLING_ENABLE_BIT,
    COOLING_MAX_PUMP_SPEED,
    COOLING_MIN_PUMP_SPEED,
    DEFAULTS,
    MIN_TARGET_TEMP,
    PARAM_EPSILON,
    REG_COMP_HZ,
    REG_FLOW_HP,
    REG_HEAT_SOURCE_COOLING_HYST,
    REG_MAX_PUMP_SPEED,
    REG_MIN_BREAK_TIME,
    REG_MIN_PUMP_SPEED,
    PREEMPT_MODES,
    REG_RETURN,
    REG_SEASON,
    REG_WORK_MODE,
    SAFE_MODES,
    STATE_IDLE,
    STATE_STARTING,
    TICK_SECONDS,
)
from .models import Config, CoolingState, Decision, Sensors
from .schedule import ScheduleDetector
from .state_machine import tick

_LOGGER = logging.getLogger(__name__)


class CoolingDriver:
    """Runs the cooling state machine on the econext coordinator's tick."""

    def __init__(
        self,
        coordinator,
        *,
        circuit: int,
        dew_point_entity: str | None,
        oem_flow_entity: str | None,
        store: Store | None = None,
    ) -> None:
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self.circuit = circuit
        self._circuit_cfg = CIRCUITS.get(circuit)
        self.dew_point_entity = dew_point_entity
        self.oem_flow_entity = oem_flow_entity
        self._store = store

        self.schedule_detector = ScheduleDetector()
        self.state = CoolingState()
        # Live tunables — the cooling device's number/switch entities push
        # their values in via update_tunable().
        self.tunables: dict[str, Any] = dict(DEFAULTS)

        self.last_decision: Decision | None = None
        self.last_sensors: Sensors | None = None
        self._setup_done = False
        # Last-known value per register, so a transient gateway poll gap holds
        # the previous reading instead of snapping to a fixed default. The
        # standalone reads sticky HA sensors; a fixed room-setpoint fallback
        # (e.g. 22.0) would otherwise fabricate cooling demand on any 92 gap.
        self._last_known: dict[str, float] = {}

    # ---------- public API ----------

    @property
    def available(self) -> bool:
        """True when the selected circuit exposes the cooling target register."""
        return bool(self._circuit_cfg and self._circuit_cfg.cooling_fixed_temp_param)

    @property
    def target_param_id(self) -> str | None:
        return self._circuit_cfg.cooling_fixed_temp_param if self._circuit_cfg else None

    def update_tunable(self, key: str, value: Any) -> None:
        """Set one tunable from its entity."""
        self.tunables[key] = value

    async def async_load(self) -> None:
        """Restore persisted CoolingState so break timers / cycle phase survive
        restarts (matches the standalone, and avoids a spurious start on reload
        because last_cycle_end is no longer unknown)."""
        if self._store is None:
            return
        data = await self._store.async_load()
        if not data:
            return
        s = self.state
        s.cycle_state = data.get("cycle_state", s.cycle_state)
        s.last_running_minutes = float(data.get("last_running_minutes", 0.0))
        s.running_comp_on_seconds = float(data.get("running_comp_on_seconds", 0.0))
        s.below_dew_streak_s = float(data.get("below_dew_streak_s", 0.0))
        s.hard_floor_streak_s = float(data.get("hard_floor_streak_s", 0.0))
        s.last_target_written = data.get("last_target_written")
        s.state_entered = parse_datetime(data["state_entered"]) if data.get("state_entered") else None
        s.last_cycle_end = parse_datetime(data["last_cycle_end"]) if data.get("last_cycle_end") else None
        s.last_preempt_active_at = (
            parse_datetime(data["last_preempt_active_at"]) if data.get("last_preempt_active_at") else None
        )
        _LOGGER.info("Cooling: restored state %s (last_run=%.1f)", s.cycle_state, s.last_running_minutes)

    def _state_to_dict(self) -> dict[str, Any]:
        s = self.state
        return {
            "cycle_state": s.cycle_state,
            "last_running_minutes": s.last_running_minutes,
            "running_comp_on_seconds": s.running_comp_on_seconds,
            "below_dew_streak_s": s.below_dew_streak_s,
            "hard_floor_streak_s": s.hard_floor_streak_s,
            "last_target_written": s.last_target_written,
            "state_entered": s.state_entered.isoformat() if s.state_entered else None,
            "last_cycle_end": s.last_cycle_end.isoformat() if s.last_cycle_end else None,
            "last_preempt_active_at": s.last_preempt_active_at.isoformat() if s.last_preempt_active_at else None,
        }

    def _persist(self) -> None:
        """Schedule a throttled save of CoolingState (coalesces rapid ticks)."""
        if self._store is not None:
            self._store.async_delay_save(self._state_to_dict, 10)

    def _observe_for_tracking(self, now: datetime) -> str | None:
        """Track work_mode-derived state every tick — even when the dew gate
        below skips the state machine — so hp_quiet (`last_preempt_active_at`)
        and the schedule flap detector stay accurate across dew-sensor gaps.
        The standalone always ticks (it uses an 18.0 dew fallback); skipping
        this during dew gaps would let hp_quiet go stale and cause premature
        starts once dew returns.
        """
        raw_mode = self.coordinator.get_param_value(REG_WORK_MODE)
        work_mode = HP_STATUS_WORK_MODE_MAPPING.get(int(raw_mode)) if raw_mode is not None else None
        self.schedule_detector.observe(work_mode, now)
        if work_mode in PREEMPT_MODES:
            self.state.last_preempt_active_at = now
        return work_mode

    async def async_tick(self, now: datetime) -> None:
        """Run one state-machine tick. Never raises into the poll loop."""
        if not self.available:
            _LOGGER.debug("Cooling async_tick: not available (circuit %s)", self.circuit)
            return

        # Always track HP activity (hp_quiet + schedule) regardless of dew.
        self._observe_for_tracking(now)

        config = self._build_config()
        dew = self._read_entity_float(self.dew_point_entity)
        _LOGGER.debug(
            "Cooling async_tick: state=%s dew_entity=%s dew=%s setup_done=%s",
            self.state.cycle_state,
            self.dew_point_entity,
            dew,
            self._setup_done,
        )

        # Idempotent boot-time HP setup (season + work_mode gated inside).
        if not self._setup_done:
            await self._assert_setup_params(config.dry_run)
            self._setup_done = True

        # Dew-safety gate: without a dew-point reading there is no dew
        # protection, so we must not cool. Wind down any active cycle.
        if dew is None:
            if self.state.cycle_state != STATE_IDLE:
                _LOGGER.warning(
                    "Cooling: dew-point sensor %s unavailable mid-cycle; forcing cooldown",
                    self.dew_point_entity,
                )
                await self._write_target(config.cooldown_target, config.dry_run)
                self._reset_to_idle(now)
            else:
                _LOGGER.info(
                    "Cooling tick: idle, skipped — no dew reading from %s",
                    self.dew_point_entity,
                )
            return

        sensors = self._build_sensors(now, dew, config)
        self.last_sensors = sensors

        decision = tick(self.state, sensors, config, now, TICK_SECONDS)
        self.last_decision = decision

        # Per-tick decision line so a dry-run shadow can be diffed tick-for-tick
        # against the live standalone controller.
        _LOGGER.info(
            "Cooling tick: dry_run=%s state=%s work_mode=%s comp=%.0f thermostat=%.1f "
            "room=%.1f dew=%.1f safe=%s flow_below_dew=%.2f -> new_state=%s target_write=%s",
            config.dry_run,
            self.state.cycle_state,
            sensors.work_mode,
            sensors.comp_hz,
            sensors.thermostat_temp,
            config.room_target,
            sensors.dew_max,
            sensors.safe_target,
            sensors.flow_below_dew,
            decision.new_state,
            decision.target_write,
        )

        await self._apply_decision(decision, config, now)

    def status(self) -> dict[str, Any]:
        """Diagnostic snapshot for the cooling-controller entities."""
        s = self.last_sensors
        return {
            "available": self.available,
            "circuit": self.circuit,
            "cycle_state": self.state.cycle_state,
            "last_running_minutes": self.state.last_running_minutes,
            "last_cycle_end": self.state.last_cycle_end,
            "safe_target": s.safe_target if s else None,
            "flow_below_dew": s.flow_below_dew if s else None,
            "schedule_active": s.schedule_active if s else None,
            "schedule_stats": self.schedule_detector.stats(),
        }

    # ---------- reading ----------

    def _build_sensors(self, now: datetime, dew: float, config: Config) -> Sensors:
        c = self._circuit_cfg
        coord = self.coordinator

        raw_mode = coord.get_param_value(REG_WORK_MODE)
        work_mode = (
            HP_STATUS_WORK_MODE_MAPPING.get(int(raw_mode))
            if raw_mode is not None
            else None
        )
        # schedule_detector.observe() and last_preempt tracking happen once per
        # tick in _observe_for_tracking(), before the dew gate.

        flow_hp = self._param_float(REG_FLOW_HP, 0.0)
        flow_oem = self._read_entity_float(self.oem_flow_entity)
        if flow_oem is None:
            flow_oem = flow_hp

        # Cooling demand thermostat; fall back to room setpoint so demand
        # reads neutral (no spurious start/stop) when the sensor is missing.
        room_target = self._param_float(c.room_temp_setpoint_param, float(self.tunables["room_target"]))
        thermostat_temp = self._param_float(c.thermostat_param, room_target)

        season = decode_current_season(coord.get_param_value(REG_SEASON) or 0)
        cooling_bit_on = self._circuit_cooling_enabled()

        safe_target = self._compute_safe_target(dew, config)

        return Sensors(
            work_mode=work_mode,
            comp_hz=self._param_float(REG_COMP_HZ, 0.0),
            flow_hp=flow_hp,
            flow_oem=flow_oem,
            return_temp=self._param_float(REG_RETURN, 0.0),
            current_target=self._param_float(c.cooling_fixed_temp_param, 20.0),
            dew_max=dew,
            thermostat_temp=thermostat_temp,
            enable_switch_on=bool(self.tunables["enable"]) and cooling_bit_on,
            season_is_summer=(season == "summer"),
            schedule_active=self.schedule_detector.is_schedule_active(now),
            safe_target=safe_target,
            flow_below_dew=round(flow_oem - dew, 2),
        )

    def _build_config(self) -> Config:
        t = self.tunables
        # room_target tracks the live circuit setpoint; falls back to tunable.
        room_target = self._param_float(
            self._circuit_cfg.room_temp_setpoint_param, float(t["room_target"])
        )
        return Config(
            safety_margin=float(t["safety_margin"]),
            delta_t_est=float(t["delta_t_est"]),
            max_run_minutes=float(t["max_run_minutes"]),
            min_break_minutes=float(t["min_break_minutes"]),
            aborted_break_minutes=float(t["aborted_break_minutes"]),
            real_cycle_threshold_minutes=float(t["real_cycle_threshold_minutes"]),
            flow_below_dew_cutoff=float(t["flow_below_dew_cutoff"]),
            flow_below_dew_min_duration_s=float(t["flow_below_dew_min_duration_s"]),
            room_target=room_target,
            working_target_offset=float(t["working_target_offset"]),
            stale_loop_flow=float(t["stale_loop_flow"]),
            hp_quiet_minutes=float(t["hp_quiet_minutes"]),
            hard_floor=float(t["hard_floor"]),
            hard_floor_duration_s=float(t["hard_floor_duration_s"]),
            panic_floor=float(t["panic_floor"]),
            start_timeout_minutes=float(t["start_timeout_minutes"]),
            dip_target=float(t["dip_target"]),
            cooldown_target=float(t["cooldown_target"]),
            dry_run=bool(t["dry_run"]),
            enable=bool(t["enable"]),
        )

    def _compute_safe_target(self, dew: float, config: Config) -> int:
        """ceil(dp + 1 + delta_t_est + safety_margin), clamped to [16, 27]."""
        if dew <= 0:
            return 22
        raw = dew + 1 + config.delta_t_est + config.safety_margin
        return max(16, min(27, math.ceil(raw)))

    def _circuit_cooling_enabled(self) -> bool:
        """Bit 17 of the circuit's settings register = cooling enabled."""
        raw = self.coordinator.get_param_value(self._circuit_cfg.settings_param)
        if raw is None:
            return False
        return ((int(raw) >> COOLING_ENABLE_BIT) & 1) == 1

    def _param_float(self, param_id: str | int | None, default: float) -> float:
        """Read a register as float, holding the last-known value across a
        transient poll gap. Only falls to `default` if the register has never
        been seen (matches the standalone's sticky-HA-sensor behaviour and
        avoids fabricating demand when e.g. the room setpoint momentarily
        drops out of the gateway response)."""
        if param_id is None:
            return default
        key = str(param_id)
        value = self.coordinator.get_param_value(param_id)
        if value is None:
            return self._last_known.get(key, default)
        try:
            f = float(value)
        except (TypeError, ValueError):
            return self._last_known.get(key, default)
        self._last_known[key] = f
        return f

    def _read_entity_float(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, "none", ""):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    # ---------- writing ----------

    async def _apply_decision(self, decision: Decision, config: Config, now: datetime) -> None:
        if decision.log_message:
            log = _LOGGER.warning if decision.log_level == "WARNING" else _LOGGER.info
            log("Cooling: %s", decision.log_message)

        if decision.target_write is not None:
            await self._write_target(float(decision.target_write), config.dry_run)

        if decision.new_state is not None and decision.new_state != self.state.cycle_state:
            _LOGGER.info("Cooling: state %s -> %s", self.state.cycle_state, decision.new_state)
            if decision.new_state == STATE_STARTING:
                await self._assert_pump_speeds(config.dry_run)
            self.state.cycle_state = decision.new_state
            self.state.state_entered = now

        if decision.finalize:
            self.state.last_running_minutes = round(self.state.running_comp_on_seconds / 60.0, 1)
            self.state.running_comp_on_seconds = 0.0
            self.state.below_dew_streak_s = 0.0
            self.state.hard_floor_streak_s = 0.0
            self.state.last_cycle_end = now

        self._persist()

    def _reset_to_idle(self, now: datetime) -> None:
        self.state.cycle_state = STATE_IDLE
        self.state.state_entered = now
        self.state.running_comp_on_seconds = 0.0
        self.state.below_dew_streak_s = 0.0
        self.state.hard_floor_streak_s = 0.0
        self.state.last_cycle_end = now
        self._persist()

    async def _write_target(self, value: float, dry_run: bool) -> None:
        """Write the circuit cooling target, debounced on last_target_written.

        Hard-floored at MIN_TARGET_TEMP so a dip-to-start never commands the HP
        below the configured minimum (dew-margin protection on high-dew days).
        """
        value = max(float(value), float(MIN_TARGET_TEMP))
        if (
            self.state.last_target_written is not None
            and abs(self.state.last_target_written - value) < 0.5
        ):
            return
        self.state.last_target_written = value

        if dry_run:
            _LOGGER.info("Cooling [dry-run]: would set target %s = %s", self.target_param_id, value)
            return
        await self.coordinator.async_set_param(self.target_param_id, value)
        _LOGGER.info("Cooling: set target %s = %s", self.target_param_id, value)

    async def _assert_setup_params(self, dry_run: bool) -> None:
        """Idempotently assert the one-time HP setup params."""
        await self._assert_param(REG_HEAT_SOURCE_COOLING_HYST, 0, dry_run)
        await self._assert_param(REG_MIN_BREAK_TIME, 5, dry_run)

    async def _assert_pump_speeds(self, dry_run: bool) -> None:
        """Assert cooling pump speeds (max before min), season + work_mode gated."""
        season = decode_current_season(self.coordinator.get_param_value(REG_SEASON) or 0)
        if season != "summer":
            return
        raw_mode = self.coordinator.get_param_value(REG_WORK_MODE)
        work_mode = HP_STATUS_WORK_MODE_MAPPING.get(int(raw_mode)) if raw_mode is not None else None
        if work_mode not in SAFE_MODES:
            return
        # Max must be set before min — min cannot exceed the current max.
        await self._assert_param(REG_MAX_PUMP_SPEED, COOLING_MAX_PUMP_SPEED, dry_run)
        await self._assert_param(REG_MIN_PUMP_SPEED, COOLING_MIN_PUMP_SPEED, dry_run)

    async def _assert_param(self, param_id: int, target: float, dry_run: bool) -> None:
        """Write `target` to `param_id` only if it has drifted from spec."""
        current = self.coordinator.get_param_value(param_id)
        if current is not None:
            try:
                if abs(float(current) - target) < PARAM_EPSILON:
                    return
            except (TypeError, ValueError):
                pass
        if dry_run:
            _LOGGER.info("Cooling [dry-run]: would assert %s = %s", param_id, target)
            return
        try:
            await self.coordinator.async_set_param(param_id, target)
            _LOGGER.info("Cooling: asserted setup param %s = %s", param_id, target)
        except Exception as exc:  # noqa: BLE001 - setup writes are best-effort
            _LOGGER.warning("Cooling: failed to assert %s = %s: %s", param_id, target, exc)
