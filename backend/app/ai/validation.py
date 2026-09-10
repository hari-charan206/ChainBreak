"""Validation metrics serving (CONTRACT.md Section 12).

Numbers are computed ONCE in threshold_derivation.py against the locked demo
window and served from the derived artifact — the scope label always travels
with the number, and the full-dataset fact stays available on request.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ai.anomaly_detection import DERIVED


def validation_metrics() -> dict:
    v = DERIVED["validation"]
    return {
        "scope": v["scope"],
        "precision": v["precision"],
        "recall": v["recall"],
        "tp": v.get("tp"),
        "fp": v.get("fp"),
        "fn": v.get("fn"),
        "truth_interval": v.get("truth_interval"),
        "truth_basis": v.get("truth_basis"),
        "method": "sustained sigma-threshold detector (2-sigma, 5s), "
                  "evaluated on manually verified attack-effect interval",
        "full_dataset_available": v.get("full_dataset_available", True),
        "full_dataset_note": v.get("full_dataset_note"),
        "if_fired_rows": DERIVED.get("if_fired_rows"),
        "if_rows_total": DERIVED.get("rows"),
    }


def full_dataset_metrics() -> dict:
    """Secondary fact for judges who ask (never the headline)."""
    v = DERIVED["validation"]
    return {
        "scope": "Full attack.csv file (54,621 rows, all labeled Attack — "
                 "no Normal labels exist, so precision/recall is not "
                 "computable on the full file)",
        "if_fired_rows": DERIVED.get("if_fired_rows"),
        "if_rows_total": DERIVED.get("rows"),
        "if_firing_rate": round(DERIVED.get("if_fired_rows", 0)
                                / max(DERIVED.get("rows", 1), 1), 4),
        "note": v.get("full_dataset_note"),
    }
