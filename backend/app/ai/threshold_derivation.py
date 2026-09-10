"""Offline threshold + demo-window derivation (build prompt Section 5.2).

Produces backend/app/ai/derived_thresholds.json, the committed artifact the
live pipeline loads. Two layers are computed and both are disclosed:

1. Section 5.2 artifacts (as specified):
   - Proxy baseline from the lowest-variance 10% of 5-minute windows over
     continuous tags only (8 near-zero-variance actuator columns excluded,
     pinned/flatlined windows rejected).
   - Global Isolation Forest over the full time series + firing timestamps.
2. Demo operational baselines (deliberate, disclosed deviation):
   - Verified finding: attack.csv is an all-Attack export split into 35 dense
     segments; NO window exists where all six demo nodes sit at the file-wide
     baselines (N6 FIT601 and N3 LIT301 are off-baseline for most of the
     file). A "healthy opening state" therefore cannot come from file-wide
     quiet windows. Per Section 5.2 step 7 (semi-synthetic fallback), the
     live demo uses operational baselines captured from the first 60 seconds
     of the locked demo window (real, steady, pre-attack readings), with
     sigma floored by drift so a steady ramp is not misread as failure.

Locked demo window: 2015-12-28 11:22:00 (segment #3, the real SWaT
LIT301/MV301 attack: FIT301 2.21 -> 0.00 at 11:23:30, DPIT301 19.8 -> 2.0,
LIT301 departs level). Downstream N4-N6 propagation during the demo is the
propagation model's predicted trajectory, flagged synthetic:true end to end.

Run once:  py -m app.ai.threshold_derivation
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.ingestion.data_loader import load_default_dataset
from app.models.graph_schema import (
    ALL_CONTINUOUS_TAGS,
    CONTINUOUS_TAGS_BY_NODE,
    EXCLUDED_ACTUATOR_COLUMNS,
    NODES,
    TAG_TO_NODE,
)

SECONDS_PER_ROW = 1
WINDOW_ROWS = 5 * 60 // SECONDS_PER_ROW      # 5-minute windows
LOW_VARIANCE_FRACTION = 0.10
CONTAMINATION = 0.05
PCT_WARN, PCT_FAIL = 97.5, 99.0

# ---- Locked demo window (verified manually across all 35 segments) ----
LOCKED_DEMO_WINDOW = "2015-12-28 11:22:00"
DEMO_SEGMENT_END = "2015-12-28 11:28:22"     # end of dense segment #3
TRUTH_ONSET = "2015-12-28 11:23:15"          # verified attack-effect onset
                                             # (DPIT301 collapse, FIT301 cut
                                             # at 11:23:30)
BASELINE_CAPTURE_SECONDS = 60                # opening steady-state capture
DRIFT_SIGMA_SECONDS = 60                     # slope allowance horizon
SUSTAIN_SECONDS = 5                          # deviation must persist this long


def _is_pinned_flat(values: np.ndarray) -> bool:
    lo, hi = values.min(), values.max()
    if hi == lo:
        return True
    return (np.mean(values == lo) > 0.98) or (np.mean(values == hi) > 0.98)


def derive_quiet_baselines(df: pd.DataFrame) -> dict:
    """Section 5.2 steps 1-3: file-wide proxy baselines (primary artifact)."""
    stats: dict[str, dict] = {}
    for tag in ALL_CONTINUOUS_TAGS:
        if tag not in df.columns:
            continue
        series = df[tag].to_numpy(dtype=np.float32)
        n = len(series)
        if n <= WINDOW_ROWS:
            continue
        stride = 60
        stds, means = [], []
        for start in range(0, n - WINDOW_ROWS, stride):
            w = series[start:start + WINDOW_ROWS]
            if float(np.std(w)) == 0.0 or _is_pinned_flat(w):
                continue
            stds.append(float(np.std(w)))
            means.append(float(np.mean(w)))
        if not stds:
            continue
        stds_a, means_a = np.array(stds), np.array(means)
        keep = stds_a <= np.quantile(stds_a, LOW_VARIANCE_FRACTION)
        mu, sd = float(np.mean(means_a[keep])), float(np.mean(stds_a[keep]))
        stats[tag] = {
            "baseline_mean": round(mu, 4),
            "baseline_std": round(sd, 4),
            "threshold_warning": round(mu + 2 * sd, 4),
            "threshold_failure": round(mu + 4 * sd, 4),
        }
    return stats


def train_isolation_forest(df: pd.DataFrame):
    cols = [t for t in ALL_CONTINUOUS_TAGS if t in df.columns]
    X = df[cols].to_numpy(dtype=np.float32)
    model = IsolationForest(n_estimators=200, contamination=CONTAMINATION,
                            random_state=42, n_jobs=-1)
    model.fit(X)
    raw = -model.decision_function(X)  # higher = more anomalous
    scores = (raw - raw.min()) / (raw.max() - raw.min() + 1e-12)
    norm = (float(raw.min()), float(raw.max()))
    return scores, norm, float(np.percentile(scores, PCT_WARN)), float(np.percentile(scores, PCT_FAIL))


def derive_operational_baselines(df: pd.DataFrame, start_ts: str) -> dict:
    """Per-tag operational baseline from the locked window's opening minute."""
    start = df.index.searchsorted(pd.Timestamp(start_ts))
    out: dict[str, dict] = {}
    for node in NODES:
        for tag in node["tags"]:
            if tag not in df.columns:
                continue
            seg = df[tag].iloc[start:start + BASELINE_CAPTURE_SECONDS] \
                .to_numpy(dtype=np.float64)
            if len(seg) < 20:
                continue
            mu = float(np.mean(seg))
            sd = float(np.std(seg))
            # drift allowance: a steady ramp at the window start is normal
            # operation (e.g. LIT101 filling), not an emerging failure.
            t = np.arange(len(seg), dtype=np.float64)
            slope = float(np.polyfit(t, seg, 1)[0]) if len(seg) > 2 else 0.0
            # quantization resolution: near-zero tags (e.g. FIT601 ~1e-4)
            # quantize coarsely relative to their mean; floor sigma at half
            # the smallest observed step so one count != instant failure.
            calib = df[tag].iloc[start:start + 300].to_numpy(dtype=np.float64)
            diffs = np.abs(np.diff(calib))
            diffs = diffs[diffs > 0]
            resolution = float(diffs.min()) if len(diffs) else 0.0
            sd_eff = max(sd, 0.01 * abs(mu), abs(slope) * DRIFT_SIGMA_SECONDS,
                         0.5 * resolution, 1e-9)
            out[tag] = {
                "node_id": node["id"],
                "mean": round(mu, 4),
                "sigma": round(sd_eff, 8),
                "raw_std": round(sd, 8),
                "slope_per_s": round(slope, 5),
                "warn_sigma": 2.0,
                "fail_sigma": 4.0,
                "sustain_seconds": SUSTAIN_SECONDS,
            }
    return out


