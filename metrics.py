"""Hitung metrik pemantauan dari deret waktu termal dan SO2 (fungsi murni)."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from scipy import stats

from config import TH


@dataclass(frozen=True)
class Metrics:
    last_date: str
    data_age_days: int
    so2_last_date: str
    so2_age_days: int
    frp_daily: float
    frp_roll7: float
    frp_roll30: float
    hotspots_daily: int
    ti4_max: float
    so2_max: float
    so2_roll30: float
    so2_15_max: float
    so2_slope_du_month: float
    so2_slope_p: float
    frp_slope: float
    frp_slope_p: float
    quiet_days_in_window: int
    came_from_quiet: bool
    calm_days_now: int

    def as_dict(self) -> dict:
        return asdict(self)


def _linreg(y: pd.Series) -> tuple[float, float]:
    """Kembalikan (slope per langkah, p-value); (0, 1) bila data kurang / degenerate."""
    s = pd.to_numeric(y, errors="coerce").dropna()
    if len(s) < 5 or s.nunique() < 2:
        return 0.0, 1.0
    x = np.arange(len(s), dtype=float)
    try:
        res = stats.linregress(x, s.to_numpy(dtype=float))
        return float(res.slope), float(res.pvalue)
    except (ValueError, FloatingPointError):
        return 0.0, 1.0


def _daily_series(df: pd.DataFrame, col: str, index: pd.DatetimeIndex,
                  fill_zero: bool) -> pd.Series:
    s = pd.to_numeric(df.set_index("date")[col], errors="coerce").reindex(index)
    return s.fillna(0.0) if fill_zero else s


def compute_metrics(thermal: pd.DataFrame, so2: pd.DataFrame,
                    today: pd.Timestamp | None = None) -> Metrics:
    """thermal: kolom date, frp_total, hotspots, ti4_max.
    so2: kolom date, so2_max_du, so2_mean_du, so2_15_du. Semuanya harian."""
    if today is None:
        today = pd.Timestamp.utcnow().tz_localize(None).normalize()

    start = min(thermal["date"].min(), so2["date"].min())
    end = max(thermal["date"].max(), so2["date"].max())
    idx = pd.date_range(start, end, freq="D")

    frp = _daily_series(thermal, "frp_total", idx, fill_zero=True)
    hs = _daily_series(thermal, "hotspots", idx, fill_zero=True)
    ti4 = _daily_series(thermal, "ti4_max", idx, fill_zero=False)
    s_max = _daily_series(so2, "so2_max_du", idx, fill_zero=False)
    s_15 = _daily_series(so2, "so2_15_du", idx, fill_zero=False)

    last = idx[-1]
    frp_r7 = frp.rolling(7, min_periods=3).mean()
    frp_r30 = frp.rolling(30, min_periods=10).mean()
    s_r30 = s_max.rolling(30, min_periods=10).mean()

    so2_slope_d, so2_p = _linreg(s_max.loc[last - pd.Timedelta(days=60):last])
    frp_slope_d, frp_p = _linreg(frp_r7.loc[last - pd.Timedelta(days=21):last])

    s_max_valid = s_max.dropna()
    s_15_valid = s_15.dropna()
    so2_last = s_max_valid.index[-1] if len(s_max_valid) else last
    so2_last_val = float(s_max_valid.iloc[-1]) if len(s_max_valid) else 0.0
    so2_15_val = float(s_15_valid.iloc[-1]) if len(s_15_valid) else 0.0

    # "tenang" harian = rata-rata 30 hari FRP dan SO2 di bawah ambang
    quiet_day = (frp_r30 < TH.quiet_frp_roll30) & (s_r30.fillna(0.0) < TH.quiet_so2_roll30)
    win = quiet_day.loc[last - pd.Timedelta(days=TH.quiet_window_days):last]
    quiet_days_in_window = int(win.sum())

    # hari tenang beruntun tepat sampai sekarang (untuk histeresis de-eskalasi)
    calm_run = 0
    for v in reversed(quiet_day.to_numpy()):
        if v:
            calm_run += 1
        else:
            break

    return Metrics(
        last_date=last.strftime("%Y-%m-%d"),
        data_age_days=int((today - last).days),
        so2_last_date=so2_last.strftime("%Y-%m-%d"),
        so2_age_days=int((today - so2_last).days),
        frp_daily=round(float(frp.iloc[-1]), 2),
        frp_roll7=round(float(frp_r7.iloc[-1]), 2),
        frp_roll30=round(float(frp_r30.iloc[-1]), 2),
        hotspots_daily=int(hs.iloc[-1]),
        ti4_max=round(float(ti4.iloc[-1]) if not np.isnan(ti4.iloc[-1]) else 0.0, 1),
        so2_max=round(so2_last_val, 2),
        so2_roll30=round(float(s_r30.iloc[-1]) if not np.isnan(s_r30.iloc[-1]) else 0.0, 2),
        so2_15_max=round(so2_15_val, 2),
        so2_slope_du_month=round(so2_slope_d * 30.0, 3),
        so2_slope_p=float(f"{so2_p:.2e}"),
        frp_slope=round(frp_slope_d, 3),
        frp_slope_p=float(f"{frp_p:.2e}"),
        quiet_days_in_window=quiet_days_in_window,
        came_from_quiet=quiet_days_in_window >= TH.quiet_days_required,
        calm_days_now=calm_run,
    )
