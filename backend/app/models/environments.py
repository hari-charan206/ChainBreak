"""environments — data access (build prompt v4 Sections 4.2, 5.2)."""

from __future__ import annotations

from app.db import get_conn, INDUSTRY_TEMPLATES


def get(environment_id: int) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM environments WHERE id = ?", (environment_id,)
    ).fetchone()
    return dict(row) if row else None


def list_for_user(user_id: int) -> list[dict]:
    """Picker payload: name, node count, last-active timestamp, status chip."""
    rows = get_conn().execute(
        """
        SELECT e.id, e.name, e.industry_template, e.created_at,
               (SELECT COUNT(*) FROM nodes n WHERE n.environment_id = e.id)
                   AS node_count,
               (SELECT COUNT(*) FROM nodes n
                 WHERE n.environment_id = e.id
                   AND n.status IN ('warning', 'failed'))
                   AS nodes_degraded,
               (SELECT MAX(r.created_at) FROM sensor_readings r
                 JOIN sensor_bindings b ON b.id = r.binding_id
                 JOIN nodes n2 ON n2.id = b.node_id
                 WHERE n2.environment_id = e.id)
                   AS last_active
        FROM environments e
        WHERE e.user_id = ?
        ORDER BY e.created_at DESC
        """,
        (user_id,),
    ).fetchall()

    out = []
    for r in rows:
        d = dict(r)
        d["status_summary"] = _chip(d["node_count"], d["nodes_degraded"])
        out.append(d)
    return out


def _chip(node_count: int, degraded: int) -> str:
    if node_count == 0:
        return "no nodes yet"
    if degraded == 0:
        return "all healthy"
    return f"{degraded} degraded"


def create(user_id: int, name: str,
           industry_template: str = "Custom") -> dict:
    if industry_template not in INDUSTRY_TEMPLATES:
        industry_template = "Custom"
    cur = get_conn().execute(
        "INSERT INTO environments (user_id, name, industry_template) "
        "VALUES (?, ?, ?)",
        (user_id, name.strip(), industry_template),
    )
    get_conn().commit()
    return get(cur.lastrowid)  # type: ignore[arg-type]


def update(environment_id: int, name: str | None = None,
           industry_template: str | None = None) -> dict | None:
    """Rename and/or change template. Raises sqlite3.IntegrityError on a
    duplicate name for the same user (caller maps it to 409)."""
    conn = get_conn()
    if name is not None and name.strip():
        conn.execute(
            "UPDATE environments SET name = ? WHERE id = ?",
            (name.strip(), environment_id),
        )
    if industry_template is not None:
        if industry_template not in INDUSTRY_TEMPLATES:
            industry_template = "Custom"
        conn.execute(
            "UPDATE environments SET industry_template = ? WHERE id = ?",
            (industry_template, environment_id),
        )
    conn.commit()
    return get(environment_id)


def delete(environment_id: int, user_id: int) -> bool:
    cur = get_conn().execute(
        "DELETE FROM environments WHERE id = ? AND user_id = ?",
        (environment_id, user_id),
    )
    get_conn().commit()
    return cur.rowcount > 0
