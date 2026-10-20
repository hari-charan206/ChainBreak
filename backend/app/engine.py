"""Environment evaluation engine (v4).

Assembles the generic /state payload (Section 9.1) for any user-defined
environment: per-binding live detection -> per-node status -> propagation
over the user's graph -> locked-weight intervention ranking -> validation.

No replay, no fixed graph: everything is read from SQLite for the given
environment on each evaluation (cheap at demo scale; the Isolation Forest
per binding is refit-cached inside anomaly_detection).
"""

from __future__ import annotations

from app.ai import anomaly_detection, propagation
from app.ai.explanation import explain_recommendation
from app.ai.intervention_ranking import rank_interventions
from app.ai.validation import validation_metrics
from app.models import edges as edges_model
from app.models import nodes as nodes_model
from app.models import sensor_bindings as bindings_model
from app.db import get_conn


def _last_updated_by_binding(environment_id: int) -> dict[int, str]:
    rows = get_conn().execute(
        """
        SELECT r.binding_id, MAX(r.created_at) AS last_updated
        FROM sensor_readings r
        JOIN sensor_bindings sb ON sb.id = r.binding_id
        JOIN nodes n ON n.id = sb.node_id
        WHERE n.environment_id = ?
        GROUP BY r.binding_id
        """,
        (environment_id,),
    ).fetchall()
    return {r["binding_id"]: r["last_updated"] for r in rows}


