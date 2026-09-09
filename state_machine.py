"""Mesin status pemantauan: NORMAL -> WATCH -> WARNING -> ERUPTION (dengan histeresis)."""
from __future__ import annotations

from config import TH
from metrics import Metrics

STATES = ("NORMAL", "WATCH", "WARNING", "ERUPTION")
_RANK = {s: i for i, s in enumerate(STATES)}


def _eruption(m: Metrics, magma_escalated: bool) -> bool:
    return (m.frp_daily > TH.eruption_frp_daily
            or m.hotspots_daily > TH.eruption_hotspots_daily
            or magma_escalated)


def _warning(m: Metrics) -> bool:
    thermal_sustained = m.frp_roll7 > TH.warning_frp_roll7
    frp_rising = m.frp_slope > 0 and m.frp_slope_p < TH.pvalue_sig
    so2_rising = (m.so2_slope_du_month > TH.watch_so2_slope_du_month
                  and m.so2_slope_p < TH.pvalue_sig)
    so2_elevated = m.so2_roll30 > 2 * TH.quiet_so2_roll30
    return thermal_sustained and (frp_rising or so2_rising or so2_elevated)


def _watch(m: Metrics) -> bool:
    thermal_onset = m.frp_roll7 > TH.watch_frp_roll7 and m.came_from_quiet
    so2_ramp = (m.so2_slope_du_month > TH.watch_so2_slope_du_month
                and m.so2_slope_p < TH.pvalue_sig
                and m.so2_roll30 > TH.quiet_so2_roll30)
    return thermal_onset or so2_ramp


def target_state(m: Metrics, magma_escalated: bool = False) -> tuple[str, str]:
    """Status yang diminta oleh data saat ini, tanpa histeresis. Kembalikan (status, alasan)."""
    if _eruption(m, magma_escalated):
        return "ERUPTION", (
            f"FRP harian {m.frp_daily} MW / {m.hotspots_daily} hotspot"
            + (" / status MAGMA naik" if magma_escalated else "")
        )
    if _warning(m):
        return "WARNING", (
            f"termal menetap (rata2 7h {m.frp_roll7} MW) + "
            f"SO2 rata2 30h {m.so2_roll30} DU, tren SO2 {m.so2_slope_du_month:+} DU/bln "
            f"(p={m.so2_slope_p:.0e})"
        )
    if _watch(m):
        return "WATCH", (
            f"onset dari kondisi tenang: rata2 7h FRP {m.frp_roll7} MW "
            f"({m.quiet_days_in_window} hari tenang dlm {TH.quiet_window_days} hari), "
            f"tren SO2 {m.so2_slope_du_month:+} DU/bln"
        )
    return "NORMAL", (
        f"rata2 30h FRP {m.frp_roll30} MW, SO2 {m.so2_roll30} DU - di bawah ambang"
    )


def next_state(prev: str, m: Metrics, magma_escalated: bool = False) -> tuple[str, str, bool]:
    """Terapkan histeresis. Kembalikan (status_baru, alasan, apakah_transisi)."""
    tgt, reason = target_state(m, magma_escalated)
    if prev not in STATES:
        prev = "NORMAL"

    # Eskalasi: langsung ikuti target bila lebih tinggi.
    if _RANK[tgt] > _RANK[prev]:
        return tgt, reason, True

    # De-eskalasi: hanya turun bila sudah tenang cukup lama (histeresis).
    if _RANK[tgt] < _RANK[prev]:
        if m.calm_days_now >= TH.deescalate_calm_days:
            return tgt, f"mereda: {m.calm_days_now} hari tenang beruntun", True
        return prev, f"menahan {prev} (baru {m.calm_days_now}/{TH.deescalate_calm_days} hari tenang)", False

    return prev, reason, False


def data_gap_alert(m: Metrics) -> bool:
    return m.data_age_days > TH.data_gap_days
