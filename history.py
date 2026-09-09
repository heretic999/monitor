"""Konteks historis: bandingkan kondisi termal saat ini dengan rekaman 2018-sekarang."""
from __future__ import annotations

import numpy as np
import pandas as pd

# Jendela episode terkenal (untuk perbandingan puncak FRP harian).
_EPISODES = {
    "2018 (kolaps sektor)": ("2018-09-01", "2019-01-31"),
    "2020 (sub-Plinian)": ("2020-03-15", "2020-05-15"),
    "2022 (Strombolian)": ("2022-04-01", "2022-08-01"),
    "2026 (sekarang)": ("2026-08-01", "2100-01-01"),
}


def historical_context(thermal: pd.DataFrame) -> dict:
    """thermal: kolom date (datetime), frp_total. Kembalikan ringkasan perbandingan."""
    df = thermal.copy()
    df["date"] = pd.to_datetime(df["date"])
    s = df.set_index("date")["frp_total"].astype(float)
    idx = pd.date_range(s.index.min(), s.index.max(), freq="D")
    s = s.reindex(idx).fillna(0.0)
    r7 = s.rolling(7, min_periods=3).mean()

    now_r7 = float(r7.iloc[-1])
    # persentil rata-rata 7 hari saat ini terhadap seluruh rekaman (hanya hari aktif > 1 MW)
    active = r7[r7 > 1.0]
    pct = float((active < now_r7).mean() * 100) if len(active) else 0.0

    peaks = {}
    for name, (a, b) in _EPISODES.items():
        seg = s.loc[a:b]
        peaks[name] = round(float(seg.max()), 0) if len(seg) else 0.0

    return {
        "record_start": s.index.min().strftime("%Y-%m-%d"),
        "record_days": int(len(s)),
        "now_frp_roll7": round(now_r7, 1),
        "percentile_vs_active_history": round(pct, 1),
        "alltime_max_daily": round(float(s.max()), 0),
        "episode_peaks": peaks,
    }
