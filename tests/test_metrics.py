"""Uji metrics.compute_metrics dengan data sintetis."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from metrics import compute_metrics  # noqa: E402


def _thermal(dates, frp, hotspots=None, ti4=None):
    n = len(dates)
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "frp_total": frp,
        "hotspots": hotspots if hotspots is not None else [0] * n,
        "ti4_max": ti4 if ti4 is not None else [np.nan] * n,
    })


def _so2(dates, so2_max, so2_15=None):
    n = len(dates)
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "so2_max_du": so2_max,
        "so2_mean_du": [v / 5 for v in so2_max],
        "so2_15_du": so2_15 if so2_15 is not None else [0.1] * n,
    })


def test_quiet_period_gives_low_rolls_and_came_from_quiet_false_when_still_quiet():
    dates = pd.date_range("2025-01-01", periods=90, freq="D")
    t = _thermal(dates, [0.4] * 90)
    s = _so2(dates, [1.5] * 90)
    m = compute_metrics(t, s, today=dates[-1])
    assert m.frp_roll30 < 3.0
    assert m.so2_roll30 < 3.0
    # Tenang terus -> jendela 45 hari penuh tenang -> came_from_quiet True,
    # tetapi frp_roll7 rendah sehingga bukan WATCH (diuji di state machine).
    assert m.came_from_quiet is True
    assert m.calm_days_now >= 30


def test_thermal_onset_after_quiet_is_detected():
    quiet = pd.date_range("2026-06-01", periods=45, freq="D")
    ramp = pd.date_range("2026-07-16", periods=20, freq="D")
    dates = quiet.append(ramp)
    frp = [0.4] * 45 + list(np.linspace(5, 120, 20))
    t = _thermal(dates, frp, hotspots=[0] * 45 + [10] * 20)
    s = _so2(dates, [1.5] * 45 + list(np.linspace(2, 15, 20)))
    m = compute_metrics(t, s, today=dates[-1])
    assert m.frp_roll7 > 40
    assert m.quiet_days_in_window >= 21
    assert m.came_from_quiet is True
    assert m.so2_slope_du_month > 0


def test_data_age_is_reported():
    dates = pd.date_range("2026-01-01", periods=40, freq="D")
    t = _thermal(dates, [1.0] * 40)
    s = _so2(dates, [2.0] * 40)
    m = compute_metrics(t, s, today=pd.Timestamp("2026-02-15"))
    assert m.data_age_days == (pd.Timestamp("2026-02-15") - dates[-1]).days


def test_missing_so2_does_not_crash():
    dates = pd.date_range("2026-01-01", periods=40, freq="D")
    t = _thermal(dates, [1.0] * 40)
    s = _so2(dates[:5], [2.0] * 5)  # SO2 berhenti lebih awal
    m = compute_metrics(t, s, today=dates[-1])
    assert isinstance(m.so2_roll30, float)
