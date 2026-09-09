"""Ambil status terbaru Anak Krakatau dari MAGMA Indonesia (best-effort, boleh gagal)."""
from __future__ import annotations

import re

import requests

_URL = "https://magma.esdm.go.id/v1/gunung-api/tinjau/kelud"  # placeholder; lihat catatan
_KRAKATAU_PAGE = "https://magma.esdm.go.id/v1/gunung-api"
_HEADERS = {"User-Agent": "krakatau-monitor/1.0"}

_LEVEL_MAP = {"normal": 1, "waspada": 2, "siaga": 3, "awas": 4}


def get_alert_level() -> int | None:
    """Kembalikan level status (1-4) Anak Krakatau, atau None bila tidak bisa diambil.

    MAGMA tidak menyediakan endpoint publik stabil untuk satu gunung; strategi:
    coba beberapa URL yang diketahui, cari kata 'Level' + romawi/angka dalam teks.
    Jika semua gagal -> None (sistem tetap jalan tanpa ground-truth ini).
    """
    candidates = [
        "https://magma.esdm.go.id/v1/gunung-api/laporan-terbaru?code=KRA",
        "https://magma.esdm.go.id/v1/gunung-api",
    ]
    for url in candidates:
        try:
            r = requests.get(url, headers=_HEADERS, timeout=30)
        except requests.RequestException:
            continue
        if r.status_code != 200:
            continue
        text = r.text.lower()
        if "krakatau" not in text:
            continue
        # cari "level iii", "level 3", "siaga"
        m = re.search(r"level\s+(iv|iii|ii|i|[1-4])", text)
        if m:
            token = m.group(1)
            roman = {"i": 1, "ii": 2, "iii": 3, "iv": 4}
            return roman.get(token, int(token) if token.isdigit() else None)
        for word, lvl in _LEVEL_MAP.items():
            if word in text:
                return lvl
    return None


if __name__ == "__main__":
    print("Level status MAGMA:", get_alert_level())
