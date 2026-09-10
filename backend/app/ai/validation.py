"""Validation metrics serving (v3 Section 12 standard carried to v4).

There are no labeled ground-truth rows in v4 — data is live MQTT, and the
SWaT attack labels retired with dataset replay. The honest computable
analogue is detector agreement on this environment's live values:

  precision := of the windows the calibrated Isolation Forest flagged,
               the fraction where the user-threshold detector also fired
  recall    := of the windows the user-threshold detector fired,
               the fraction the calibrated Isolation Forest also flagged

The scope label ALWAYS travels with the numbers and states plainly that
this is cross-detector agreement on live values, not labeled-dataset
accuracy. During the disclosed warm-up (a binding with too few samples to
calibrate) the payload is null — no number is shown rather than a fake one.
"""

from __future__ import annotations

from app.ai.anomaly_detection import MIN_TRAIN_SAMPLES


def validation_metrics(detections: list[dict]) -> dict | None:
    """detections: per-binding results from anomaly_detection.detect_binding_state."""
    total = len(detections)
    if total == 0:
        return None
    if all(d["samples"] == 0 for d in detections):
        return None  # no live data at all yet -> nothing to validate

    calibrating = [d for d in detections if d["calibrated"]]
    if not calibrating:
        return {
            "precision": None,
            "recall": None,
            "scope_label": (
                "Warm-up: the Isolation Forest needs "
                f"{MIN_TRAIN_SAMPLES}+ live readings per sensor before its "
                "flags are calibrated — no metrics shown yet (disclosed "
                "per build prompt Section 7.1)."
            ),
            "warm_up": True,
            "bindings_tracked": total,
        }

    tp = sum(1 for d in calibrating
             if d["if_state"] in ("warning", "failed")
             and d["threshold_state"] in ("warning", "failed"))
    if_flagged = sum(1 for d in calibrating
                     if d["if_state"] in ("warning", "failed"))
    thr_fired = sum(1 for d in calibrating
                    if d["threshold_state"] in ("warning", "failed"))

    precision = round(tp / if_flagged, 4) if if_flagged else None
    recall = round(tp / thr_fired, 4) if thr_fired else None

    return {
        "precision": precision,
        "recall": recall,
        "scope_label": (
            "Detector agreement on this environment's live sensor values "
            "(Isolation Forest vs user-set thresholds) — NOT accuracy "
            "against labeled failures; no labeled ground truth exists in "
            "live-demo mode."
        ),
        "warm_up": False,
        "bindings_tracked": total,
        "bindings_calibrated": len(calibrating),
        "method": ("cross-detector agreement (trained Isolation Forest vs "
                   "sustained user-threshold detector)"),
    }
