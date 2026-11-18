"""Tests for the beta-polish round on the cooling feature.

Covers the fan_coil migration, the stable heating_curve unique_id, and the
entity-registry rename for legacy heating_curve entries.
"""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.econext.climate import CIRCUITS
from custom_components.econext.const import (
    CIRCUIT_NUMBERS,
    DOMAIN,
    EconextNumberEntityDescription,
)
from custom_components.econext.cooling.migrate import (
    async_ensure_fan_coil,
    async_migrate_heating_curve_unique_ids,
    async_migrate_min_setpoint_cooling_limit_unique_id,
)
from custom_components.econext.coordinator import EconextCoordinator
from custom_components.econext.number import EconextNumber


@pytest.fixture(autouse=True)
def patch_frame_helper():
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


# ---------- async_ensure_fan_coil ----------


class _FakeCoord:
    def __init__(self, params: dict) -> None:
        self._params = {str(k): v for k, v in params.items()}
        self.writes: list[tuple[str, float]] = []

    def get_param_value(self, pid):
        return self._params.get(str(pid))

    async def async_set_param(self, pid, value):
        self._params[str(pid)] = value
        self.writes.append((str(pid), value))
        return True


async def test_ensure_fan_coil_noop_when_already_fan_coil():
    cfg = CIRCUITS[2]
    coord = _FakeCoord({cfg.type_settings_param: 3, cfg.curve_fancoil_param: 1.2})
    await async_ensure_fan_coil(coord, 2)
    assert coord.writes == []


async def test_ensure_fan_coil_copies_curve_before_flipping_type():
    # Circuit 2 starts as UFH (type=2) with curve_floor value 1.7.
    cfg = CIRCUITS[2]
    coord = _FakeCoord(
        {
            cfg.type_settings_param: 2,
            cfg.curve_floor_param: 1.7,
            cfg.curve_fancoil_param: 0.5,
        }
    )
    await async_ensure_fan_coil(coord, 2)

    # The curve value must be carried over to the fan_coil register BEFORE the
    # type flip, so the heating_curve entity reads the same after.
    assert coord.writes[0] == (str(cfg.curve_fancoil_param), 1.7)
    assert coord.writes[1] == (str(cfg.type_settings_param), 3)


async def test_ensure_fan_coil_from_radiator_uses_radiator_curve():
    cfg = CIRCUITS[1]
    coord = _FakeCoord(
        {
            cfg.type_settings_param: 1,  # radiator
            cfg.curve_radiator_param: 2.4,
            cfg.curve_fancoil_param: 0.0,
        }
    )
    await async_ensure_fan_coil(coord, 1)

    assert coord.writes[0] == (str(cfg.curve_fancoil_param), 2.4)
    assert coord.writes[1] == (str(cfg.type_settings_param), 3)


async def test_ensure_fan_coil_silent_when_type_unknown():
    cfg = CIRCUITS[3]
    coord = _FakeCoord({})  # type register missing
    await async_ensure_fan_coil(coord, 3)
    assert coord.writes == []


# ---------- stable heating_curve unique_id ----------


@pytest.fixture
def coordinator(all_params_parsed: dict) -> EconextCoordinator:
    hass = MagicMock()
    api = MagicMock()
    c = EconextCoordinator(hass, api)
    c.data = all_params_parsed
    return c


def test_heating_curve_description_has_stable_unique_id_key():
    desc = next(n for n in CIRCUIT_NUMBERS if n.key == "heating_curve")
    assert desc.unique_id_key == "heating_curve"


def test_heating_curve_unique_id_is_stable_across_curve_param(coordinator):
    # Two descriptions with DIFFERENT param_ids (radiator vs fan_coil curves)
    # but the SAME unique_id_key must produce the SAME entity unique_id.
    radiator_desc = EconextNumberEntityDescription(
        key="heating_curve",
        param_id="273",  # curve_radiator_param for circuit 1
        unique_id_key="heating_curve",
    )
    fancoil_desc = EconextNumberEntityDescription(
        key="heating_curve",
        param_id="586",  # curve_fancoil_param for circuit 1
        unique_id_key="heating_curve",
    )

    e1 = EconextNumber(coordinator, radiator_desc, device_id="circuit_1")
    e2 = EconextNumber(coordinator, fancoil_desc, device_id="circuit_1")

    assert e1.unique_id == e2.unique_id
    assert e1.unique_id.endswith("_circuit_1_heating_curve")


def test_other_numbers_keep_param_id_based_unique_id(coordinator):
    # Descriptions without unique_id_key keep the legacy param-id form.
    desc = EconextNumberEntityDescription(key="min_break_time", param_id="499")
    e = EconextNumber(coordinator, desc)
    assert e.unique_id.endswith("_499")


