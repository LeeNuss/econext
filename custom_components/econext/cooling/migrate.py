"""One-shot migrations executed when the cooling feature is enabled.

These keep the controlled circuit in a state the cooling state machine
expects (circuit type = fan_coil), and preserve the user's existing heating
curve value across the type flip so the heating-curve number entity reads
the same after as before.
"""

from __future__ import annotations

import logging

from homeassistant.helpers import entity_registry as er

from ..climate import CIRCUITS
from ..const import CIRCUIT_TYPE_MAPPING, CIRCUIT_TYPE_REVERSE, DOMAIN

_LOGGER = logging.getLogger(__name__)

FAN_COIL = CIRCUIT_TYPE_REVERSE["fan_coil"]  # 3


def _curve_param_for_type(cfg, type_value: int) -> str | None:
    """The currently-active curve register for a circuit at a given type."""
    if type_value == 1:  # radiator
        return cfg.curve_radiator_param
    if type_value == 2:  # ufh
        return cfg.curve_floor_param
    if type_value == 3:  # fan_coil
        return cfg.curve_fancoil_param
    return None


async def async_ensure_fan_coil(coordinator, circuit: int) -> None:
    """Switch the chosen cooling circuit to fan_coil and carry the curve value.

    Idempotent: a no-op when the circuit is already fan_coil. Read the current
    type, capture the active curve value, write it to the fan-coil curve
    register, then flip the type to 3. Failures here must not break setup —
    callers should swallow exceptions.
    """
    cfg = CIRCUITS.get(circuit)
    if cfg is None:
        return

    raw = coordinator.get_param_value(cfg.type_settings_param)
    if raw is None:
        _LOGGER.debug("Cooling: circuit %s type unknown; skipping fan_coil migration", circuit)
        return
    current_type = int(raw)
    if current_type == FAN_COIL:
        return  # already where we want it

    src_param = _curve_param_for_type(cfg, current_type)
    if src_param is not None:
        curve_value = coordinator.get_param_value(src_param)
        if curve_value is not None:
            try:
                await coordinator.async_set_param(cfg.curve_fancoil_param, curve_value)
                _LOGGER.info(
                    "Cooling: copied circuit %s heating curve %s -> fan_coil curve %s (%s)",
                    circuit,
                    src_param,
                    cfg.curve_fancoil_param,
                    curve_value,
                )
            except Exception as exc:  # noqa: BLE001 - cooling setup must not break setup
                _LOGGER.warning(
                    "Cooling: failed to copy heating curve for circuit %s: %s", circuit, exc
                )

    try:
        await coordinator.async_set_param(cfg.type_settings_param, FAN_COIL)
        _LOGGER.info(
            "Cooling: set circuit %s type %s -> fan_coil",
            circuit,
            CIRCUIT_TYPE_MAPPING.get(current_type, current_type),
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Cooling: failed to set circuit %s type to fan_coil: %s", circuit, exc)


def async_migrate_heating_curve_unique_ids(hass, entry) -> None:
    """Rename old param-id-based heating_curve unique_ids to a stable form.

    For installs that ran before the `unique_id_key` stabilisation, the
    heating_curve entity's unique_id embedded the currently-active curve
    register (e.g. `_circuit_2_274` for UFH). When the type flipped, the old
    entry was orphaned. Rename any such existing entries to the new stable
    `_circuit_N_heating_curve` form so the user sees the same entity_id and
    no second "(unavailable)" entity appears.

    Safe to call every setup: once renamed, the old pattern doesn't match
    any registry entries.
    """
    uid = entry.runtime_data.get_device_uid()
    if not uid or uid == "unknown":
        return

    # Build the set of "old" heating_curve unique_ids per circuit.
    old_to_new: dict[str, tuple[str, int]] = {}
    for n, cfg in CIRCUITS.items():
        new_uid = f"{uid}_circuit_{n}_heating_curve"
        for regid in (cfg.curve_radiator_param, cfg.curve_floor_param, cfg.curve_fancoil_param):
            if regid:
                old_to_new[f"{uid}_circuit_{n}_{regid}"] = (new_uid, n)

    _rename_unique_ids(hass, entry, old_to_new, "heating_curve")


def async_migrate_min_setpoint_cooling_limit_unique_id(hass, entry) -> None:
    """Move the circuit 2 "continuous cooling" number onto its circuit.

    Param 1311 used to be a 0-1 number on the controller device with unique_id
    `<uid>_1311`. It is now the per-circuit min cooling setpoint limit,
    `<uid>_circuit_2_1311`. Renaming the registry entry keeps the entity_id
    and history. Safe to call every setup.
    """
    uid = entry.runtime_data.get_device_uid()
    if not uid or uid == "unknown":
        return

    param = CIRCUITS[2].min_setpoint_cooling_limit_param
    old_to_new = {f"{uid}_{param}": (f"{uid}_circuit_2_{param}", 2)}
    _rename_unique_ids(hass, entry, old_to_new, "min_setpoint_cooling_limit")


def _rename_unique_ids(hass, entry, old_to_new: dict[str, tuple[str, int]], what: str) -> None:
    """Rename registry entries from old to new unique_ids, dropping duplicates."""
    reg = er.async_get(hass)
    for ent in list(er.async_entries_for_config_entry(reg, entry.entry_id)):
        if ent.platform != DOMAIN:
            continue
        match = old_to_new.get(ent.unique_id)
        if not match:
            continue
        new_uid, circuit_num = match
        # If the new uid already exists on a different entity, drop the old.
        existing = reg.async_get_entity_id(ent.domain, ent.platform, new_uid)
        if existing and existing != ent.entity_id:
            reg.async_remove(ent.entity_id)
            _LOGGER.info(
                "Cooling: removed duplicate legacy %s entity %s for circuit %s",
                what,
                ent.entity_id,
                circuit_num,
            )
            continue
        reg.async_update_entity(ent.entity_id, new_unique_id=new_uid)
        _LOGGER.info(
            "Cooling: migrated %s unique_id %s -> %s (circuit %s)",
            what,
            ent.unique_id,
            new_uid,
            circuit_num,
        )
