"""Human-readable explanation payloads for the ExplanationDrawer.

Renders the heuristic score breakdown verbatim (v3 Sections 7/13 standard,
carried to v4) — the frontend does no math of its own. References the
user's own node display names and relationship labels instead of SWaT tags.
"""

from __future__ import annotations

from app.ai.intervention_ranking import METHOD_LABEL, WEIGHTS

FACTOR_LABELS = {
    "downstream_count_norm": "Downstream node count",
    "propagation_prob": "Propagation probability",
    "time_to_impact_inv_norm": "Time-to-impact (sooner scores higher)",
    "criticality": "Dependency criticality",
}

METHOD_LABELS = {
    "anomaly": ("Anomaly detection: trained Isolation Forest (scikit-learn), "
                "trained live on each sensor's observed values after a "
                "disclosed warm-up; user-set thresholds until then"),
    "propagation": ("Propagation estimation: probabilistic model over "
                    "anomaly score x edge criticality (not trained)"),
    "ranking": ("Intervention ranking: heuristic scoring model with locked "
                "v1 weights (not trained/learned)"),
}


def explain_recommendation(entry: dict, predicted: dict,
                           node: dict, bindings: list[dict]) -> dict:
    """Full payload for the drawer when a node is selected."""
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
        f"{node['display_name']} scores {entry['score']:.2f} on the "
        f"locked heuristic.",
    ]
    if pred:
        path = " -> ".join(pred["path_names"])
        sentences.append(
            f"If unaddressed, predicted propagation path is {path} at "
            f"{pred['propagation_prob']:.0%} probability, reaching the "
            f"last node in ~{int(pred['eta_seconds'])}s of process time "
            f"(assumed {300}s per hop, disclosed)."
        )
    if entry.get("downstream_nodes"):
        sentences.append(
            f"Intervening here protects {len(entry['downstream_nodes'])} "
            f"downstream nodes: "
            f"{', '.join(entry['downstream_node_names'])}."
        )
    sentences.append(
        "Score = 0.35xdownstream + 0.30xpropagation + 0.20xtime + "
        "0.15xcriticality (heuristic, locked weights)."
    )

    return {
        "node_id": entry["node_id"],
        "display_name": node["display_name"],
        "node_type": node["node_type"],
        "bindings": [
            {"topic": b["mqtt_topic"], "unit": b["unit"],
             "warning_threshold": b["warning_threshold"],
             "failure_threshold": b["failure_threshold"]}
            for b in bindings
        ],
        "score": entry["score"],
        "rank": entry.get("rank"),
        "label": entry.get("label"),
        "factors": factors,
        "summary": " ".join(sentences),
        "method": entry.get("method", METHOD_LABEL),
        "honesty_labels": [METHOD_LABELS["anomaly"],
                           METHOD_LABELS["propagation"],
                           METHOD_LABELS["ranking"]],
    }
