"""nodes — data access (build prompt v4 Section 5.2)."""

from __future__ import annotations

from app.db import (
    COLD_START_FAILURE_MULT,
    COLD_START_WARNING_MULT,
    get_conn,
    NODE_TYPES,
)


def get(node_id: int) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM nodes WHERE id = ?", (node_id,)
    ).fetchone()
    return dict(row) if row else None


def list_for_environment(environment_id: int) -> list[dict]:
    rows = get_conn().execute(
        "SELECT * FROM nodes WHERE environment_id = ? ORDER BY id",
        (environment_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def create(environment_id: int, display_name: str,
           node_type: str = "sensor", position_x: float = 0.0,
           position_y: float = 0.0) -> dict:
    if node_type not in NODE_TYPES:
        node_type = "custom"
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO nodes (environment_id, display_name, node_type, "
        "position_x, position_y) VALUES (?, ?, ?, ?, ?)",
        (environment_id, display_name.strip(), node_type,
         float(position_x), float(position_y)),
    )
    conn.commit()
    return get(cur.lastrowid)  # type: ignore[arg-type]


def update(node_id: int, environment_id: int,
           display_name: str | None = None,
           node_type: str | None = None) -> dict | None:
    """Rename and/or retype a node; None when it is not in this env."""
    node = get(node_id)
    if node is None or node["environment_id"] != environment_id:
        return None
    conn = get_conn()
    if display_name is not None and display_name.strip():
        conn.execute(
            "UPDATE nodes SET display_name = ? WHERE id = ?",
            (display_name.strip(), node_id),
        )
    if node_type is not None:
        if node_type not in NODE_TYPES:
            node_type = "custom"
        conn.execute(
            "UPDATE nodes SET node_type = ? WHERE id = ?",
            (node_type, node_id),
        )
    conn.commit()
    return get(node_id)


def set_status(node_id: int, status: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE nodes SET status = ? WHERE id = ?", (status, node_id)
    )
    conn.commit()


def delete(node_id: int, environment_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM nodes WHERE id = ? AND environment_id = ?",
        (node_id, environment_id),
    )
    conn.commit()
    return cur.rowcount > 0


def auto_layout(environment_id: int) -> None:
    """Assign cascade row positions to nodes that are still at the origin.

    The builder UI uses simple forms (no drag-and-drop editor), so nodes get
    a default left-to-right layout order; positions persist for React Flow.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT id FROM nodes WHERE environment_id = ? "
        "AND position_x = 0 AND position_y = 0 ORDER BY id",
        (environment_id,),
    ).fetchall()
    for i, r in enumerate(rows):
        conn.execute(
            "UPDATE nodes SET position_x = ?, position_y = ? WHERE id = ?",
            (60 + i * 220.0, 160.0, r["id"]),
        )
    conn.commit()


# ---- sensor_bindings helpers live here to keep threshold defaults with the
# node-creation cold-start rule (Section 12.4). ----

def apply_cold_start_defaults(warning: float | None,
                              failure: float | None,
                              baseline: float | None) -> tuple[float | None,
                                                               float | None]:
    """Fill missing thresholds from the locked cold-start formula.

    warning = baseline x 1.2, failure = baseline x 1.5. If no baseline was
    given either, thresholds stay None and the AI layer keeps the node
    healthy until enough live data accumulates (warm-up disclosure).
    """
    if warning is None and baseline is not None:
        warning = round(float(baseline) * COLD_START_WARNING_MULT, 6)
    if failure is None and baseline is not None:
        failure = round(float(baseline) * COLD_START_FAILURE_MULT, 6)
    return warning, failure
