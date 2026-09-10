"""Cascade engine: sustains detections, runs propagation, tracks intervention.

Owns the demo narrative state machine:
  healthy -> warning (N3, real data) -> failure (N3, real data)
  -> real secondary effect on N4 (LIT401 departs pre-attack trend ~95s later)
  -> predicted propagation to N5/N6 (synthetic:true, disclosed)
  -> intervention applied -> replay frozen -> before/after computed.

At 30x replay and 2s polling, ~60 dataset rows elapse between polls, so
sustain detection runs over ALL dataset rows since the last evaluation
(vectorized) — identical logic to the offline validation detector
(2-sigma sustained 5 rows = warning, 4-sigma sustained 5 rows = failure).

From failure+105s onward N4/N5/N6 states beyond raw sensor coincidence come
from the propagation model, so cascade payloads carry synthetic:true and the
UI must disclose it (CONTRACT.md Sections 9/13).
"""

from __future__ import annotations

import threading
import time

import numpy as np

from app.ai.anomaly_detection import (
    OPERATIONAL,
    evaluate_nodes,
    if_score_for_row,
)
from app.ai.intervention_ranking import rank_interventions
from app.ai.propagation import propagate
from app.models.graph_schema import NODES, NODE_BY_ID

SUSTAIN = 5                  # dataset rows a deviation must persist
N4_DEPARTURE_LAG = 95        # measured: LIT401 departs trend 95s after N3 failure
TREND_SIGMA_MULTIPLE = 6.0   # N4 departure threshold vs pre-attack trend
N4_TREND_TAGS = ["LIT401", "FIT401", "AIT402"]
CATCHUP_MAX_ROWS = 900
_STATUS_ORDER = {"healthy": 0, "warning": 1, "failed": 2}


def _sustained_mask(dev: np.ndarray, sigma_mult: float) -> np.ndarray:
    """Rows where dev > sigma_mult*sigma has held for SUSTAIN rows."""
    over = (dev > sigma_mult).astype(int)
    kernel = np.ones(SUSTAIN, dtype=int)
    run = np.convolve(over, kernel, mode="full")[: len(over)]
    return run >= SUSTAIN


