"""Intervention ranking — LOCKED heuristic (CONTRACT.md Section 11).

score = 0.35 x downstream_count_norm
      + 0.30 x propagation_prob
      + 0.20 x time_to_impact_inv_norm
      + 0.15 x criticality

Weights are locked starting values. Any tuning must be flagged in
CONTRACT.md, never silently changed here. Explicitly a heuristic scoring
model — never described as trained or learned (v1).
"""

from __future__ import annotations

from app.ai.propagation import ETA_CAP_SECONDS, reachable_downstream
from app.models.graph_schema import EDGES, NODES, NODE_BY_ID

WEIGHTS = {
    "downstream_count": 0.35,
    "propagation_prob": 0.30,
    "time_to_impact_inv": 0.20,
    "criticality": 0.15,
}

# Criticality of the worst edge leaving each node's incoming path — for the
# fixed chain we use the node's own incoming edge criticality as its
# dependency criticality factor (N1 has none -> 0).
INCOMING_CRITICALITY = {"N1": 0.0}
for _e in EDGES:
    INCOMING_CRITICALITY[_e["to"]] = _e["criticality"]


def rank_interventions(evaluation: dict, predicted: dict,
                       failed_countdown: dict | None = None) -> list[dict]:
    """Rank candidate intervention nodes by the locked heuristic.

    Candidates: any node currently warning/failed, plus any node with an
    active propagation prediction. failed_countdown maps node_id -> seconds
    until simulated failure for countdown-normalized time-to-impact.
    """
    failed_countdown = failed_countdown or {}
    candidates: set[str] = set()
    for nid, ev in evaluation.items():
        if ev["status"] in ("warning", "failed"):
            candidates.add(nid)
    candidates.update(predicted.keys())

    ranked = []
    for nid in candidates:
        node = NODE_BY_ID[nid]
        downstream = reachable_downstream(nid)
        downstream_count_norm = (len(downstream) /
                                 (len(NODES) - 1))
        pred = predicted.get(nid, {})
        propagation_prob = float(pred.get("propagation_prob", 0.0))
        if nid in failed_countdown:
            eta = float(failed_countdown[nid])
        else:
            eta = float(pred.get("eta_seconds", ETA_CAP_SECONDS))
        time_to_impact_inv_norm = 1.0 - min(eta / ETA_CAP_SECONDS, 1.0)
        criticality = INCOMING_CRITICALITY.get(nid, 0.0)

        score = (WEIGHTS["downstream_count"] * downstream_count_norm
                 + WEIGHTS["propagation_prob"] * propagation_prob
                 + WEIGHTS["time_to_impact_inv"] * time_to_impact_inv_norm
                 + WEIGHTS["criticality"] * criticality)

        ranked.append({
            "node_id": nid,
            "display_name": node["display_name"],
            "score": round(score, 4),
            "breakdown": {
                "downstream_count_norm": round(downstream_count_norm, 4),
                "propagation_prob": round(propagation_prob, 4),
                "time_to_impact_inv_norm": round(time_to_impact_inv_norm, 4),
                "criticality": round(criticality, 4),
            },
            "weights": WEIGHTS,
            "eta_seconds": round(eta, 1),
            "downstream_nodes": downstream,
            "method": "heuristic scoring model (locked v1 weights)",
        })

    ranked.sort(key=lambda r: -r["score"])
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
        r["label"] = "FOCUS HERE FIRST" if i == 0 else None
    return ranked
