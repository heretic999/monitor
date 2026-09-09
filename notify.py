"""Kirim notifikasi ke Discord webhook atau Telegram; fallback cetak ke layar (dry-run)."""
from __future__ import annotations

import requests

from config import DISCLAIMER, DISCORD_WEBHOOK, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN

_EMOJI = {"NORMAL": "🟢", "WATCH": "🟡", "WARNING": "🟠", "ERUPTION": "🔴", "GAP": "⚪"}


def build_message(state: str, reason: str, metrics: dict) -> str:
    icon = _EMOJI.get(state, "•")
    lines = [
        f"{icon} **Anak Krakatau — status: {state}**",
        f"_{reason}_",
        "",
        f"Data terakhir: {metrics['last_date']} (umur {metrics['data_age_days']} hari)",
        f"FRP: harian {metrics['frp_daily']} MW | rata2 7h {metrics['frp_roll7']} | "
        f"rata2 30h {metrics['frp_roll30']} MW | {metrics['hotspots_daily']} hotspot",
        f"SO₂ ({metrics['so2_last_date']}): maks {metrics['so2_max']} DU | "
        f"rata2 30h {metrics['so2_roll30']} DU | "
        f"tren 60h {metrics['so2_slope_du_month']:+} DU/bln (p={metrics['so2_slope_p']:.0e})",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def _send_discord(msg: str) -> bool:
    try:
        r = requests.post(DISCORD_WEBHOOK, json={"content": msg[:1950]}, timeout=30)
        return r.status_code in (200, 204)
    except requests.RequestException as exc:
        print(f"  ! Discord gagal: {exc}")
        return False


def _send_telegram(msg: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=30)
        return r.status_code == 200
    except requests.RequestException as exc:
        print(f"  ! Telegram gagal: {exc}")
        return False


def send(state: str, reason: str, metrics: dict) -> None:
    msg = build_message(state, reason, metrics)
    sent = False
    if DISCORD_WEBHOOK:
        sent = _send_discord(msg) or sent
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        sent = _send_telegram(msg) or sent
    if not sent:
        print("\n--- NOTIFIKASI (dry-run, tidak ada webhook dikonfigurasi) ---")
        print(msg)
        print("--- akhir notifikasi ---\n")