# ---------- entity-registry migration ----------


class _RegEntry:
    def __init__(self, entity_id: str, unique_id: str, platform: str = DOMAIN, domain: str = "number") -> None:
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.platform = platform
        self.domain = domain


class _FakeRegistry:
    def __init__(self, entries: list[_RegEntry]) -> None:
        self.entries = entries
        self.renames: list[tuple[str, str]] = []
        self.removed: list[str] = []

    def async_get_entity_id(self, domain, platform, uid):
        for e in self.entries:
            if e.domain == domain and e.platform == platform and e.unique_id == uid:
                return e.entity_id
        return None

    def async_update_entity(self, entity_id, new_unique_id=None):
        self.renames.append((entity_id, new_unique_id))
        for e in self.entries:
            if e.entity_id == entity_id:
                e.unique_id = new_unique_id

    def async_remove(self, entity_id):
        self.removed.append(entity_id)
        self.entries = [e for e in self.entries if e.entity_id != entity_id]


def _make_entry(uid: str = "TESTUID"):
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.runtime_data.get_device_uid.return_value = uid
    return entry


def test_migration_renames_legacy_curve_unique_ids():
    uid = "TESTUID"
    # Circuit 2's UFH curve param is 274; an old install would have the
    # heating_curve number registered under `_circuit_2_324`.
    legacy = _RegEntry("number.x_heating_curve", f"{uid}_circuit_2_324")
    unrelated = _RegEntry("sensor.x_thermostat", f"{uid}_circuit_2_327")
    reg = _FakeRegistry([legacy, unrelated])

    entry = _make_entry(uid)
    with patch(
        "custom_components.econext.cooling.migrate.er.async_get", return_value=reg
    ), patch(
        "custom_components.econext.cooling.migrate.er.async_entries_for_config_entry",
        return_value=reg.entries,
    ):
        async_migrate_heating_curve_unique_ids(MagicMock(), entry)

    assert reg.renames == [("number.x_heating_curve", f"{uid}_circuit_2_heating_curve")]
    assert legacy.unique_id == f"{uid}_circuit_2_heating_curve"
    # Unrelated entries are left alone.
    assert unrelated.unique_id == f"{uid}_circuit_2_327"


def test_migration_no_op_when_already_stable():
    uid = "TESTUID"
    stable = _RegEntry("number.x_heating_curve", f"{uid}_circuit_2_heating_curve")
    reg = _FakeRegistry([stable])
    entry = _make_entry(uid)
    with patch(
        "custom_components.econext.cooling.migrate.er.async_get", return_value=reg
    ), patch(
        "custom_components.econext.cooling.migrate.er.async_entries_for_config_entry",
        return_value=reg.entries,
    ):
        async_migrate_heating_curve_unique_ids(MagicMock(), entry)

    assert reg.renames == []
    assert reg.removed == []


def test_migration_drops_legacy_duplicate_if_new_already_exists():
    uid = "TESTUID"
    stable = _RegEntry("number.x_heating_curve", f"{uid}_circuit_2_heating_curve")
    legacy = _RegEntry("number.x_heating_curve_2", f"{uid}_circuit_2_324")
    reg = _FakeRegistry([stable, legacy])
    entry = _make_entry(uid)
    with patch(
        "custom_components.econext.cooling.migrate.er.async_get", return_value=reg
    ), patch(
        "custom_components.econext.cooling.migrate.er.async_entries_for_config_entry",
        return_value=list(reg.entries),
    ):
        async_migrate_heating_curve_unique_ids(MagicMock(), entry)

    assert reg.removed == ["number.x_heating_curve_2"]
    assert reg.renames == []


def test_migration_moves_circuit_2_cooling_limit_onto_its_circuit():
    uid = "TESTUID"
    # The old 0-1 "continuous cooling" number sat on the controller device.
    legacy = _RegEntry("number.x_circuit_2_continuous_cooling", f"{uid}_1311")
    other_controller = _RegEntry("number.x_circuit_temperature_correction", f"{uid}_1309")
    reg = _FakeRegistry([legacy, other_controller])

    entry = _make_entry(uid)
    with patch(
        "custom_components.econext.cooling.migrate.er.async_get", return_value=reg
    ), patch(
        "custom_components.econext.cooling.migrate.er.async_entries_for_config_entry",
        return_value=reg.entries,
    ):
        async_migrate_min_setpoint_cooling_limit_unique_id(MagicMock(), entry)
        # Second run finds nothing left to rename.
        async_migrate_min_setpoint_cooling_limit_unique_id(MagicMock(), entry)

    assert reg.renames == [("number.x_circuit_2_continuous_cooling", f"{uid}_circuit_2_1311")]
    assert other_controller.unique_id == f"{uid}_1309"
