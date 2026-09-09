"""Isi data/*.csv dengan riwayat dari pemindaian kontinu 2018-2026 — SEKALI saja.

Bersifat non-destruktif: berkas yang sudah ada TIDAK ditimpa (agar tidak menghapus
data harian yang sudah terkumpul dari run.py). Pakai --force untuk menimpa.

Sumber: seed_data/firms_kontinu.csv & seed_data/s5p_so2_kontinu.csv (atau ../ pada folder proyek asli).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from config import HOTSPOT_MAP_DAYS, HOTSPOTS_CSV, SO2_CSV, THERMAL_CSV

_HERE = Path(__file__).resolve().parent
_CANDIDATES = (_HERE / "seed_data", _HERE.parent)
_FORCE = "--force" in sys.argv


def _find(name: str) -> Path | None:
    for base in _CANDIDATES:
        p = base / name
        if p.exists():
            return p
    return None


def _guard(target: Path) -> bool:
    if target.exists() and not _FORCE:
        print(f"  lewati {target.name} — sudah ada (pakai --force untuk menimpa)")
        return False
    return True


def seed_thermal() -> None:
    if not _guard(THERMAL_CSV):
        return
    src = _find("firms_kontinu.csv")
    if src is None:
        print("  ! firms_kontinu.csv tidak ditemukan — lewati")
        return
    d = pd.read_csv(src, parse_dates=["waktu_wib"])
    daily = (d.set_index("waktu_wib").resample("D")
             .agg(frp_total=("frp", "sum"),
                  hotspots=("frp", "size"),
                  ti4_max=("bright_ti4", "max"))
             .reset_index().rename(columns={"waktu_wib": "date"}))
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    daily.to_csv(THERMAL_CSV, index=False)
    print(f"  seed termal: {len(daily)} hari -> {THERMAL_CSV.name}")


def seed_so2() -> None:
    if not _guard(SO2_CSV):
        return
    src = _find("s5p_so2_kontinu.csv")
    if src is None:
        print("  ! s5p_so2_kontinu.csv tidak ditemukan — lewati")
        return
    d = pd.read_csv(src, parse_dates=["tanggal"])
    out = pd.DataFrame({
        "date": d["tanggal"].dt.strftime("%Y-%m-%d"),
        "so2_max_du": d["so2_max_DU"],
        "so2_mean_du": d["so2_mean_DU"],
        "so2_15_du": d["so2_15_mean_DU"],
    })
    out.to_csv(SO2_CSV, index=False)
    print(f"  seed SO2: {len(out)} hari -> {SO2_CSV.name}")


def seed_hotspots() -> None:
    if not _guard(HOTSPOTS_CSV):
        return
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
    print(f"  seed hotspot: {len(out)} titik -> {HOTSPOTS_CSV.name}")


if __name__ == "__main__":
    seed_thermal()
    seed_so2()
    seed_hotspots()
