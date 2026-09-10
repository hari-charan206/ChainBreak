"""users — data access (build prompt v4 Section 4.2)."""

from __future__ import annotations

from app.db import get_conn


def get_by_email(email: str) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM users WHERE email = ?", (email.strip(),)
    ).fetchone()
    return dict(row) if row else None


def get_by_id(user_id: int) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def create(email: str, password_hash: str) -> dict:
    cur = get_conn().execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email.strip(), password_hash),
    )
    get_conn().commit()
    return get_by_id(cur.lastrowid)  # type: ignore[arg-type]