def compute_validation_metrics(df: pd.DataFrame,
                               operational: dict) -> dict:
    """Scoped precision/recall for the demonstrated subsystem (Section 7).

    Scope: N3 continuous tags inside the locked demo segment. Ground truth is
    the manually verified attack-effect interval (Section 5.2 step 6
    inspection): DPIT301 collapse from 11:23:15, FIT301 cut to 0.00 at
    11:23:30, LIT301 level departure. Prediction is the same sustained
    sigma-threshold detector used live (2-sigma for 5 consecutive seconds).
    """
    n3_tags = [t for t in CONTINUOUS_TAGS_BY_NODE["N3"] if t in operational]
    lo = df.index.searchsorted(pd.Timestamp(LOCKED_DEMO_WINDOW))
    hi = df.index.searchsorted(pd.Timestamp(DEMO_SEGMENT_END)) + 1
    truth_lo = df.index.searchsorted(pd.Timestamp(TRUTH_ONSET))

    sustained = SUSTAIN_SECONDS
    pred = np.zeros(hi - lo, dtype=bool)
    for tag in n3_tags:
        b = operational[tag]
        dev = np.abs(df[tag].iloc[lo:hi].to_numpy(dtype=np.float64) - b["mean"])
        over = dev > b["warn_sigma"] * b["sigma"]
        # sustained: running sum over the last `sustained` rows
        run = np.convolve(over.astype(int),
                          np.ones(sustained, dtype=int),
                          mode="full")[: len(over)]
        pred |= run >= sustained

    truth = np.arange(lo, hi) >= truth_lo
    tp = int(np.sum(pred & truth))
    fp = int(np.sum(pred & ~truth))
    fn = int(np.sum(~pred & truth))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "scope": "Model accuracy shown for the demonstrated subsystem "
                 "(Stage 3 sensors, locked demo window 2015-12-28 11:22-11:28)",
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "tp": tp, "fp": fp, "fn": fn,
        "truth_interval": [TRUTH_ONSET, DEMO_SEGMENT_END],
        "truth_basis": "manually verified attack-effect onset (Section 5.2 "
                       "step 6): DPIT301 collapse + FIT301 flow cut",
        "full_dataset_available": True,
        "full_dataset_note": "attack.csv has no Normal labels; the full-file "
                             "fact below is the Isolation Forest firing rate "
                             "(2.5% of rows), not precision/recall. Available "
                             "on request.",
    }


