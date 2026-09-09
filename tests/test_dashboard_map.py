"""Uji dashboard.hotspot_map_html."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard import hotspot_map_html  # noqa: E402


def test_empty_returns_blank():
    assert hotspot_map_html(pd.DataFrame(columns=["latitude", "longitude", "frp", "ts"])) == ""


def test_far_only_points_return_blank():
    df = pd.DataFrame({
        "latitude": [-6.5], "longitude": [106.0], "frp": [10.0],
        "bright_ti4": [340.0], "ts": ["2026-09-07 01:11"],
    })
    assert hotspot_map_html(df) == ""


def test_near_points_produce_map_with_leaflet_and_data():
    df = pd.DataFrame({
        "latitude": [-6.102, -6.104, -6.100],
        "longitude": [105.423, 105.425, 105.421],
        "frp": [12.0, 3.5, 40.0],
        "bright_ti4": [340.0, 320.0, 367.0],
        "ts": ["2026-09-05 01:16", "2026-09-06 13:22", "2026-09-07 01:11"],
    })
    html = hotspot_map_html(df)
    assert "leaflet" in html.lower()
    assert 'id="hsmap"' in html
    assert '"frp":40.0' in html or '"frp": 40.0' in html
    assert "n=3" in html
