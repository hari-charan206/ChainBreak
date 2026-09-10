"""Environments API (Section 9.1) — all routes require a valid JWT and
enforce "is this environment's user_id the requester" (Section 4.3).
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_owned_environment
from app.db import get_conn
from app.engine import evaluate_environment
from app.ingestion import mqtt_subscriber
from app.models import edges as edges_model
from app.models import environments as envs_model
from app.models import nodes as nodes_model
from app.models import sensor_bindings as bindings_model

router = APIRouter(prefix="/api/environments", tags=["environments"])


# ---------------- request schemas ----------------


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    industry_template: str = "Custom"


class NodeCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    node_type: str = "sensor"
    position_x: float = 0.0
    position_y: float = 0.0


class EdgeCreate(BaseModel):
    source: int
    target: int
    relationship_type: str = "feeds"
    criticality: float = Field(default=0.5, ge=0.0, le=1.0)


class EnvironmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    industry_template: str | None = None


class NodeUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    node_type: str | None = None


class SensorBindingCreate(BaseModel):
    node_id: int
    mqtt_topic: str = Field(min_length=1, max_length=200)
    unit: str = ""
    warning_threshold: float | None = None
    failure_threshold: float | None = None
    baseline: float | None = Field(
        default=None,
        description=("Optional observed baseline; cold-start defaults apply "
                     "as warning = baseline x1.2, failure = x1.5 "
                     "(Section 12.4) when explicit thresholds are omitted."),
    )


class BindingUpdate(BaseModel):
    """Threshold refinement on an existing binding (Section 7.1: the anomaly
    model refines thresholds live as data arrives — this is its manual
    counterpart). Fields left out are left unchanged."""
    warning_threshold: float | None = None
    failure_threshold: float | None = None


# ---------------- environments ----------------


@router.get("")
def list_environments(user: dict = Depends(get_current_user)):
    return {"environments": envs_model.list_for_user(user["id"])}


@router.post("", status_code=201)
def create_environment(req: EnvironmentCreate,
                       user: dict = Depends(get_current_user)):
    env = envs_model.create(user["id"], req.name, req.industry_template)
    return env


@router.get("/{environment_id}")
def get_environment(env: dict = Depends(get_owned_environment)):
    payload = dict(env)
    payload["nodes"] = nodes_model.list_for_environment(env["id"])
    payload["edges"] = edges_model.list_for_environment(env["id"])
    payload["sensor_bindings"] = bindings_model.list_for_environment(env["id"])
    return payload


@router.patch("/{environment_id}")
def update_environment(environment_id: int, req: EnvironmentUpdate,
                       env: dict = Depends(get_owned_environment)):
    try:
        updated = envs_model.update(env["id"], req.name, req.industry_template)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409,
                            detail="you already have an environment with "
                                   "that name") from None
    return updated


@router.delete("/{environment_id}")
def delete_environment(env: dict = Depends(get_owned_environment)):
    envs_model.delete(env["id"], env["user_id"])
    return {"ok": True}


# ---------------- builder sub-resources ----------------


@router.post("/{environment_id}/nodes", status_code=201)
def add_node(environment_id: int, req: NodeCreate,
             env: dict = Depends(get_owned_environment)):
    node = nodes_model.create(env["id"], req.display_name, req.node_type,
                              req.position_x, req.position_y)
    nodes_model.auto_layout(env["id"])
    return node


@router.patch("/{environment_id}/nodes/{node_id}")
def update_node(environment_id: int, node_id: int, req: NodeUpdate,
                env: dict = Depends(get_owned_environment)):
    node = nodes_model.update(node_id, env["id"], req.display_name,
                              req.node_type)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    return node


@router.delete("/{environment_id}/nodes/{node_id}")
def delete_node(environment_id: int, node_id: int,
                env: dict = Depends(get_owned_environment)):
    if not nodes_model.delete(node_id, env["id"]):
        raise HTTPException(status_code=404, detail="node not found")
    return {"ok": True}


@router.delete("/{environment_id}/edges/{edge_id}")
def delete_edge(environment_id: int, edge_id: int,
                env: dict = Depends(get_owned_environment)):
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM edges WHERE id = ? AND environment_id = ?",
        (edge_id, env["id"]),
    )
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="edge not found")
    return {"ok": True}


@router.delete("/{environment_id}/sensor-bindings/{binding_id}")
def delete_binding(environment_id: int, binding_id: int,
                   env: dict = Depends(get_owned_environment)):
    binding = bindings_model.get(binding_id)
    node = (nodes_model.get(binding["node_id"])
            if binding is not None else None)
    if binding is None or node is None or node["environment_id"] != env["id"]:
        raise HTTPException(status_code=404, detail="binding not found")
    bindings_model.delete(binding_id)
    return {"ok": True}


@router.post("/{environment_id}/edges", status_code=201)
def add_edge(environment_id: int, req: EdgeCreate,
             env: dict = Depends(get_owned_environment)):
    node_ids = {n["id"] for n in
                nodes_model.list_for_environment(env["id"])}
    if req.source not in node_ids or req.target not in node_ids:
        raise HTTPException(status_code=404,
                            detail="source/target node not in this environment")
    if req.source == req.target:
        raise HTTPException(status_code=422,
                            detail="cannot connect a node to itself")
    try:
        return edges_model.create(env["id"], req.source, req.target,
                                  req.relationship_type, req.criticality)
    except Exception:
        raise HTTPException(
            status_code=409,
            detail="an edge between these nodes already exists",
        ) from None


@router.post("/{environment_id}/sensor-bindings", status_code=201)
def add_sensor_binding(environment_id: int, req: SensorBindingCreate,
                       env: dict = Depends(get_owned_environment)):
    node = nodes_model.get(req.node_id)
    if node is None or node["environment_id"] != env["id"]:
        raise HTTPException(status_code=404, detail="node not found")
    if bindings_model.get_by_topic(req.mqtt_topic) is not None:
        raise HTTPException(status_code=409,
                            detail="mqtt topic already bound")
    if (req.warning_threshold is not None
            and req.failure_threshold is not None
            and req.failure_threshold <= req.warning_threshold):
        raise HTTPException(status_code=422,
                            detail="failure_threshold must exceed "
                                   "warning_threshold")
    binding = bindings_model.create(
        req.node_id, req.mqtt_topic, req.unit,
        req.warning_threshold, req.failure_threshold, req.baseline)
    mqtt_subscriber.refresh_subscriptions()
    return binding


@router.patch("/{environment_id}/sensor-bindings/{binding_id}")
def update_binding(environment_id: int, binding_id: int,
                   req: BindingUpdate,
                   env: dict = Depends(get_owned_environment)):
    """Adjust thresholds/baseline on a binding (common after warm-up)."""
    binding = bindings_model.get(binding_id)
    node = (nodes_model.get(binding["node_id"])
            if binding is not None else None)
    if binding is None or node is None or node["environment_id"] != env["id"]:
        raise HTTPException(status_code=404, detail="binding not found")
    new_warn = (req.warning_threshold
                if "warning_threshold" in req.model_fields_set
                else binding["warning_threshold"])
    new_fail = (req.failure_threshold
                if "failure_threshold" in req.model_fields_set
                else binding["failure_threshold"])
    if new_warn is not None and new_fail is not None \
            and new_fail <= new_warn:
        raise HTTPException(status_code=422,
                            detail="failure_threshold must exceed "
                                   "warning_threshold")
    return bindings_model.update_thresholds(binding_id, new_warn, new_fail)


# ---------------- polled state ----------------


@router.get("/{environment_id}/state")
def get_state(env: dict = Depends(get_owned_environment)):
    """Polled every ~2s by the frontend (Section 9.1 generic payload)."""
    return evaluate_environment(env["id"])
