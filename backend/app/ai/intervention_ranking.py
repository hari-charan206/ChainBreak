"""Intervention ranking — LOCKED heuristic (v3 Section 11, carried to v4
unchanged per build prompt Section 7.3).

score = 0.35 x downstream_count_norm
      + 0.30 x propagation_prob
      + 0.20 x time_to_impact_inv_norm
      + 0.15 x criticality

Weights are locked starting values. Any tuning must be flagged in
CONTRACT.md, never silently changed here. Explicitly a heuristic scoring
model — never described as trained or learned.
"""

from __future__ import annotations

from app.ai.propagation import (
    ETA_CAP_SECONDS,
    incoming_criticality,
    reachable_downstream,
)

WEIGHTS = {
    "downstream_count": 0.35,
    "propagation_prob": 0.30,
    "time_to_impact_inv": 0.20,
    "criticality": 0.15,
}

METHOD_LABEL = "heuristic scoring model (locked v1 weights)"


def rank_interventions(evaluation: dict[int, dict],
                       predicted: dict[int, dict],
                       edges: list[dict],
                       node_count: int) -> list[dict]:
    """Rank candidate intervention nodes by the locked heuristic.

    Candidates: any node currently warning/failed, plus any node with an
    active propagation prediction — same rule as v3, now over any graph.
    """
    if node_count <= 1:
        return []

    crit_by_node = incoming_criticality(edges)
    adj = {}
    for e in edges:
        adj.setdefault(e["source_node_id"], []).append(e)

    candidates: set[int] = set()
    for nid, ev in evaluation.items():
        if ev["status"] in ("warning", "failed"):
            candidates.add(nid)
    candidates.update(predicted.keys())

    ranked = []
    for nid in candidates:
        downstream = reachable_downstream(adj, nid)
        downstream_count_norm = len(downstream) / (node_count - 1)
        pred = predicted.get(nid, {})
        propagation_prob = float(pred.get("propagation_prob", 0.0))
        eta = float(pred.get("eta_seconds", ETA_CAP_SECONDS))
        time_to_impact_inv_norm = 1.0 - min(eta / ETA_CAP_SECONDS, 1.0)
        criticality = crit_by_node.get(nid, 0.0)

        score = (WEIGHTS["downstream_count"] * downstream_count_norm
                 + WEIGHTS["propagation_prob"] * propagation_prob
                 + WEIGHTS["time_to_impact_inv"] * time_to_impact_inv_norm
                 + WEIGHTS["criticality"] * criticality)

        ranked.append({
            "node_id": nid,
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
            "method": METHOD_LABEL,
        })

    ranked.sort(key=lambda r: -r["score"])
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
        r["label"] = "FOCUS HERE FIRST" if i == 0 else None
    return ranked
