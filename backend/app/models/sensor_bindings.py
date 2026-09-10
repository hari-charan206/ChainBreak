"""sensor_bindings — data access (build prompt v4 Section 5.2).

The topic -> (environment_id, node_id, binding) map is the dynamic lookup
that replaces v3's fixed SWaT tag mapping (Section 6.2 step 2).
"""

from __future__ import annotations

from app.db import get_conn
from app.models.nodes import apply_cold_start_defaults


def get(binding_id: int) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM sensor_bindings WHERE id = ?", (binding_id,)
    ).fetchone()
    return dict(row) if row else None


def list_for_environment(environment_id: int) -> list[dict]:
    rows = get_conn().execute(
        """
        SELECT sb.*, n.environment_id, n.display_name AS node_display_name
        FROM sensor_bindings sb
        JOIN nodes n ON n.id = sb.node_id
        WHERE n.environment_id = ?
        ORDER BY sb.id
        """,
        (environment_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_by_topic(mqtt_topic: str) -> dict | None:
    row = get_conn().execute(
        """
        SELECT sb.*, n.environment_id, n.display_name AS node_display_name
        FROM sensor_bindings sb
        JOIN nodes n ON n.id = sb.node_id
        WHERE sb.mqtt_topic = ?
        """,
        (mqtt_topic,),
    ).fetchone()
    return dict(row) if row else None


def create(node_id: int, mqtt_topic: str, unit: str = "",
           warning_threshold: float | None = None,
           failure_threshold: float | None = None,
           baseline: float | None = None) -> dict:
    warning_threshold, failure_threshold = apply_cold_start_defaults(
        warning_threshold, failure_threshold, baseline
    )
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO sensor_bindings (node_id, mqtt_topic, unit, "
        "warning_threshold, failure_threshold) VALUES (?, ?, ?, ?, ?)",
        (node_id, mqtt_topic.strip(), unit.strip(),
         warning_threshold, failure_threshold),
    )
    conn.commit()
    return get(cur.lastrowid)  # type: ignore[arg-type]


def update_thresholds(binding_id: int, warning: float | None,
                      failure: float | None) -> dict:
    conn = get_conn()
    conn.execute(
        "UPDATE sensor_bindings SET warning_threshold = ?, "
        "failure_threshold = ? WHERE id = ?",
        (warning, failure, binding_id),
    )
    conn.commit()
    # thresholds changed -> the live IF cache is still valid (cutpoints are
    # data-derived), but drop it anyway so the next evaluation refits fresh
    from app.ai import anomaly_detection
    anomaly_detection.clear_binding(binding_id)
    return get(binding_id)  # type: ignore[arg-type]


def delete(binding_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM sensor_bindings WHERE id = ?", (binding_id,))
    conn.commit()
    from app.ai import anomaly_detection
    anomaly_detection.clear_binding(binding_id)
    return cur.rowcount > 0


def topic_map() -> dict[str, dict]:
    """Full topic -> binding-with-context map (subscriber cache).

    Rebuilt on demand; cheap at demo scale. Replaces the v3 fixed
    TAG_TO_NODE mapping — any topic bound by any user resolves here.
    """
    rows = get_conn().execute(
        """
        SELECT sb.id, sb.node_id, sb.mqtt_topic, sb.unit,
               sb.warning_threshold, sb.failure_threshold,
               n.environment_id, n.display_name AS node_display_name
        FROM sensor_bindings sb
        JOIN nodes n ON n.id = sb.node_id
        """
    ).fetchall()
    return {r["mqtt_topic"]: dict(r) for r in rows}


def recent_values(binding_id: int, limit: int = 120) -> list[float]:
    rows = get_conn().execute(
        "SELECT value FROM sensor_readings WHERE binding_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (binding_id, limit),
    ).fetchall()
    return [r["value"] for r in reversed(rows)]


def record_reading(binding_id: int, value: float) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO sensor_readings (binding_id, value) VALUES (?, ?)",
        (binding_id, float(value)),
    )
    # keep the live table bounded; 2000 rows per binding is far more than
    # any demo session needs for trends and warm-up calibration
    conn.execute(
        "DELETE FROM sensor_readings WHERE binding_id = ? AND id NOT IN "
        "(SELECT id FROM sensor_readings WHERE binding_id = ? "
        "ORDER BY id DESC LIMIT 2000)",
        (binding_id, binding_id),
    )
    conn.commit()
