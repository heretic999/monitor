"""Isi data/thermal.csv dan data/so2.csv dengan riwayat dari pemindaian kontinu 2018-2026.

Jalankan SEKALI sebelum run.py pertama, agar metrik rata-rata 30 hari / tren 60 hari
punya konteks. Sumber: ../firms_kontinu.csv dan ../s5p_so2_kontinu.csv (hasil skrip 21-22).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import HOTSPOT_MAP_DAYS, HOTSPOTS_CSV, SO2_CSV, THERMAL_CSV

# Cari sumber seed di ./seed_data/ (repo standalone) lalu ../ (folder proyek asli).
_HERE = Path(__file__).resolve().parent
_CANDIDATES = (_HERE / "seed_data", _HERE.parent)


def _find(name: str) -> Path | None:
    for base in _CANDIDATES:
        p = base / name
        if p.exists():
            return p
    return None


def seed_thermal() -> None:
    src = _find("firms_kontinu.csv")
    if src is None:
        print("  ! firms_kontinu.csv tidak ditemukan di seed_data/ atau ../ — lewati")
        return
    d = pd.read_csv(src, parse_dates=["waktu_wib"])
    daily = (d.set_index("waktu_wib").resample("D")
             .agg(frp_total=("frp", "sum"),
                  hotspots=("frp", "size"),
                  ti4_max=("bright_ti4", "max"))
             .reset_index().rename(columns={"waktu_wib": "date"}))
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    daily.to_csv(THERMAL_CSV, index=False)
    print(f"  seed termal: {len(daily)} hari -> {THERMAL_CSV}")


def seed_so2() -> None:
    src = _find("s5p_so2_kontinu.csv")
    if src is None:
        print("  ! s5p_so2_kontinu.csv tidak ditemukan di seed_data/ atau ../ — lewati")
        return
    d = pd.read_csv(src, parse_dates=["tanggal"])
    out = pd.DataFrame({
        "date": d["tanggal"].dt.strftime("%Y-%m-%d"),
        "so2_max_du": d["so2_max_DU"],
        "so2_mean_du": d["so2_mean_DU"],
        "so2_15_du": d["so2_15_mean_DU"],
    })
    out.to_csv(SO2_CSV, index=False)
    print(f"  seed SO2: {len(out)} hari -> {SO2_CSV}")


def seed_hotspots() -> None:
    src = _find("firms_kontinu.csv")
    if src is None:
        return
    d = pd.read_csv(src, parse_dates=["waktu_wib"])
    cutoff = d["waktu_wib"].max() - pd.Timedelta(days=HOTSPOT_MAP_DAYS)
    d = d[d["waktu_wib"] >= cutoff]
    out = (d[["latitude", "longitude", "frp", "bright_ti4", "waktu_wib"]]
           .rename(columns={"waktu_wib": "ts"})
           .drop_duplicates(["latitude", "longitude", "ts"])
           .sort_values("ts"))
    out["ts"] = out["ts"].dt.strftime("%Y-%m-%d %H:%M")
    out.to_csv(HOTSPOTS_CSV, index=False)
    print(f"  seed hotspot: {len(out)} titik -> {HOTSPOTS_CSV}")


if __name__ == "__main__":
    seed_thermal()
    seed_so2()
    seed_hotspots()
