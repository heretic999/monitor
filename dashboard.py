"""Render dashboard HTML statis: banner status + grafik (PNG base64) + tabel metrik."""
from __future__ import annotations

import base64
import io
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from config import DASHBOARD_HTML, DISCLAIMER

_COLOR = {"NORMAL": "#2e7d32", "WATCH": "#f9a825", "WARNING": "#ef6c00", "ERUPTION": "#c62828"}


def _plot(thermal: pd.DataFrame, so2: pd.DataFrame) -> str:
    idx = pd.date_range(
        min(thermal["date"].min(), so2["date"].min()),
        max(thermal["date"].max(), so2["date"].max()), freq="D")
    frp = thermal.set_index("date")["frp_total"].reindex(idx).fillna(0.0)
    s_max = so2.set_index("date")["so2_max_du"].reindex(idx)

    win = idx >= (idx[-1] - pd.Timedelta(days=120))
    fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    ax[0].fill_between(idx[win], frp[win].clip(upper=250), color="#e57373", lw=0)
    ax[0].plot(idx[win], frp.rolling(7, min_periods=1).mean()[win].clip(upper=250),
               color="#c62828", lw=1.3)
    ax[0].set_ylabel("FRP/hari (MW)")
    ax[1].plot(idx[win], s_max[win].clip(upper=20), ".", ms=3, color="#90caf9")
    ax[1].plot(idx[win], s_max.rolling(14, min_periods=1).mean()[win].clip(upper=20),
               color="#1565c0", lw=1.3)
    ax[1].set_ylabel("SO₂ maks (DU)")
    ax[1].set_xlabel("120 hari terakhir")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _rows(metrics: dict) -> str:
    labels = {
        "last_date": "Tanggal data termal terakhir", "data_age_days": "Umur data termal (hari)",
        "so2_last_date": "Tanggal data SO₂ terakhir", "so2_age_days": "Umur data SO₂ (hari)",
        "frp_daily": "FRP harian (MW)", "frp_roll7": "FRP rata-rata 7 hari (MW)",
        "frp_roll30": "FRP rata-rata 30 hari (MW)", "hotspots_daily": "Jumlah hotspot",
        "ti4_max": "TI4 maks (K)", "so2_max": "SO₂ maks harian (DU)",
        "so2_roll30": "SO₂ rata-rata 30 hari (DU)", "so2_15_max": "SO₂ 15 km (DU)",
        "so2_slope_du_month": "Tren SO₂ 60 hari (DU/bulan)", "so2_slope_p": "p-value tren SO₂",
        "quiet_days_in_window": "Hari tenang (jendela 45 hari)",
        "came_from_quiet": "Dari kondisi tenang?", "calm_days_now": "Hari tenang beruntun",
    }
    return "".join(
        f"<tr><td>{labels.get(k, k)}</td><td><b>{metrics[k]}</b></td></tr>"
        for k in labels
    )


def render(state: str, reason: str, metrics: dict,
           thermal: pd.DataFrame, so2: pd.DataFrame) -> None:
    color = _COLOR.get(state, "#555")
    img = _plot(thermal, so2)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = f"""<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pemantau Anak Krakatau — {state}</title>
<style>
 body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f4f4f5;color:#18181b}}
 .wrap{{max-width:760px;margin:0 auto;padding:16px}}
 .banner{{background:{color};color:#fff;border-radius:12px;padding:20px;margin-bottom:16px}}
 .banner h1{{margin:0 0 6px;font-size:1.6rem}}
 .banner p{{margin:0;opacity:.95}}
 .card{{background:#fff;border-radius:12px;padding:16px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
 table{{width:100%;border-collapse:collapse;font-size:.92rem}}
 td{{padding:6px 8px;border-bottom:1px solid #eee}}
 td:last-child{{text-align:right}}
 img{{width:100%;border-radius:8px}}
 .disc{{font-size:.82rem;color:#71717a;line-height:1.5}}
 .ts{{font-size:.8rem;color:#a1a1aa}}
</style></head><body><div class="wrap">
 <div class="banner"><h1>🌋 Anak Krakatau — {state}</h1><p>{reason}</p></div>
 <div class="card"><img alt="grafik termal dan SO2" src="data:image/png;base64,{img}"></div>
 <div class="card"><table>{_rows(metrics)}</table></div>
 <div class="card disc">{DISCLAIMER}<br><span class="ts">Diperbarui otomatis: {now}</span></div>
</div></body></html>"""
    DASHBOARD_HTML.write_text(html, encoding="utf-8")
    print(f"  dashboard: {DASHBOARD_HTML}")
