"""Propagation estimation — generalized to arbitrary user-defined graphs
(build prompt v4 Section 7.2).

Same probabilistic/trend-based approach as v3, NOT trained — never
described as trained. For each edge A -> B:

  propagation_prob(B) = anomaly_score(A) * product of edge criticalities
  eta_seconds(B)      = sum of per-hop lag estimates along the path

v3's measured SWaT hop lags are gone with the fixed graph; every hop in a
user-defined environment uses the same disclosed assumed lag v3 used for
unmeasured hops (300s), carried in every payload's disclosure note.
"""

from __future__ import annotations

# v3's disclosed assumed lag for unmeasured hops — reused as the v4 default
ASSUMED_HOP_LAG_SECONDS = 300
# v3's normalization cap for time-to-impact (unchanged locked constant)
ETA_CAP_SECONDS = 2400
# branches below this propagation probability are not predicted at all
NEGLIGIBLE_PROB = 0.01


def build_adjacency(edges: list[dict]) -> dict[int, list[dict]]:
    """node_id -> outgoing edge list (works for any graph shape)."""
    adj: dict[int, list[dict]] = {}
    for e in edges:
        adj.setdefault(e["source_node_id"], []).append(e)
    return adj


def incoming_criticality(edges: list[dict]) -> dict[int, float]:
    """node_id -> worst (max) incoming edge criticality; 0.0 for origins.

    v3 used the node's single incoming edge on the fixed chain; with
    arbitrary graphs the worst incoming dependency is the honest analogue.
    """
    out: dict[int, float] = {}
    for e in edges:
        out[e["target_node_id"]] = max(out.get(e["target_node_id"], 0.0),
                                       float(e["criticality"]))
    return out


def reachable_downstream(adjacency: dict[int, list[dict]],
                         node_id: int) -> list[int]:
    """All nodes strictly reachable from node_id (BFS, cycles safe)."""
    seen: set[int] = set()
    queue = [node_id]
    while queue:
        current = queue.pop(0)
        for edge in adjacency.get(current, []):
            nxt = edge["target_node_id"]
            if nxt not in seen and nxt != node_id:
                seen.add(nxt)
                queue.append(nxt)
    return sorted(seen)


def propagate(evaluation: dict[int, dict],
              adjacency: dict[int, list[dict]]) -> dict[int, dict]:
    """Predicted propagation from currently warning/failed nodes.

    Returns node_id -> {propagation_prob, eta_seconds, source_node, path,
    assumed_hops} for every node downstream of a seed. The origin node's
    own probability is its measured anomaly score (v3 behavior).
    """
    predicted: dict[int, dict] = {}
    seeds = [nid for nid, ev in evaluation.items()
             if ev["status"] in ("warning", "failed")]
    for origin in seeds:
        origin_score = max(evaluation[origin]["anomaly_score"], 0.01)
        # (node, prob, eta, path) — BFS with multiplicative decay
        queue: list[tuple[int, float, float, list[int]]] = [
            (origin, origin_score, 0.0, [origin])]
        while queue:
            current, prob, eta, path = queue.pop(0)
            for edge in adjacency.get(current, []):
                nxt = edge["target_node_id"]
                if nxt in path:  # no cycles
                    continue
                new_prob = prob * float(edge["criticality"])
                if new_prob < NEGLIGIBLE_PROB:
                    continue
                new_eta = eta + ASSUMED_HOP_LAG_SECONDS
                candidate = {
                    "propagation_prob": round(min(new_prob, 1.0), 4),
                    "eta_seconds": round(new_eta, 1),
                    "source_node": origin,
                    "path": path + [nxt],
                    "assumed_hops": True,  # every v4 hop is the assumed lag
                }
                existing = predicted.get(nxt)
                if existing is None or (candidate["propagation_prob"]
                                        > existing["propagation_prob"]):
                    predicted[nxt] = candidate
                    queue.append((nxt, new_prob, new_eta, path + [nxt]))
    return predicted
