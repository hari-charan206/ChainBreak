"""Anomaly detection + node state evaluation.

Two components, both disclosed (CONTRACT.md Section 10):

1. Isolation Forest (trained, persisted): global per-row anomaly score for the
   replay row. Metadata carries method="isolation_forest".
2. Operational sigma detector: per-tag deviation vs the demo-window
   operational baseline (2-sigma sustained = warning, 4-sigma = failure).
   Drives node status. Method metadata carries "sigma_threshold".

Sustain filtering (a deviation must persist 5 consecutive seconds) is applied
by the cascade engine, which feeds confirmed per-tag states back in.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ingestion.dataset_replay import Snapshot
from app.models.graph_schema import (
    NODE_STATUSES,
    NODES,
    is_status_tag,
)

_DERIVED_PATH = Path(__file__).resolve().parent / "derived_thresholds.json"
_MODEL_PATH = Path(__file__).resolve().parent / "if_model.joblib"

with open(_DERIVED_PATH) as fh:
    DERIVED = json.load(fh)

IF_MODEL = joblib.load(_MODEL_PATH)
IF_COLUMNS = DERIVED["if_feature_columns"]
IF_WARN_CUT = DERIVED["if_score_warning_cutpoint"]
IF_FAIL_CUT = DERIVED["if_score_failure_cutpoint"]
IF_NORM_LO, IF_NORM_HI = DERIVED["if_score_norm"]
OPERATIONAL = DERIVED["operational_baselines"]
METHOD_LABELS = {
    "anomaly": "trained Isolation Forest (scikit-learn)",
    "sigma": "operational sigma thresholds vs demo-window baseline",
}


def if_score_for_row(row: pd.Series) -> float:
    """Normalized Isolation Forest anomaly score for one replay row."""
    x = np.array([[float(row[c]) for c in IF_COLUMNS]], dtype=np.float32)
    raw = -IF_MODEL.decision_function(x)[0]
    span = (IF_NORM_HI - IF_NORM_LO) or 1.0
    return float(min(max((raw - IF_NORM_LO) / span, 0.0), 1.0))


def if_state_for_score(score: float) -> str:
    if score >= IF_FAIL_CUT:
        return "failed"
    if score >= IF_WARN_CUT:
        return "warning"
    return "healthy"


def instantaneous_tag_states(snapshot: Snapshot) -> dict:
    """Raw (unsustained) per-tag deviation state for the current row."""
    out = {}
    for node in NODES:
        for tag in node["tags"]:
            if tag not in OPERATIONAL or tag not in snapshot.row.index:
                continue
            b = OPERATIONAL[tag]
            value = float(snapshot.row[tag])
            sigma = abs(value - b["mean"]) / max(b["sigma"], 1e-9)
            if is_status_tag(tag):
                # actuator/state changes are displayed, never drive status
                state = "healthy"
            elif sigma > b["fail_sigma"]:
                state = "failed"
            elif sigma > b["warn_sigma"]:
                state = "warning"
            else:
                state = "healthy"
            out[tag] = {"node_id": node["id"], "state": state,
                        "deviation_sigma": round(float(sigma), 3),
                        "value": value,
                        "kind": "status" if is_status_tag(tag) else "sensor"}
    return out


def evaluate_nodes(snapshot: Snapshot, confirmed: dict[str, str],
                   if_score: float) -> dict:
    """Per-node status/score using confirmed (sustained) tag states.

    `confirmed` maps tag -> "healthy" | "warning" | "failed", sustained over
    the last SUSTAIN seconds by the cascade engine.
    """
    result = {}
    inst = instantaneous_tag_states(snapshot)
    for node in NODES:
        node_id = node["id"]
        tag_states = {}
        worst = "healthy"
        dev_max = 0.0
        for tag in node["tags"]:
            info = inst.get(tag)
            if info is None:
                continue
            state = confirmed.get(tag, "healthy")
            tag_states[tag] = {
                "state": state,
                "deviation_sigma": info["deviation_sigma"],
                "value": info["value"],
            }
            dev_max = max(dev_max, info["deviation_sigma"])
            if NODE_STATUSES.index(state) > NODE_STATUSES.index(worst):
                worst = state

        anomaly_score = round(min(dev_max / 4.0, 1.0), 3)
        result[node_id] = {
            "node_id": node_id,
            "status": worst,
            "anomaly_score": anomaly_score,
            "if_score": round(if_score, 4),
            "if_state": if_state_for_score(if_score),
            "method": METHOD_LABELS["sigma"],
            "if_method": METHOD_LABELS["anomaly"],
            "tag_states": tag_states,
            "timestamp": str(snapshot.timestamp),
        }
    return result
