"""Dataset replay engine (CONTRACT.md Section 9).

Replays the SWaT attack.csv segment containing the LOCKED demo window
(2015-12-28 11:22:00 -> 11:28:22, dense 1 Hz segment #3) at a fixed playback
multiplier. Wall-clock position is derived from elapsed time since start, so
there is no per-tick drift.

Defaults: locked timestamp 2015-12-28 11:22:00 at 30x. A multiplier override
on /api/replay/start is an explicit, flagged rehearsal adjustment per
build-prompt Section 9 step 2 ("adjust the multiplier, not the script") — the
default stays locked at 30x.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import timedelta

import pandas as pd

from app.ai.threshold_derivation import (
    DEMO_SEGMENT_END,
    LOCKED_DEMO_WINDOW,
)
from app.ingestion.data_loader import load_default_dataset
from app.models.graph_schema import NODES


@dataclass
class ReplayState:
    running: bool = False
    started_at: float | None = None          # time.monotonic() at start
    position: int = 0                        # current row index in the segment
    multiplier: int = 30
    interval: float = 2.0                    # seconds between appended rows
    finished: bool = False


@dataclass
class Snapshot:
    position: int
    timestamp: pd.Timestamp
    row: pd.Series
    history: pd.DataFrame                    # recent rows per tag (row-major)


class DatasetReplay:
    """Streams rows from the locked demo segment of attack.csv."""

    def __init__(self, multiplier: int = 30):
        ds = load_default_dataset()
        self.df: pd.DataFrame = ds.df
        lo = self.df.index.searchsorted(pd.Timestamp(LOCKED_DEMO_WINDOW))
        hi = self.df.index.searchsorted(pd.Timestamp(DEMO_SEGMENT_END)) + 1
        self.segment = self.df.iloc[lo:hi]
        self.node_tag_map = {n["id"]: n["tags"] for n in NODES}
        self.lock = threading.Lock()
        self.state = ReplayState(multiplier=multiplier)

    # ---- control ----

    def start(self, multiplier: int | None = None) -> dict:
        with self.lock:
            if self.state.running:
                return self.status()
            if multiplier is not None:
                self.state.multiplier = int(multiplier)
            self.state.running = True
            self.state.started_at = time.monotonic()
            self.state.finished = False
            # position persists across stop/start so start() can resume
            return self.status()

    def stop(self) -> dict:
        with self.lock:
            self.state.running = False
            return self.status()

    def reset(self) -> None:
        with self.lock:
            self.state.running = False
            self.state.position = 0
            self.state.started_at = None
            self.state.finished = False

    @property
    def segment_length(self) -> int:
        return len(self.segment)

    # ---- engine tick (called by the API layer's background loop) ----

    def tick(self) -> Snapshot | None:
        """Advance to wall-clock position and return the latest snapshot."""
        st = self.state
        if not st.running or st.started_at is None:
            return None
        elapsed = time.monotonic() - st.started_at
        target = int(elapsed * st.multiplier) + 1
        if target <= st.position:
            return None
        if target >= self.segment_length:
            target = self.segment_length
        with self.lock:
            st.position = target
            if st.position >= self.segment_length:
                st.running = False
                st.finished = True
        return self._snapshot()

    def _snapshot(self) -> Snapshot:
        st = self.state
        pos = max(st.position, 1)
        row = self.segment.iloc[pos - 1]
        window = min(pos, 120)
        return Snapshot(
            position=pos - 1,
            timestamp=row.name,
            row=row,
            history=self.segment.iloc[pos - window:pos],
        )

    def latest(self) -> Snapshot | None:
        if self.state.position == 0:
            return None
        return self._snapshot()

    def status(self) -> dict:
        st = self.state
        pos = max(st.position - 1, 0)
        ts = (self.segment.index[pos] if st.position > 0
              else self.segment.index[0])
        return {
            "running": st.running,
            "position": pos,
            "total_rows": self.segment_length,
            "timestamp": str(ts),
            "multiplier": st.multiplier,
            "finished": st.finished,
            "locked_start": LOCKED_DEMO_WINDOW,
            "locked_multiplier": 30,
        }
