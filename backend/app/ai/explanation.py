"""Human-readable explanation payloads for the ExplanationDrawer.

Renders the heuristic score breakdown verbatim (CONTRACT.md Sections 7/13) —
the frontend does no math of its own.
"""

from __future__ import annotations

from app.ai.intervention_ranking import WEIGHTS
from app.ai.propagation import HOP_LAG_SECONDS
from app.models.graph_schema import NODE_BY_ID

FACTOR_LABELS = {
    "downstream_count_norm": "Downstream node count",
    "propagation_prob": "Propagation probability",
    "time_to_impact_inv_norm": "Time-to-impact (sooner scores higher)",
    "criticality": "Dependency criticality",
}

METHOD_LABELS = {
    "anomaly": "Anomaly detection: trained Isolation Forest (scikit-learn), "
               "validated on the locked demo window",
    "propagation": "Propagation estimation: probabilistic/trend model over "
                   "sensor behavior + dependency strength (not trained)",
    "ranking": "Intervention ranking: heuristic scoring model with locked v1 "
               "weights (not trained/learned)",
}


def explain_recommendation(entry: dict, predicted: dict) -> dict:
    """Full payload for the drawer when a node is selected."""
    node = NODE_BY_ID[entry["node_id"]]
    pred = predicted.get(entry["node_id"])
    factors = []
    for key, weight in WEIGHTS.items():
        norm_key = {
            "downstream_count": "downstream_count_norm",
            "propagation_prob": "propagation_prob",
            "time_to_impact_inv": "time_to_impact_inv_norm",
            "criticality": "criticality",
        }[key]
        factors.append({
            "factor": norm_key,
            "label": FACTOR_LABELS[norm_key],
            "weight": weight,
            "value": entry["breakdown"][norm_key],
            "contribution": round(weight * entry["breakdown"][norm_key], 4),
        })
    factors.sort(key=lambda f: -f["contribution"])

    sentences = [
        f"{node['display_name']} ({node['id']}) scores "
        f"{entry['score']:.2f} on the locked heuristic.",
    ]
    if pred:
        path = " -> ".join(pred["path"])
        sentences.append(
            f"If unaddressed, predicted propagation path is {path} at "
            f"{pred['propagation_prob']:.0%} probability, reaching the last "
            f"node in ~{int(pred['eta_seconds'])}s of process time "
            f"(~{int(pred['eta_seconds'] / 30)}s at 30x replay)."
        )
    if entry.get("downstream_nodes"):
        sentences.append(
            f"Intervening here protects {len(entry['downstream_nodes'])} "
            f"downstream systems: {', '.join(entry['downstream_nodes'])}."
        )
    sentences.append(
        "Score = 0.35×downstream + 0.30×propagation + 0.20×time + "
        "0.15×criticality (heuristic, locked weights)."
    )

    return {
        "node_id": entry["node_id"],
        "display_name": node["display_name"],
        "role": node["role"],
        "score": entry["score"],
        "rank": entry.get("rank"),
        "label": entry.get("label"),
        "factors": factors,
        "summary": " ".join(sentences),
        "method": entry.get("method", METHOD_LABELS["ranking"]),
        "honesty_labels": [METHOD_LABELS["anomaly"], METHOD_LABELS["propagation"],
                           METHOD_LABELS["ranking"]],
    }