def main() -> None:
    print("Loading attack.csv ...")
    ds = load_default_dataset()
    df = ds.df
    print(f"Rows: {len(df)}  tags: {len(df.columns)}  labels: {ds.label_values}")

    print("Deriving Section 5.2 proxy baselines ...")
    quiet = derive_quiet_baselines(df)
    print(f"  quiet-window baselines for {len(quiet)} tags")

    print("Training Isolation Forest ...")
    scores, if_norm, warn_cut, fail_cut = train_isolation_forest(df)
    fired = int((scores >= warn_cut).sum())
    print(f"  IF fired on {fired}/{len(scores)} rows "
          f"({100 * fired / len(scores):.1f}%)")

    print(f"Deriving operational baselines from locked window "
          f"{LOCKED_DEMO_WINDOW} (first {BASELINE_CAPTURE_SECONDS}s) ...")
    operational = derive_operational_baselines(df, LOCKED_DEMO_WINDOW)
    print(f"  operational baselines for {len(operational)} tags")

    print("Computing scoped validation metrics (Section 7) ...")
    validation = compute_validation_metrics(df, operational)
    print(f"  precision={validation['precision']} "
          f"recall={validation['recall']} "
          f"(tp={validation['tp']} fp={validation['fp']} fn={validation['fn']})")

    print("Persisting Isolation Forest model ...")
    import joblib
    cols = [t for t in ALL_CONTINUOUS_TAGS if t in df.columns]
    model = IsolationForest(n_estimators=200, contamination=CONTAMINATION,
                            random_state=42, n_jobs=-1)
    model.fit(df[cols].to_numpy(dtype=np.float32))
    model_path = Path(__file__).resolve().parent / "if_model.joblib"
    joblib.dump(model, model_path)
    print(f"  wrote {model_path}")

    out = {
        "source_dataset": ds.source_name,
        "rows": len(df),
        "excluded_actuator_columns": EXCLUDED_ACTUATOR_COLUMNS,
        "locked_demo_window": LOCKED_DEMO_WINDOW,
        "replay_multiplier": 30,
        "method": {
            "quiet_baseline": "lowest-variance 10% of 5-minute rolling "
                              "windows over continuous tags; pinned/flatlined "
                              "windows rejected (Section 5.2 steps 1-3)",
            "anomaly_model": f"IsolationForest(contamination={CONTAMINATION}, "
                             "n_estimators=200) over all continuous tags; "
                             "min-max normalized score",
            "if_cutpoints": f"warning >= P{PCT_WARN}, failure >= P{PCT_FAIL} "
                            "of the normalized score (fixed, consistent)",
            "operational_baseline": "per-tag mean/std/slope from the first 60s "
                                    "of the locked demo window; sigma_eff = "
                                    "max(std, 1%|mean|, |slope|*60s); warning "
                                    "> 2 sigma, failure > 4 sigma, sustained "
                                    "5s (disclosed semi-synthetic fallback, "
                                    "Section 5.2 step 7)",
            "honesty_note": "attack.csv has no Normal rows (all 54,621 labeled "
                            "Attack) and no all-healthy window exists in the "
                            "file; operational baselines make the demo's "
                            "healthy opening state real data, and downstream "
                            "N4-N6 propagation is the model's prediction "
                            "(synthetic:true), not raw sensor coincidence",
        },
        "if_score_warning_cutpoint": round(warn_cut, 6),
        "if_score_failure_cutpoint": round(fail_cut, 6),
        "if_score_norm": [round(if_norm[0], 6), round(if_norm[1], 6)],
        "if_fired_rows": fired,
        "if_feature_columns": cols,
        "validation": validation,
        "quiet_baselines": quiet,
        "operational_baselines": operational,
        "node_tag_map": {n["id"]: n["tags"] for n in NODES},
        "tag_node_map": TAG_TO_NODE,
    }
    out_path = Path(__file__).resolve().parent / "derived_thresholds.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
