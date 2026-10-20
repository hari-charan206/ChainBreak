"""SQLite access layer for ChainBreak v4.

Schema per build prompt v4 Sections 4.2 and 5.2:

  users, environments, nodes, edges, sensor_bindings, sensor_readings

Frozen rules implemented here:
  - Cold-start thresholds: warning = baseline x 1.2, failure = baseline x 1.5
    (Section 12.4 confirmation). Applies at node creation and on-demand to
    any binding with a null threshold.
  - Statuses: healthy | warning | failed | offline (Section 5.2).
"""

from __future__ import annotations


import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "chainbreak.db"

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """One connection per thread; foreign keys ON; WAL for concurrent reads."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        conn.execute("PRAGMA journal_mode = WAL")
        _local.conn = conn
    return conn


# Cold-start defaults (Section 12.4 — locked)
COLD_START_WARNING_MULT = 1.2
COLD_START_FAILURE_MULT = 1.5

NODE_TYPES = ("sensor", "pump", "valve", "control_unit", "custom")
INDUSTRY_TEMPLATES = ("Water Treatment", "Manufacturing", "HVAC", "Custom")


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS environments (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name              TEXT NOT NULL,
            industry_template TEXT NOT NULL DEFAULT 'Custom',
            created_at        TEXT NOT NULL DEFAULT (datetime('now')),

            UNIQUE (user_id, name)
        );

        CREATE TABLE IF NOT EXISTS nodes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            environment_id INTEGER NOT NULL REFERENCES environments(id) ON DELETE CASCADE,
            display_name   TEXT NOT NULL,
            node_type      TEXT NOT NULL DEFAULT 'sensor',
            status         TEXT NOT NULL DEFAULT 'healthy'
                           CHECK (status IN ('healthy','warning','failed','offline')),
            position_x     REAL NOT NULL DEFAULT 0,
            position_y     REAL NOT NULL DEFAULT 0,
            created_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS edges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            environment_id  INTEGER NOT NULL REFERENCES environments(id) ON DELETE CASCADE,
            source_node_id  INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
            target_node_id  INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
            relationship_type TEXT NOT NULL DEFAULT 'feeds',
            criticality     REAL NOT NULL DEFAULT 0.5 CHECK (criticality BETWEEN 0 AND 1),
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),

            UNIQUE (environment_id, source_node_id, target_node_id)
        );

        CREATE TABLE IF NOT EXISTS sensor_bindings (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id           INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
            mqtt_topic        TEXT NOT NULL,
            unit              TEXT NOT NULL DEFAULT '',
            warning_threshold REAL,
            failure_threshold REAL,
            created_at        TEXT NOT NULL DEFAULT (datetime('now')),

            UNIQUE (mqtt_topic)
        );

        CREATE TABLE IF NOT EXISTS sensor_readings (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            binding_id INTEGER NOT NULL REFERENCES sensor_bindings(id) ON DELETE CASCADE,
            value      REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_sensor_readings_binding
            ON sensor_readings (binding_id, id);
        CREATE INDEX IF NOT EXISTS idx_nodes_env ON nodes (environment_id);
        CREATE INDEX IF NOT EXISTS idx_edges_env ON edges (environment_id);
        """
    )
    conn.commit()

#iwantto
