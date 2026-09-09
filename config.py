"""Konfigurasi pemantau Anak Krakatau: path, area studi, ambang, kredensial."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

THERMAL_CSV = DATA_DIR / "thermal.csv"
SO2_CSV = DATA_DIR / "so2.csv"
STATE_JSON = DATA_DIR / "state.json"
DASHBOARD_HTML = ROOT / "dashboard.html"

# --- Area studi ---
BBOX_FIRMS = "105.30,-6.20,105.55,-6.00"  # barat,selatan,timur,utara
CENTER_LON = 105.423
CENTER_LAT = -6.102
SO2_BUFFER_M = 30_000
ISLAND_RECT = (105.407, -6.118, 105.440, -6.088)  # untuk SAR (fase lanjutan)

# --- Sumber data (kredensial via environment variable) ---
# FIRMS_MAP_KEY: ambil gratis di https://firms.modaps.eosdis.nasa.gov/api/map_key/
# Lokal: set di run_local.bat atau environment. CI: repository secret.
FIRMS_MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "")
FIRMS_SOURCES = ("VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT")
FIRMS_LOOKBACK_DAYS = 12  # tarik ulang jendela ini tiap run (menangkap revisi)
GEE_PROJECT = os.environ.get("GEE_PROJECT", "latihan-481319")
SO2_LOOKBACK_DAYS = 14
DU_PER_MOL_M2 = 2241.15

# --- Notifikasi (kosong = mode dry-run, hanya cetak ke layar) ---
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


@dataclass(frozen=True)
class Thresholds:
    """Ambang keputusan, diturunkan dari analisis rekaman 2018-2026."""

    quiet_frp_roll30: float = 3.0       # MW/hari - batas "tenang" termal
    quiet_so2_roll30: float = 3.0       # DU     - batas "tenang" SO2
    watch_frp_roll7: float = 5.0        # MW/hari - onset termal
    watch_so2_slope_du_month: float = 0.5
    warning_frp_roll7: float = 40.0     # MW/hari - eskalasi termal menetap
    eruption_frp_daily: float = 300.0   # MW     - level paroksismal
    eruption_hotspots_daily: int = 50
    quiet_days_required: int = 21       # hari tenang minimal utk "dari kondisi tenang"
    quiet_window_days: int = 45         # jendela pencarian hari tenang
    pvalue_sig: float = 0.05
    deescalate_calm_days: int = 30      # histeresis: turun status butuh tenang selama ini
    data_gap_days: int = 3


TH = Thresholds()

DISCLAIMER = (
    "Pemantauan otomatis pribadi berbasis data satelit terbuka (VIIRS FIRMS, "
    "TROPOMI/Sentinel-5P). BUKAN peringatan resmi dan tidak untuk pengambilan "
    "keputusan darurat. Sumber resmi: https://magma.esdm.go.id  (PVMBG / Badan Geologi)."
)
