"""edges — data access (build prompt v4 Section 5.2)."""

from __future__ import annotations

from app.db import get_conn


def get(edge_id: int) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM edges WHERE id = ?", (edge_id,)
    ).fetchone()
    return dict(row) if row else None


def list_for_environment(environment_id: int) -> list[dict]:
    rows = get_conn().execute(
        "SELECT * FROM edges WHERE environment_id = ? ORDER BY id",
        (environment_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def create(environment_id: int, source_node_id: int, target_node_id: int,
           relationship_type: str = "feeds",
           criticality: float = 0.5) -> dict:
    criticality = min(max(float(criticality), 0.0), 1.0)
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO edges (environment_id, source_node_id, target_node_id, "
        "relationship_type, criticality) VALUES (?, ?, ?, ?, ?)",
        (environment_id, source_node_id, target_node_id,
         relationship_type.strip() or "feeds", criticality),
    )
    conn.commit()
    return get(cur.lastrowid)  # type: ignore[arg-type]


def adjacency(edges: list[dict]) -> dict[int, list[dict]]:
    """node_id -> outgoing edges (for walking arbitrary graph shapes)."""
    out: dict[int, list[dict]] = {}
    for e in edges:
        out.setdefault(e["source_node_id"], []).append(e)
    return out
