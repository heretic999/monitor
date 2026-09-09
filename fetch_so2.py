"""Tarik SO2 TROPOMI/Sentinel-5P terbaru via Google Earth Engine dan perbarui so2.csv harian."""
from __future__ import annotations

import json
import os
import tempfile

import pandas as pd

from config import CENTER_LAT, CENTER_LON, DU_PER_MOL_M2, GEE_PROJECT, SO2_BUFFER_M, SO2_CSV, SO2_LOOKBACK_DAYS

_BANDS = ["SO2_column_number_density", "SO2_column_number_density_15km"]


def _init_ee():
    """Autentikasi GEE. Prioritas: service account (untuk CI) -> kredensial lokal."""
    import ee

    sa_json = os.environ.get("EE_SERVICE_ACCOUNT_JSON", "")
    if sa_json:
        info = json.loads(sa_json)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(info, fh)
            key_path = fh.name
        creds = ee.ServiceAccountCredentials(info["client_email"], key_path)
        ee.Initialize(creds, project=GEE_PROJECT)
        return ee

    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        ee.Authenticate()  # interaktif hanya bila belum ada kredensial lokal
        ee.Initialize(project=GEE_PROJECT)
    return ee


def fetch_recent_so2() -> pd.DataFrame:
    """Kembalikan SO2 harian (DU) untuk jendela SO2_LOOKBACK_DAYS terakhir."""
    ee = _init_ee()
    region = ee.Geometry.Point([CENTER_LON, CENTER_LAT]).buffer(SO2_BUFFER_M).bounds()
    end = pd.Timestamp.utcnow().tz_localize(None).normalize() + pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=SO2_LOOKBACK_DAYS)

    offl = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_SO2").select(_BANDS)
    nrti = ee.ImageCollection("COPERNICUS/S5P/NRTI/L3_SO2").select(_BANDS)
    col = (offl.merge(nrti)
           .filterDate(str(start.date()), str(end.date()))
           .filterBounds(region))

    def per_image(img):
        stats = img.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
            geometry=region, scale=7000, maxPixels=int(1e9), bestEffort=True,
        )
        return ee.Feature(None, {
            "date": img.date().format("YYYY-MM-dd"),
            "so2_mean": stats.get("SO2_column_number_density_mean"),
            "so2_max": stats.get("SO2_column_number_density_max"),
            "so2_15_mean": stats.get("SO2_column_number_density_15km_mean"),
        })

    feats = col.map(per_image).getInfo().get("features", [])
    df = pd.DataFrame([f["properties"] for f in feats]).dropna(subset=["so2_max"])
    if df.empty:
        return pd.DataFrame(columns=["date", "so2_max_du", "so2_mean_du", "so2_15_du"])

    df = (df.groupby("date", as_index=False)
          .agg(so2_mean=("so2_mean", "mean"),
               so2_max=("so2_max", "max"),
               so2_15_mean=("so2_15_mean", "mean")))
    df["so2_max_du"] = df["so2_max"] * DU_PER_MOL_M2
    df["so2_mean_du"] = df["so2_mean"] * DU_PER_MOL_M2
    df["so2_15_du"] = df["so2_15_mean"] * DU_PER_MOL_M2
    return df[["date", "so2_max_du", "so2_mean_du", "so2_15_du"]]


def update_so2_csv() -> pd.DataFrame:
    try:
        new = fetch_recent_so2()
    except Exception as exc:  # GEE gagal / tak terautentikasi
        print(f"  ! SO2 gagal diambil: {exc}")
        new = pd.DataFrame(columns=["date", "so2_max_du", "so2_mean_du", "so2_15_du"])

    if SO2_CSV.exists():
        old = pd.read_csv(SO2_CSV)
    else:
        old = pd.DataFrame(columns=["date", "so2_max_du", "so2_mean_du", "so2_15_du"])

    merged = (
        pd.concat([old, new], ignore_index=True)
        .drop_duplicates(subset="date", keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )
    merged.to_csv(SO2_CSV, index=False, float_format="%.6g")
    merged["date"] = pd.to_datetime(merged["date"])
    tail = f"(sd {merged['date'].max():%Y-%m-%d})" if len(merged) else "(kosong)"
    print(f"  SO2: {len(new)} hari baru, total {len(merged)} hari {tail}")
    return merged


if __name__ == "__main__":
    update_so2_csv()
