"""Live anomaly detection per sensor binding (build prompt v4 Section 7.1).

Two components, both disclosed (honesty standard carried over from v3):

1. User-set thresholds — cold-start fallback (Section 12.4: warning =
   baseline x 1.2, failure = x 1.5, set at binding creation). A value
   sustained over the trailing SUSTAIN_SAMPLES readings crosses into
   warning/failed. Method label: "user thresholds".
2. Isolation Forest — trained LIVE per binding on the values observed so
   far (MIN_TRAIN_SAMPLES minimum), refit as data accumulates. Cutpoints
   are data-derived, not invented: warning = 99th percentile of the
   binding's own training-score distribution; failure = beyond the
   historical maximum (normalized score >= 1.0). Until calibrated, the
   binding reports warm_up=true and only the threshold detector drives
   status — this is the UI-disclosed warm-up period (Section 7.1).

Sustain rule (deviation must persist 5 consecutive samples) is carried
over from v3's engine. States recover when values return to normal — v4
is a live system, not a scripted replay, so states are re-derived from
the trailing window on every evaluation instead of latched.
"""

from __future__ import annotations

import threading

import numpy as np
from sklearn.ensemble import IsolationForest

MIN_TRAIN_SAMPLES = 30
REFIT_EVERY_NEW_SAMPLES = 10
SUSTAIN_SAMPLES = 5          # carried over from v3 (5 consecutive samples)
TRAIN_WINDOW = 200           # trailing readings used for training

_METHOD_THRESHOLD = ("user-set thresholds (cold-start defaults: warning = "
                     "baseline x1.2, failure = x1.5)")
_METHOD_IF = ("trained Isolation Forest (scikit-learn), trained live on "
              "this binding's observed values")

_lock = threading.Lock()
# binding_id -> {"n_fitted", "model", "score_lo", "score_span", "warn_cut"}
_if_cache: dict[int, dict] = {}


def clear_binding(binding_id: int) -> None:
    with _lock:
        _if_cache.pop(binding_id, None)


def _normalized_train_scores(model: IsolationForest, X: np.ndarray):
    raw = -model.decision_function(X)
    lo = float(raw.min())
    span = float(raw.max() - raw.min()) or 1.0
    return (raw - lo) / span, lo, span


def _maybe_refit(binding_id: int, values: list[float]) -> dict | None:
    """Fit/refit the binding's Isolation Forest; None until calibrated."""
    n = len(values)
    if n < MIN_TRAIN_SAMPLES:
        return None
    cached = _if_cache.get(binding_id)
    if cached is not None and (n - cached["n_fitted"]) < REFIT_EVERY_NEW_SAMPLES:
        return cached
    with _lock:
        # re-check inside the lock (another thread may have refit)
        cached = _if_cache.get(binding_id)
        if cached is not None and (n - cached["n_fitted"]) < REFIT_EVERY_NEW_SAMPLES:
            return cached
        X = np.asarray(values[-TRAIN_WINDOW:], dtype=np.float64).reshape(-1, 1)
        model = IsolationForest(n_estimators=100, random_state=0)
        model.fit(X)
        train_norm, lo, span = _normalized_train_scores(model, X)
        entry = {
            "n_fitted": n,
            "model": model,
            "score_lo": lo,
            "score_span": span,
            # data-derived cutpoints: P99 of this binding's own training
            # scores warns; beyond the historical maximum fails (>= 1.0
            # after normalization by construction).
            "warn_cut": float(np.percentile(train_norm, 99)),
        }
        _if_cache[binding_id] = entry
        return entry


def _if_score(entry: dict, value: float) -> float:
    """Normalized IF anomaly score for one value (can exceed 1.0)."""
    raw = -entry["model"].decision_function(
        np.array([[value]], dtype=np.float64))[0]
    return float((raw - entry["score_lo"]) / entry["score_span"])


def _threshold_state(values: list[float], warning: float | None,
                     failure: float | None) -> str:
    if not values:
        return "healthy"

    def sustained(level: float) -> bool:
        tail = values[-SUSTAIN_SAMPLES:]
        return len(tail) >= SUSTAIN_SAMPLES and all(v >= level for v in tail)

    if failure is not None and sustained(failure):
        return "failed"
    if warning is not None and sustained(warning):
        return "warning"
    return "healthy"


def _threshold_score(value: float, warning: float | None,
                     failure: float | None) -> float:
    """Normalized exceedance of the locked thresholds, 0-1.

    Derived from the user's thresholds only — 1.0 at the failure threshold.
    At the cold-start defaults (warn = 1.2x, fail = 1.5x baseline) a
    warning value scores ~0.8.
    """
    ref = failure if failure else warning
    if not ref or ref <= 0:
        return 0.0
    return min(max(value / ref, 0.0), 1.0)


def detect_binding_state(binding: dict, values: list[float]) -> dict:
    """Full detection result for one sensor binding's trailing values."""
    warning = binding["warning_threshold"]
    failure = binding["failure_threshold"]
    result: dict = {
        "binding_id": binding["id"],
        "state": "healthy",
        "threshold_state": "healthy",
        "if_state": None,
        "if_score": None,
        "if_cutpoints": None,
        "anomaly_score": 0.0,
        "calibrated": False,
        "warm_up": True,
        "samples": len(values),
        "method": _METHOD_THRESHOLD,
        "warning_threshold": warning,
        "failure_threshold": failure,
    }
    if not values:
        return result

    thr_state = _threshold_state(values, warning, failure)
    thr_score = _threshold_score(values[-1], warning, failure)

    entry = _maybe_refit(binding["id"], values)
    if_state = None
    if_score = None
    if entry is not None:
        norm = _if_score(entry, values[-1])
        if_score = round(min(norm, 1.0), 4)
        if norm >= 1.0:
            if_state = "failed"
        elif norm >= entry["warn_cut"]:
            if_state = "warning"
        else:
            if_state = "healthy"

    order = {"healthy": 0, "warning": 1, "failed": 2}
    state = thr_state
    if if_state is not None and order[if_state] > order[state]:
        state = if_state

    result.update({
        "state": state,
        "threshold_state": thr_state,
        "if_state": if_state,
        "if_score": if_score,
        "anomaly_score": round(max(thr_score, if_score or 0.0), 4),
        "calibrated": entry is not None,
        "warm_up": entry is None,
        "method": _METHOD_IF if entry is not None else _METHOD_THRESHOLD,
        "if_cutpoints": ({"warning": round(entry["warn_cut"], 4),
                          "failure": 1.0} if entry is not None else None),
    })
    return result
