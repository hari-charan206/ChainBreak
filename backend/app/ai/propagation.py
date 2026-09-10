"""Propagation estimation (CONTRACT.md Section 10, component 2).

Probabilistic/trend-based model over sensor behavior + dependency strength.
NOT trained — never described as trained. For each edge A -> B it estimates:

  propagation_prob(B) = anomaly_score(A) * criticality(A->B)
  eta_seconds(B)      = sum of per-hop lag estimates along the path

Per-hop lags come from the cross-stage correlation analysis (build prompt
Section 2: N3->N4 ~400s, N3->N5 ~1560s cumulative; our quiet-stretch scan:
N6 reaction ~2328s after N3). Unmeasured hops (N1->N2, N2->N3) use an
assumed 300s and are disclosed as assumed.
"""

from __future__ import annotations

from app.models.graph_schema import EDGES, NODES

# Per-hop lag estimates (seconds). Measured where noted; assumed otherwise.
HOP_LAG_SECONDS = {
    "N1->N2": 300,    # assumed (no measurable event pair in the demo window)
    "N2->N3": 300,    # assumed
    "N3->N4": 400,    # measured (build prompt Section 2 cross-correlation)
    "N4->N5": 1160,   # measured (1560s cumulative to N5 minus 400s)
    "N5->N6": 768,    # measured (2328s to N6 minus 1560s, quiet-stretch scan)
}

EDGE_BY_PAIR = {(e["from"], e["to"]): e for e in EDGES}
NODE_ORDER = [n["id"] for n in NODES]

ETA_CAP_SECONDS = 2400  # normalization cap for time-to-impact


def reachable_downstream(node_id: str) -> list[str]:
    """All nodes strictly downstream of node_id on the fixed chain."""
    i = NODE_ORDER.index(node_id)
    return NODE_ORDER[i + 1:]


def propagate(evaluation: dict) -> dict[str, dict]:
    """Predicted propagation from currently anomalous nodes.

    Returns node_id -> {propagation_prob, eta_seconds, source_node, path}
    for every node downstream of a warning/failed node. The origin node's
    own probability is its measured anomaly score.
    """
    predicted: dict[str, dict] = {}

    # Seed: nodes currently warning/failed (real detections)
    seeds = [nid for nid, ev in evaluation.items()
             if ev["status"] in ("warning", "failed")]
    for origin in seeds:
        origin_score = max(evaluation[origin]["anomaly_score"], 0.01)
        # walk the fixed chain forward
        prob = origin_score
        eta = 0.0
        current = origin
        path = [origin]
        while True:
            downstream = reachable_downstream(current)
            if not downstream:
                break
            nxt = downstream[0]
            edge = EDGE_BY_PAIR[(current, nxt)]
            prob = prob * edge["criticality"]
            eta += HOP_LAG_SECONDS[f"{current}->{nxt}"]
            path = path + [nxt]
            existing = predicted.get(nxt)
            candidate = {
                "propagation_prob": round(min(prob, 1.0), 4),
                "eta_seconds": round(eta, 1),
                "source_node": origin,
                "path": list(path),
                "assumed_hops": [k for k, v in HOP_LAG_SECONDS.items()
                                 if v == 300 and k in
                                 [f"{a}->{b}" for a, b in zip(path, path[1:])]],
            }
            # keep the highest-probability prediction per node
            if existing is None or candidate["propagation_prob"] > existing["propagation_prob"]:
                predicted[nxt] = candidate
            current = nxt
    return predicted
