"""Ambil level status Anak Krakatau dari MAGMA Indonesia (best-effort, konservatif).

Scraping halaman publik itu rapuh. Prinsip: hanya kembalikan sebuah level jika kata
"krakatau" dan token level yang jelas ("siaga"/"awas"/"level iii" dst.) muncul
BERDEKATAN. Kalau ragu -> None, dan sistem jalan tanpa sinyal ini.
"""
from __future__ import annotations

import re

import requests

_HEADERS = {"User-Agent": "krakatau-monitor/1.0"}
_CANDIDATES = (
    "https://magma.esdm.go.id/v1/gunung-api/laporan-terbaru?code=KRA",
    "https://magma.esdm.go.id/v1/gunung-api",
)
_WORD_LEVEL = {"normal": 1, "waspada": 2, "siaga": 3, "awas": 4}
_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4}

# "krakatau" ... (maks 300 karakter) ... token level
_CONTEXT = re.compile(
    r"krakatau.{0,300}?(?:tingkat\s+aktivitas\s+)?"
    r"(level\s+(iv|iii|ii|i)\b|normal|waspada|siaga|awas)",
    re.IGNORECASE | re.DOTALL,
)


def _parse(text: str) -> int | None:
    m = _CONTEXT.search(text)
    if not m:
        return None
    token = m.group(1).lower().strip()
    if token.startswith("level"):
        return _ROMAN.get(m.group(2).lower())
    return _WORD_LEVEL.get(token)


def get_alert_level() -> int | None:
    for url in _CANDIDATES:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=30)
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        level = _parse(resp.text)
        if level is not None:
            return level
    return None


if __name__ == "__main__":
    print("Level status Anak Krakatau (MAGMA):", get_alert_level())
