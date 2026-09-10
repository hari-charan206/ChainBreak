"""ChainBreak backend — FastAPI app (CONTRACT.md Section 6 endpoints).

Run (from backend/):  .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.ai.anomaly_detection import OPERATIONAL
from app.ai.explanation import METHOD_LABELS, explain_recommendation
from app.ai.intervention_ranking import rank_interventions
from app.ai.propagation import ETA_CAP_SECONDS, HOP_LAG_SECONDS, reachable_downstream
from app.ai.validation import full_dataset_metrics, validation_metrics
from app.engine import (
    N4_DEPARTURE_LAG,
    N4_TREND_TAGS,
    CascadeEngine,
)
from app.ingestion.dataset_replay import DatasetReplay
from app.models.graph_schema import EDGES, NODE_BY_ID, NODES

REPLAY_POLL_SECONDS = 0.25

replay = DatasetReplay()
engine = CascadeEngine(replay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_replay_loop())
    yield
    task.cancel()


async def _replay_loop():
    """Background tick loop driving the replay engine."""
    while True:
        replay.tick()
        await asyncio.sleep(REPLAY_POLL_SECONDS)


app = FastAPI(title="ChainBreak API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReplayStartRequest(BaseModel):
    multiplier: int | None = None  # flagged rehearsal adjustment only


class InterventionApplyRequest(BaseModel):
    node_id: str


# ---------------- graph / sensors ----------------


@app.get("/api/graph")
def get_graph():
    snap = replay.latest()
    if snap is None:
        return {
            "nodes": [
                {"id": n["id"], "display_name": n["display_name"],
                 "status": "healthy", "border_style": "solid"}
                for n in NODES
            ],
            "edges": [
                {"from": e["from"], "to": e["to"],
                 "criticality": e["criticality"], "active_cascade": False}
                for e in EDGES
            ],
            "synthetic": False,
            "replay_running": False,
        }
    evaluation, predicted, ranked, n3_failed, n4_departed = engine.evaluate(snap)
    status_style = {"healthy": "solid", "warning": "dashed",
                    "failed": "thick", "offline": "dotted"}
    nodes = []
    for n in NODES:
        ev = evaluation[n["id"]]
        pred = predicted.get(n["id"])
        nodes.append({
            "id": n["id"],
            "display_name": n["display_name"],
            "status": ev["status"],
            "border_style": status_style[ev["status"]],
            "anomaly_score": ev["anomaly_score"],
            "at_risk": pred is not None,
            "predicted": pred is not None,
            "eta_seconds": pred.get("eta_seconds") if pred else None,
        })
    cascade = cascade_payload(evaluation, predicted, ranked, n3_failed,
                              n4_departed)
    edges = [
        {
            "from": e["from"],
            "to": e["to"],
            "criticality": e["criticality"],
            "active_cascade": f"{e['from']}->{e['to']}"
            in cascade["active_edges"],
        }
        for e in EDGES
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "synthetic": cascade["synthetic"],
        "replay_running": replay.state.running,
        "active_edges": cascade["active_edges"],
        "cascade_note": cascade["note"],
    }


@app.get("/api/sensors/{node_id}")
def get_sensors(node_id: str):
    node = NODE_BY_ID.get(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="unknown node_id")
    snap = replay.latest()
    tags_payload = {}
    for tag in node["tags"]:
        if tag not in replay.df.columns:
            continue
        entry = {"trend": [], "value": None, "unit": ""}
        if snap is not None and tag in snap.row.index:
            entry["value"] = round(float(snap.row[tag]), 4)
            entry["trend"] = [round(float(v), 4)
                              for v in snap.history[tag].tolist()]
        elif snap is None:
            # pre-replay: show the locked window's first 60s as preview trend
            preview = replay.segment.iloc[:60]
            if tag in preview.columns:
                entry["trend"] = [round(float(v), 4)
                                  for v in preview[tag].tolist()]
        tags_payload[tag] = entry
    return {
        "node_id": node_id,
        "tags": tags_payload,
        "timestamp": str(snap.timestamp) if snap is not None else None,
    }


# ---------------- replay ----------------


@app.get("/api/replay/state")
def replay_state():
    return replay.status()


@app.post("/api/replay/start")
def replay_start(req: ReplayStartRequest):
    if req.multiplier is not None and req.multiplier != 30:
        # permitted as flagged rehearsal adjustment (Section 9 step 2)
        pass
    replay.start(multiplier=req.multiplier)
    return replay.status()


@app.post("/api/replay/stop")
def replay_stop():
    return replay.stop()


@app.post("/api/replay/reset")
def replay_reset():
    replay.reset()
    engine.reset()
    return replay.status()


# ---------------- failure / anomaly / cascade ----------------


@app.post("/api/failure/simulate")
def failure_simulate():
    """Guaranteed-timing fallback (Section 9 step 5)."""
    if replay.latest() is None:
        raise HTTPException(status_code=409,
                            detail="start the replay before simulating failure")
    engine.mark_simulated_failure()
    return {"simulated": True, "state": replay.status()}


@app.get("/api/anomaly/status")
def anomaly_status():
    snap = replay.latest()
    if snap is None:
        return {"nodes": []}
    evaluation, predicted, ranked, n3_failed, n4_departed = engine.evaluate(snap)
    out = []
    for n in NODES:
        ev = evaluation[n["id"]]
        out.append({
            "node_id": n["id"],
            "anomaly_score": ev["anomaly_score"],
            "state": ev["status"],
            "if_score": ev["if_score"],
            "if_state": ev["if_state"],
            "threshold_warning": 0.5,
            "threshold_failure": 1.0,
            "method": ev["method"],
            "if_method": ev["if_method"],
        })
    return {"nodes": out, "timestamp": str(snap.timestamp)}


def cascade_payload(evaluation, predicted, ranked, n3_failed, n4_departed):
    active = []
    synthetic = False
    if n3_failed:
        synthetic = True
        chain = ["N3", "N4", "N5", "N6"]
        for a, b in zip(chain, chain[1:]):
            active.append(f"{a}->{b}")
    elif n4_departed:
        active.append("N3->N4")
        synthetic = True
    return {
        "active_edges": active,
        "synthetic": synthetic,
        "method": METHOD_LABELS["propagation"],
        "note": ("N3's anomaly is real SWaT attack data; the downstream "
                 "propagation shown is our model's prediction, illustrated "
                 "for the demo (Section 5.2 step 7 disclosure)."
                 if synthetic else None),
    }


@app.get("/api/cascade")
def get_cascade():
    snap = replay.latest()
    if snap is None:
        return {"active_edges": [], "synthetic": False,
                "method": METHOD_LABELS["propagation"], "note": None}
    evaluation, predicted, ranked, n3_failed, n4_departed = engine.evaluate(snap)
    return cascade_payload(evaluation, predicted, ranked, n3_failed, n4_departed)


# ---------------- intervention / impact ----------------


@app.get("/api/intervention/ranking")
def intervention_ranking():
    snap = replay.latest()
    if snap is None:
        return {"ranked": [], "note": "replay not started"}
    evaluation, predicted, ranked, n3_failed, n4_departed = engine.evaluate(snap)
    countdown = {}
    if engine.failure_at is not None or engine.simulated:
        for nid in ("N4", "N5", "N6"):
            countdown[nid] = countdown_from(nid, snap.position)
    ranked = rank_interventions(evaluation, predicted, countdown)
    return {
        "ranked": ranked,
        "note": (f"Time-to-impact for N4-N6 counts down from the observed "
                 f"N3 failure at {replay.state.multiplier}x replay speed "
                 f"(locked default: 30x)."
                 if countdown else None),
    }


def countdown_from(node_id: str, position: int) -> float:
    """Process-time seconds until predicted failure reaches node_id from now."""
    elapsed = position - (engine.failure_at or 0)
    if node_id == "N4":
        eta = N4_DEPARTURE_LAG - elapsed
    elif node_id == "N5":
        eta = N4_DEPARTURE_LAG + HOP_LAG_SECONDS["N4->N5"] - elapsed
    else:
        eta = N4_DEPARTURE_LAG + HOP_LAG_SECONDS["N4->N5"] \
            + HOP_LAG_SECONDS["N5->N6"] - elapsed
    return max(float(eta), 1.0)


@app.post("/api/intervention/apply")
def intervention_apply(req: InterventionApplyRequest):
    if req.node_id not in NODE_BY_ID:
        raise HTTPException(status_code=404, detail="unknown node_id")
    snap = replay.latest()
    if snap is None:
        raise HTTPException(status_code=409, detail="replay not started")
    engine.apply_intervention(req.node_id)
    replay.stop()
    return {
        "applied": req.node_id,
        "display_name": NODE_BY_ID[req.node_id]["display_name"],
        "replay": replay.status(),
    }


@app.get("/api/impact/before-after")
def impact_before_after():
    """Impact comparison with a concrete reduction number (Section 9 step 9).

    Scenario A (no intervention): cascade reaches N4-N6 = 3 downstream
    systems affected. Scenario B (recommended intervention at N4, the
    FOCUS HERE FIRST node): propagation stops at N4 = 1 system affected.
    """
    snap = replay.latest()
    applied = engine.intervention_applied
    focus = None
    if snap is not None:
        evaluation, predicted, ranked, n3_failed, n4_departed = engine.evaluate(snap)
        if ranked:
            focus = ranked[0]["node_id"]
    # Without intervention the cascade reaches N4-N6 = 3 systems. Acting on
    # node X stops propagation downstream of X; systems already reached
    # (N4 up to and including X) count as affected.
    order = [n["id"] for n in NODES]
    affected_after = 3
    if applied:
        i_applied = order.index(applied)
        i_first = order.index("N4")
        affected_after = max(1, i_applied - i_first + 1)
    return {
        "before": {"downstream_systems_affected": 3},
        "after": {"downstream_systems_affected": affected_after},
        "headline": f"Downstream systems affected: 3 -> {affected_after}",
        "intervention_applied": applied,
        "focus_node": focus,
        "method": "fixed-chain propagation footprint: acting on a node "
                  "contains the cascade there; systems already reached "
                  "before intervention count as affected",
    }


# ---------------- validation ----------------


@app.get("/api/validation/metrics")
def get_validation_metrics():
    return validation_metrics()


@app.get("/api/validation/full")
def get_full_dataset_metrics():
    """Secondary fact for judges who ask (never the headline)."""
    return full_dataset_metrics()


@app.get("/api/methods")
def get_methods():
    """Honesty labels for all three AI components (Section 10)."""
    return {
        "components": [
            {"name": "Anomaly detection", "method": METHOD_LABELS["anomaly"]},
            {"name": "Propagation estimation", "method": METHOD_LABELS["propagation"]},
            {"name": "Intervention ranking", "method": METHOD_LABELS["ranking"]},
        ]
    }


@app.get("/api/explanation/{node_id}")
def get_explanation(node_id: str):
    if node_id not in NODE_BY_ID:
        raise HTTPException(status_code=404, detail="unknown node_id")
    snap = replay.latest()
    if snap is None:
        raise HTTPException(status_code=409, detail="replay not started")
    evaluation, predicted, ranked, n3_failed, n4_departed = engine.evaluate(snap)
    entry = next((r for r in ranked if r["node_id"] == node_id), None)
    if entry is None:
        entry = {
            "node_id": node_id,
            "score": 0.0,
            "breakdown": {"downstream_count_norm": 0.0,
                          "propagation_prob": 0.0,
                          "time_to_impact_inv_norm": 0.0,
                          "criticality": 0.0},
            "rank": None,
            "label": None,
            "method": METHOD_LABELS["ranking"],
            "downstream_nodes": reachable_downstream(node_id),
        }
    return explain_recommendation(entry, predicted)
