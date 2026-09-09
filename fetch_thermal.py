"""Tarik deteksi hotspot VIIRS terbaru (NASA FIRMS) dan perbarui thermal.csv harian."""
from __future__ import annotations

import io
import time

import pandas as pd
import requests

from config import (
    BBOX_FIRMS, FIRMS_LOOKBACK_DAYS, FIRMS_MAP_KEY, FIRMS_SOURCES,
    HOTSPOT_MAP_DAYS, HOTSPOTS_CSV, THERMAL_CSV,
)

_HEADERS = {"User-Agent": "krakatau-monitor/1.0 (riset pribadi)"}
_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
_MAX_WINDOW = 5  # batas hari per permintaan FIRMS


def _fetch_window(source: str, start: pd.Timestamp, days: int) -> pd.DataFrame | None:
    url = f"{_API}/{FIRMS_MAP_KEY}/{source}/{BBOX_FIRMS}/{days}/{start:%Y-%m-%d}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=90)
    except requests.RequestException as exc:  # jaringan
        print(f"  ! {source} {start:%Y-%m-%d}: {exc}")
        return None
    if resp.status_code != 200 or not resp.text.lstrip().lower().startswith("latitude"):
        return None
    df = pd.read_csv(io.StringIO(resp.text))
    return df if len(df) else None


def fetch_recent_detections() -> pd.DataFrame:
    """Kembalikan deteksi mentah untuk jendela FIRMS_LOOKBACK_DAYS terakhir."""
    if not FIRMS_MAP_KEY:
        print("  ! FIRMS_MAP_KEY kosong — set environment variable / repository secret.")
        return pd.DataFrame()
    end = pd.Timestamp.utcnow().tz_localize(None).normalize() + pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=FIRMS_LOOKBACK_DAYS)
    frames: list[pd.DataFrame] = []
    for source in FIRMS_SOURCES:
        cursor = start
        while cursor < end:
            span = min(_MAX_WINDOW, (end - cursor).days)
            df = _fetch_window(source, cursor, span)
            if df is not None:
                df["source"] = source
                frames.append(df)
            cursor += pd.Timedelta(days=span)
            time.sleep(0.3)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _save_recent_hotspots(detections: pd.DataFrame) -> None:
    """Simpan deteksi individual (lat, lon, frp, waktu) untuk peta sebaran."""
    if detections.empty:
        return
    d = detections.copy()
    d["ts"] = pd.to_datetime(
        d["acq_date"] + " " + d["acq_time"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M") + pd.Timedelta(hours=7)
    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=HOTSPOT_MAP_DAYS)
    d = d[d["ts"] >= cutoff]
    out = (d[["latitude", "longitude", "frp", "bright_ti4", "ts"]]
           .drop_duplicates(["latitude", "longitude", "ts"])
           .sort_values("ts"))
    out["ts"] = out["ts"].dt.strftime("%Y-%m-%d %H:%M")
    out.to_csv(HOTSPOTS_CSV, index=False)
    print(f"  hotspot terkini: {len(out)} titik ({HOTSPOT_MAP_DAYS} hari) -> {HOTSPOTS_CSV.name}")


def _to_daily(detections: pd.DataFrame) -> pd.DataFrame:
    if detections.empty:
        return pd.DataFrame(columns=["date", "frp_total", "hotspots", "ti4_max"])
    d = detections.copy()
    d["ts"] = pd.to_datetime(
        d["acq_date"] + " " + d["acq_time"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M",
    ) + pd.Timedelta(hours=7)  # WIB
    d = d.drop_duplicates(["latitude", "longitude", "ts", "source"])
    daily = (
        d.set_index("ts")
        .resample("D")
        .agg(frp_total=("frp", "sum"),
             hotspots=("frp", "size"),
             ti4_max=("bright_ti4", "max"))
        .reset_index()
        .rename(columns={"ts": "date"})
    )
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    return daily


def update_thermal_csv() -> pd.DataFrame:
    """Gabungkan data baru ke THERMAL_CSV (baris terbaru menang) dan kembalikan seluruh riwayat."""
    detections = fetch_recent_detections()
    _save_recent_hotspots(detections)
    new_daily = _to_daily(detections)

    if THERMAL_CSV.exists():
        old = pd.read_csv(THERMAL_CSV)
    else:
        old = pd.DataFrame(columns=["date", "frp_total", "hotspots", "ti4_max"])

    merged = (
        pd.concat([old, new_daily], ignore_index=True)
        .drop_duplicates(subset="date", keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )
    merged.to_csv(THERMAL_CSV, index=False)
    merged["date"] = pd.to_datetime(merged["date"])
    print(f"  termal: {len(new_daily)} hari baru, total {len(merged)} hari "
          f"(sd {merged['date'].max():%Y-%m-%d})")
    return merged


if __name__ == "__main__":
    update_thermal_csv()
