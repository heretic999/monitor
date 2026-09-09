"""Render dashboard HTML statis: banner status + grafik + tabel metrik + konteks historis."""
from __future__ import annotations

import base64
import io
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from config import (  # noqa: E402
    DASHBOARD_HTML, DISCLAIMER, NOTIFY_CONFIGURED, REPO_URL, SO2_STALE_DAYS,
)
from history import historical_context  # noqa: E402

_COLOR = {"NORMAL": "#2e7d32", "WATCH": "#f9a825", "WARNING": "#ef6c00", "ERUPTION": "#c62828"}

_STATE_LEGEND = {
    "NORMAL": "aktivitas di bawah ambang",
    "WATCH": "onset termal dari kondisi tenang, atau tren SO₂ naik signifikan",
    "WARNING": "termal menetap tinggi + SO₂ ikut naik (pola eskalasi)",
    "ERUPTION": "FRP > 300 MW/hari, atau > 50 hotspot, atau status MAGMA naik",
}


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
    ax[1].set_xlabel("120 hari terakhir  (nilai dipotong: FRP 250 MW, SO₂ 20 DU)")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _metric_rows(metrics: dict) -> str:
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
        f"<tr><td>{v}</td><td><b>{metrics[k]}</b></td></tr>" for k, v in labels.items()
    )


def _history_rows(ctx: dict) -> str:
    r = [
        ("Rekaman", f"{ctx['record_start']} – sekarang ({ctx['record_days']} hari)"),
        ("FRP rata-rata 7 hari sekarang", f"{ctx['now_frp_roll7']} MW"),
        ("Persentil vs hari aktif historis", f"{ctx['percentile_vs_active_history']} %"),
        ("FRP harian tertinggi sepanjang rekaman", f"{ctx['alltime_max_daily']:.0f} MW"),
    ]
    for name, peak in ctx["episode_peaks"].items():
        r.append((f"Puncak FRP harian — {name}", f"{peak:.0f} MW"))
    return "".join(f"<tr><td>{a}</td><td><b>{b}</b></td></tr>" for a, b in r)


def _so2_stale_banner(metrics: dict) -> str:
    age = metrics.get("so2_age_days", 0)
    if age <= SO2_STALE_DAYS:
        return ""
    return (
        f'<div class="card warn">⚠️ <b>Data SO₂ basi</b> — terakhir {metrics["so2_last_date"]} '
        f'({age} hari lalu). Kemungkinan produk OFFL/NRTI tertunda, atau pengambilan SO₂ di CI '
        f'belum aktif (butuh <code>EE_SERVICE_ACCOUNT_JSON</code>). Metrik & status di bawah '
        f'sebagian besar dari data <b>termal</b>.</div>'
    )


def _footer(now: str) -> str:
    legend = "".join(
        f"<li><b>{s}</b> — {d}</li>" for s, d in _STATE_LEGEND.items()
    )
    alert = ("aktif — notifikasi terkirim saat status berubah"
             if NOTIFY_CONFIGURED else
             "dorman — set <code>DISCORD_WEBHOOK</code> atau <code>TELEGRAM_TOKEN</code> untuk mengaktifkan")
    return f"""
 <div class="card disc">
  <p><b>Cara kerja.</b> Setiap hari: tarik hotspot VIIRS (NASA FIRMS) + kolom SO₂ TROPOMI
  (Sentinel-5P), hitung rata-rata bergerak & regresi linear tren, bandingkan dengan ambang
  yang dikalibrasi dari rekaman 2018–2026, lalu tetapkan status. Rincian & rumus:
  <a href="{REPO_URL}#readme">README</a> / Lampiran A laporan.</p>
  <p><b>Arti status</b> (dengan histeresis — turun status butuh 30 hari tenang):</p>
  <ul>{legend}</ul>
  <p><b>Notifikasi:</b> {alert}.</p>
  <p>{DISCLAIMER}</p>
  <span class="ts">Diperbarui otomatis: {now} · <a href="{REPO_URL}">kode sumber</a></span>
 </div>"""


def render(state: str, reason: str, metrics: dict,
           thermal: pd.DataFrame, so2: pd.DataFrame) -> None:
    color = _COLOR.get(state, "#555")
    img = _plot(thermal, so2)
    ctx = historical_context(thermal)
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
 .card.warn{{background:#fff8e1;border:1px solid #ffe082;font-size:.9rem;line-height:1.5}}
 h2{{font-size:1rem;margin:0 0 10px}}
 table{{width:100%;border-collapse:collapse;font-size:.92rem}}
 td{{padding:6px 8px;border-bottom:1px solid #eee}}
 td:last-child{{text-align:right;white-space:nowrap}}
 img{{width:100%;border-radius:8px}}
 .disc{{font-size:.84rem;color:#52525b;line-height:1.55}}
 .disc ul{{margin:6px 0;padding-left:20px}}
 .disc a{{color:#1565c0}}
 .ts{{font-size:.8rem;color:#a1a1aa}}
 code{{background:#f4f4f5;padding:1px 4px;border-radius:4px;font-size:.85em}}
</style></head><body><div class="wrap">
 <div class="banner"><h1>🌋 Anak Krakatau — {state}</h1><p>{reason}</p></div>
 {_so2_stale_banner(metrics)}
 <div class="card"><img alt="grafik termal dan SO2" src="data:image/png;base64,{img}"></div>
 <div class="card"><h2>Metrik terkini</h2><table>{_metric_rows(metrics)}</table></div>
 <div class="card"><h2>Konteks historis (2018–sekarang)</h2><table>{_history_rows(ctx)}</table></div>
 {_footer(now)}
</div></body></html>"""
    DASHBOARD_HTML.write_text(html, encoding="utf-8")
    print(f"  dashboard: {DASHBOARD_HTML}")
