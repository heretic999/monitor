"""Uji mesin status: target_state, histeresis, celah data."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from metrics import Metrics  # noqa: E402
from state_machine import target_state, next_state, data_gap_alert  # noqa: E402


def mk(**kw) -> Metrics:
    base = dict(
        last_date="2026-09-01", data_age_days=1,
        so2_last_date="2026-09-01", so2_age_days=1,
        frp_daily=0.0, frp_roll7=0.0, frp_roll30=0.0,
        hotspots_daily=0, ti4_max=0.0,
        so2_max=1.0, so2_roll30=1.0, so2_15_max=0.1,
        so2_slope_du_month=0.0, so2_slope_p=0.9,
        frp_slope=0.0, frp_slope_p=0.9,
        quiet_days_in_window=45, came_from_quiet=True, calm_days_now=45,
    )
    base.update(kw)
    return Metrics(**base)


def test_normal_when_everything_low():
    st, _ = target_state(mk())
    assert st == "NORMAL"


def test_watch_on_thermal_onset_from_quiet():
    st, _ = target_state(mk(frp_roll7=8.0, came_from_quiet=True, quiet_days_in_window=30))
    assert st == "WATCH"


def test_no_watch_if_not_from_quiet():
    st, _ = target_state(mk(frp_roll7=8.0, came_from_quiet=False, quiet_days_in_window=5))
    assert st == "NORMAL"


def test_watch_on_so2_ramp():
    st, _ = target_state(mk(so2_slope_du_month=1.1, so2_slope_p=1e-6, so2_roll30=4.0))
    assert st == "WATCH"


def test_warning_on_sustained_thermal_plus_so2():
    st, _ = target_state(mk(frp_roll7=60.0, so2_roll30=7.0,
                            so2_slope_du_month=1.0, so2_slope_p=1e-6))
    assert st == "WARNING"


def test_eruption_on_high_frp():
    st, _ = target_state(mk(frp_daily=756.0, hotspots_daily=205))
    assert st == "ERUPTION"


def test_eruption_on_magma_escalation():
    st, _ = target_state(mk(frp_daily=20.0), magma_escalated=True)
    assert st == "ERUPTION"


def test_escalation_is_immediate():
    new, _, changed = next_state("NORMAL", mk(frp_daily=756.0, hotspots_daily=205))
    assert new == "ERUPTION" and changed is True


def test_deescalation_needs_hysteresis():
    calm_metrics = mk(frp_daily=0.0, frp_roll7=0.0, frp_roll30=0.0, calm_days_now=5)
    held, _, changed = next_state("WARNING", calm_metrics)
    assert held == "WARNING" and changed is False

    long_calm = mk(frp_daily=0.0, frp_roll7=0.0, frp_roll30=0.0, calm_days_now=35)
    dropped, _, changed = next_state("WARNING", long_calm)
    assert dropped == "NORMAL" and changed is True


def test_data_gap_alert():
    assert data_gap_alert(mk(data_age_days=5)) is True
    assert data_gap_alert(mk(data_age_days=1)) is False