class CascadeEngine:
    def __init__(self, replay):
        self.replay = replay
        self.lock = threading.Lock()
        self.last_processed = -1                 # last replay row evaluated
        self.latched: dict[str, str] = {}        # worst sustained state per tag
        self.trend_ref: dict[str, list[float]] = {}
        self.n4_departure_at: int | None = None
        self.failure_at: int | None = None
        self.intervention_applied: str | None = None
        self.intervention_time: float | None = None
        self.freeze_position: int | None = None
        self.simulated: bool = False
        self._cached_pos: int | None = None
        self._cached_result = None

    # ---------- detection plumbing ----------

    _ORDER = {"healthy": 0, "warning": 1, "failed": 2}

    def _catch_up(self, snapshot) -> dict[str, str]:
        """Sustained per-tag states over all dataset rows since last poll.

        States are LATCHED per run: once a tag's deviation has been sustained
        (warning or failed), it holds that state until reset — a failure does
        not un-fail while the demo narrative continues, and short tail
        windows at the end of the segment cannot regress confirmed states.
        """
        lo = max(0, self.last_processed + 1)
        hi = snapshot.position + 1
        if hi - lo > CATCHUP_MAX_ROWS:          # safety cap on catch-up
            lo = hi - CATCHUP_MAX_ROWS
        seg = self.replay.segment.iloc[lo:hi]
        for tag, b in OPERATIONAL.items():
            if tag not in seg.columns or len(seg) == 0:
                continue
            sigma_eff = max(b["sigma"], 1e-6)
            values = seg[tag].to_numpy(dtype=np.float64)
            dev = np.abs(values - b["mean"]) / sigma_eff
            if _sustained_mask(dev, b["fail_sigma"]).any():
                new_state = "failed"
            elif _sustained_mask(dev, b["warn_sigma"]).any():
                new_state = "warning"
            else:
                continue  # no new confirmation; keep latched state
            if self._ORDER[new_state] > self._ORDER.get(
                    self.latched.get(tag, "healthy"), 0):
                self.latched[tag] = new_state
        return dict(self.latched)

    def _n4_trend_update(self, snapshot) -> None:
        """Capture the N4 pre-attack trend reference while things are calm."""
        if self.failure_at is not None or self.simulated:
            return
        for tag in N4_TREND_TAGS:
            if tag not in snapshot.row.index:
                continue
            series = snapshot.history[tag].to_numpy(dtype=np.float64)
            if len(series) >= 30:
                self.trend_ref[tag] = series[-30:].tolist()

    def _n4_departed(self, snapshot) -> bool:
        """True when N4's level/flow departs its pre-attack trajectory."""
        # measured real departure: LIT401 departs ~95s after the N3 failure
        if self.failure_at is not None \
                and snapshot.position - self.failure_at >= N4_DEPARTURE_LAG:
            return True
        if self.simulated:
            return True
        # early independent departure check vs captured trend
        if not self.trend_ref:
            return False
        for tag, ref in self.trend_ref.items():
            if tag not in snapshot.row.index or len(ref) < 2:
                continue
            sigma = max(OPERATIONAL[tag]["raw_std"], 1e-3)
            slope = (ref[-1] - ref[0]) / max(len(ref) - 1, 1)
            extrapolated = ref[-1] + slope
            if abs(snapshot.row[tag] - extrapolated) > TREND_SIGMA_MULTIPLE * sigma:
                return True
        return False

    # ---------- main evaluation ----------

    def evaluate(self, snapshot):
        """Full evaluation bundle for the current replay position.

        Memoized per position: several endpoints poll within the same tick,
        and re-running catch-up detection on a partial window would
        recompute different sustained states (flicker).
        """
        with self.lock:
            if snapshot.position == self._cached_pos \
                    and self._cached_result is not None:
                return self._cached_result

            sustained = self._catch_up(snapshot)
            self.last_processed = snapshot.position
            self._n4_trend_update(snapshot)

            # N3 failure: any N3 tag 4-sigma sustained (real data)
            n3_failed = any(sustained.get(t) == "failed"
                            for t in NODE_BY_ID["N3"]["tags"]
                            if t in OPERATIONAL)
            if n3_failed and self.failure_at is None:
                self.failure_at = snapshot.position

            # N4 real secondary departure
            n4_departed = self._n4_departed(snapshot)
            if n4_departed and self.n4_departure_at is None:
                self.n4_departure_at = snapshot.position

            evaluation = evaluate_nodes(snapshot, sustained,
                                        if_score_for_row(snapshot.row))

            # overlay confirmed narrative states (real where measured)
            if n3_failed:
                evaluation["N3"]["status"] = "failed"
                for t in NODE_BY_ID["N3"]["tags"]:
                    if t in evaluation["N3"]["tag_states"]:
                        evaluation["N3"]["tag_states"][t]["state"] = "failed"
            if n4_departed and evaluation["N4"]["status"] == "healthy":
                evaluation["N4"]["status"] = "warning"
                for t in N4_TREND_TAGS:
                    if t in evaluation["N4"]["tag_states"]:
                        evaluation["N4"]["tag_states"][t]["state"] = "warning"

            predicted = propagate(evaluation)
            ranked = rank_interventions(evaluation, predicted)
            self._cached_pos = snapshot.position
            self._cached_result = (evaluation, predicted, ranked,
                                   n3_failed, n4_departed)
            return self._cached_result

    # ---------- narrative helpers ----------

    def mark_simulated_failure(self) -> None:
        with self.lock:
            self.simulated = True
            if self.failure_at is None:
                snap = self.replay.latest()
                self.failure_at = snap.position if snap else 0
            self._cached_pos = None  # force re-evaluation

    def apply_intervention(self, node_id: str) -> None:
        with self.lock:
            self.intervention_applied = node_id
            self.intervention_time = time.monotonic()
            self.freeze_position = self.replay.state.position

    def reset(self) -> None:
        """Clear all narrative state (replay reset)."""
        with self.lock:
            self.last_processed = -1
            self.latched = {}
            self.trend_ref = {}
            self.n4_departure_at = None
            self.failure_at = None
            self.intervention_applied = None
            self.intervention_time = None
            self.freeze_position = None
            self.simulated = False
            self._cached_pos = None
            self._cached_result = None

    def intervention_state(self) -> dict:
        return {
            "applied": self.intervention_applied,
            "time": self.intervention_time,
            "freeze_position": self.freeze_position,
        }