def evaluate_environment(environment_id: int) -> dict:
    nodes = nodes_model.list_for_environment(environment_id)
    edges = edges_model.list_for_environment(environment_id)
    bindings = bindings_model.list_for_environment(environment_id)
    last_updated = _last_updated_by_binding(environment_id)

    node_by_id = {n["id"]: n for n in nodes}
    name_by_id = {n["id"]: n["display_name"] for n in nodes}

    # ---- 1. per-binding live detection (Section 6.2 step 3) ----
    pairs_by_node: dict[int, list[tuple[dict, dict]]] = {}
    detections: list[dict] = []
    for b in bindings:
        values = bindings_model.recent_values(b["id"], limit=200)
        det = anomaly_detection.detect_binding_state(b, values)
        det["last_value"] = values[-1] if values else None
        det["last_updated"] = last_updated.get(b["id"])
        det["trend"] = [round(v, 4) for v in values[-60:]]
        detections.append(det)
        pairs_by_node.setdefault(b["node_id"], []).append((b, det))

    # ---- 2. per-node status: worst binding state (Section 6.2 step 3-4) ----
    evaluation: dict[int, dict] = {}
    order = {"healthy": 0, "warning": 1, "failed": 2}
    for n in nodes:
        pairs = pairs_by_node.get(n["id"], [])
        worst = "offline"     # no data yet -> offline (Section 6.4)
        anomaly_score = 0.0
        warm_up = False
        current_value = None
        updated = None
        for b, d in pairs:
            if d["samples"] == 0:
                continue      # bound but no live data yet
            state = d["state"] if d["state"] in order else "healthy"
            if worst == "offline" or order[state] > order[worst]:
                worst = state
            anomaly_score = max(anomaly_score, d["anomaly_score"])
            warm_up = warm_up or d["warm_up"]
            if d["last_value"] is not None:
                current_value = d["last_value"]
            if d["last_updated"] and (updated is None
                                      or d["last_updated"] > updated):
                updated = d["last_updated"]
        evaluation[n["id"]] = {
            "status": worst,
            "anomaly_score": round(anomaly_score, 4),
            "warm_up": warm_up,
            "current_value": current_value,
            "last_updated": updated,
        }

    # persist node statuses so the picker chips stay live (best-effort)
    for n in nodes:
        if n["status"] != evaluation[n["id"]]["status"]:
            nodes_model.set_status(n["id"], evaluation[n["id"]]["status"])

    # ---- 3. propagation over the user's graph (Section 6.2 step 4) ----
    adj = propagation.build_adjacency(edges)
    predicted = propagation.propagate(evaluation, adj)
    for nid, p in predicted.items():
        p["path_names"] = [name_by_id.get(x, str(x)) for x in p["path"]]

    # ---- 4. locked-weight intervention ranking (Section 7.3) ----
    ranked = rank_interventions(evaluation, predicted, edges, len(nodes))
    for r in ranked:
        r["node_name"] = name_by_id.get(r["node_id"], str(r["node_id"]))
        r["downstream_node_names"] = [
            name_by_id.get(x, str(x)) for x in r["downstream_nodes"]]

    # ---- 5. edge cascade highlighting ----
    edge_payload = []
    for e in edges:
        active = False
        p = predicted.get(e["target_node_id"])
        if p and len(p["path"]) >= 2 \
                and p["path"][-2] == e["source_node_id"] \
                and p["path"][-1] == e["target_node_id"]:
            active = True
        edge_payload.append({
            "id": e["id"],
            "source": e["source_node_id"],
            "target": e["target_node_id"],
            "relationship_type": e["relationship_type"],
            "criticality": e["criticality"],
            "active_cascade": active,
        })

    # ---- 6. cascade + intervention + validation payloads ----
    active_cascade = None
    if predicted:
        seeds = sorted({p["source_node"] for p in predicted.values()})
        active_cascade = {
            "origin_node_id": seeds[0],
            "origin_node_name": name_by_id.get(seeds[0], str(seeds[0])),
            "affected_nodes": sorted(predicted.keys()),
            "affected_node_names": [name_by_id.get(x, str(x))
                                    for x in sorted(predicted.keys())],
            "active_edges": [
                f"{e['source']}->{e['target']}"
                for e in edge_payload if e["active_cascade"]],
            "method": ("propagation estimation: probabilistic model over "
                       "anomaly score x edge criticality (not trained)"),
        }

    intervention = None
    if ranked:
        top = ranked[0]
        node = node_by_id[top["node_id"]]
        node_bindings = [b for b in bindings if b["node_id"] == top["node_id"]]
        explanation = explain_recommendation(
            top, predicted, node, node_bindings)
        intervention = {
            "recommended_node_id": top["node_id"],
            "recommended_node_name": top["node_name"],
            "score": top["score"],
            "score_breakdown": top["breakdown"],
            "explanation": explanation["summary"],
            "method": top["method"],
        }

    validation = validation_metrics(detections)

    # ---- 7. projected impact (backend-computed; replaces v3's
    # /impact/before-after endpoint, which the v4 endpoint list drops) ----
    before_after = None
    if active_cascade and intervention is not None:
        rec = intervention["recommended_node_id"]
        rec_pred = predicted.get(rec)
        before = len(active_cascade["affected_nodes"])
        # acting at the recommended node contains propagation there:
        # systems already reached on the path up to and including it
        after = len(rec_pred["path"]) if rec_pred else before
        before_after = {
            "before": {"downstream_systems_affected": before},
            "after": {"downstream_systems_affected": after},
            "headline": f"Downstream systems affected: {before} -> {after}",
            "method": ("projected footprint: acting on the recommended "
                       "node contains the cascade there; nodes already "
                       "reached count as affected"),
        }

    return {
        "environment_id": environment_id,
        "nodes": [
            {
                "id": n["id"],
                "display_name": n["display_name"],
                "node_type": n["node_type"],
                "status": evaluation[n["id"]]["status"],
                "current_value": evaluation[n["id"]]["current_value"],
                "last_updated": evaluation[n["id"]]["last_updated"],
                "anomaly_score": evaluation[n["id"]]["anomaly_score"],
                "warm_up": evaluation[n["id"]]["warm_up"],
                "at_risk": n["id"] in predicted,
                "eta_seconds": (predicted[n["id"]]["eta_seconds"]
                                if n["id"] in predicted else None),
                "predicted_path": (predicted[n["id"]]["path_names"]
                                   if n["id"] in predicted else None),
                "position_x": n["position_x"],
                "position_y": n["position_y"],
                "bindings": [
                    {
                        "topic": b["mqtt_topic"],
                        "unit": b["unit"],
                        "warning_threshold": b["warning_threshold"],
                        "failure_threshold": b["failure_threshold"],
                        "state": d["state"],
                        "if_state": d["if_state"],
                        "if_score": d["if_score"],
                        "calibrated": d["calibrated"],
                        "warm_up": d["warm_up"],
                        "samples": d["samples"],
                        "trend": d["trend"],
                        "last_value": d["last_value"],
                        "last_updated": d["last_updated"],
                    }
                    for b, d in pairs_by_node.get(n["id"], [])
                ],
            }
            for n in nodes
        ],
        "edges": edge_payload,
        "active_cascade": active_cascade,
        "intervention": intervention,
        "ranked": ranked,
        "before_after": before_after,
        "validation_metrics": validation,
    }
