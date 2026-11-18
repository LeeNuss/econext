"""Constants for the cooling controller feature."""

from __future__ import annotations

TICK_SECONDS = 10

# Cycle state values (persisted on the cycle_state sensor).
STATE_IDLE = "idle"
STATE_STARTING = "starting"
STATE_RUNNING = "running"
STATE_COOLDOWN = "cooldown"
CYCLE_STATES = [STATE_IDLE, STATE_STARTING, STATE_RUNNING, STATE_COOLDOWN]

# HP work-mode enum values (decoded from register 1350 via
# econext.const.HP_STATUS_WORK_MODE_MAPPING) that mean "doing real work
# that should preempt cooling" — heating, DHW (mode 2), defrost. The
# bug fix is that `cooling`/`standby` flapping does NOT count as preempt
# activity, so the HP-quiet timer doesn't reset on idle noise.
PREEMPT_MODES = ("heating", "hp_status_mode_2", "defrost", "unknown")

# Safe modes for the controller to act in.
SAFE_MODES = ("standby", "cooling")

# Global / heat-pump register ids read each tick.
REG_COMP_HZ = 1365
REG_FLOW_HP = 1134
REG_RETURN = 1135
REG_WORK_MODE = 1350
REG_SEASON = 162
REG_MIN_PUMP_SPEED = 1440
REG_MAX_PUMP_SPEED = 1441

# One-time HP setup params asserted idempotently on boot and at each
# cooling-cycle start. (register id, target value).
REG_HEAT_SOURCE_COOLING_HYST = 473  # must be 0 for the dip-and-recover trick
REG_MIN_BREAK_TIME = 499  # minutes

SETUP_PARAMS: list[tuple[int, float]] = [
    (REG_HEAT_SOURCE_COOLING_HYST, 0),
    (REG_MIN_BREAK_TIME, 5),
]

# Pump speeds during cooling (written via registers 1441 then 1440 — max
# before min, since min cannot exceed the current max). Season + work_mode
# gated so the DHW/season automations keep owning the heating value.
COOLING_MAX_PUMP_SPEED = 100
COOLING_MIN_PUMP_SPEED = 85

# Hard floor on the cooling-water target written to the HP. The dip-to-start
# would otherwise command 15; on a high-dew day that drives flow too far below
# dew point. Never command the circuit cooling target below this.
MIN_TARGET_TEMP = 16

# Float epsilon for setup-param idempotency comparison.
PARAM_EPSILON = 0.05

# Bit of a circuit's settings register that enables cooling.
COOLING_ENABLE_BIT = 17

# Production defaults for the tunable number/switch entities.
DEFAULTS: dict[str, float | bool] = {
    "safety_margin": 0.5,
    "delta_t_est": 1.5,
    "max_run_minutes": 240.0,
    "min_break_minutes": 40.0,
    "aborted_break_minutes": 5.0,
    "real_cycle_threshold_minutes": 10.0,
    "flow_below_dew_cutoff": 2.5,
    "flow_below_dew_min_duration_s": 180.0,
    "room_target": 22.0,
    "working_target_offset": 3.0,
    "stale_loop_flow": 30.0,
    "hp_quiet_minutes": 5.0,
    "hard_floor": 3.5,
    "hard_floor_duration_s": 600.0,
    "panic_floor": 4.0,
    "start_timeout_minutes": 4.0,
    "dip_target": 15.0,
    "cooldown_target": 25.0,
    # Default ON so a freshly-enabled controller observes only (no writes)
    # until an operator explicitly flips dry_run off at cutover. This makes
    # it safe to run as a shadow alongside another active controller.
    "dry_run": True,
    "enable": True,
}
