"""Orkestrator pemantau Anak Krakatau: tarik data -> metrik -> status -> notifikasi -> dashboard.

Aman dijalankan berulang (idempoten). Panggil sekali per hari via Task Scheduler / cron / CI.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd

import dashboard
import notify
from config import STATE_JSON
from fetch_magma import get_alert_level
from fetch_so2 import update_so2_csv
from fetch_thermal import update_thermal_csv
from metrics import compute_metrics
from state_machine import data_gap_alert, next_state


def _load_state() -> dict:
    if STATE_JSON.exists():
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    return {"state": "NORMAL", "since": None, "last_magma_level": None,
            "last_gap_notified": None, "history": []}


def _save_state(state: dict) -> None:
    STATE_JSON.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    print(f"=== Pemantau Anak Krakatau — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} ===")
    prev = _load_state()

    thermal = update_thermal_csv()
    so2 = update_so2_csv()
    if thermal.empty:
        print("  ! tidak ada data termal sama sekali — berhenti.")
        return
    if so2.empty:  # SO2 opsional; isi minimal agar metrik jalan
        so2 = pd.DataFrame({"date": thermal["date"], "so2_max_du": 0.0,
                            "so2_mean_du": 0.0, "so2_15_du": 0.0})

    magma_level = get_alert_level()
    prev_level = prev.get("last_magma_level")
    magma_escalated = (magma_level is not None and prev_level is not None
                       and magma_level > prev_level)
    print(f"  MAGMA level: {magma_level} (sebelumnya {prev_level})")

    m = compute_metrics(thermal, so2)
    new_state, reason, changed = next_state(prev["state"], m, magma_escalated)
    print(f"  status: {prev['state']} -> {new_state}  ({reason})")

    # --- notifikasi ---
    if changed:
        notify.send(new_state, reason, m.as_dict())
    if data_gap_alert(m):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if prev.get("last_gap_notified") != today:
            notify.send("GAP", f"data satelit tertinggal {m.data_age_days} hari — "
                               f"status ({new_state}) mungkin usang", m.as_dict())
            prev["last_gap_notified"] = today

    # --- dashboard ---
    dashboard.render(new_state, reason, m.as_dict(), thermal, so2)

    # --- simpan state ---
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = {"run": now_iso, "state": new_state, "reason": reason, **m.as_dict()}
    prev["history"] = (prev.get("history", []) + [entry])[-400:]
    prev["state"] = new_state
    prev["since"] = now_iso if changed else prev.get("since")
    prev["last_magma_level"] = magma_level if magma_level is not None else prev_level
    _save_state(prev)
    print("  state.json disimpan.")


if __name__ == "__main__":
    main()
