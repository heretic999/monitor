"""Uji history.historical_context."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history import historical_context  # noqa: E402


def test_context_reports_percentile_and_peaks():
    dates = pd.date_range("2018-01-01", "2026-09-09", freq="D")
    frp = np.zeros(len(dates))
    d = pd.Series(frp, index=dates)
    d.loc["2018-09-15":"2018-11-15"] = 120.0          # puncak 2018
    d.loc["2022-05-01":"2022-06-01"] = 90.0           # puncak 2022
    d.loc["2026-08-20":"2026-09-09"] = 300.0          # sekarang, tertinggi

    df = pd.DataFrame({"date": dates, "frp_total": d.to_numpy()})
    ctx = historical_context(df)

    assert ctx["record_start"] == "2018-01-01"
    assert ctx["alltime_max_daily"] == 300.0
    assert ctx["episode_peaks"]["2018 (kolaps sektor)"] == 120.0
    assert ctx["episode_peaks"]["2026 (sekarang)"] == 300.0
    # kondisi sekarang termasuk yang tertinggi -> persentil tinggi
    assert ctx["percentile_vs_active_history"] > 80.0


def test_handles_short_record():
    dates = pd.date_range("2026-08-01", "2026-09-09", freq="D")
    df = pd.DataFrame({"date": dates, "frp_total": [5.0] * len(dates)})
    ctx = historical_context(df)
    assert ctx["record_days"] == len(dates)
    assert isinstance(ctx["now_frp_roll7"], float)
