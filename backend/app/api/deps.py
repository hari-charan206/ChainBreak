"""Shared API dependencies: JWT auth + environment ownership scoping.

Section 4.3: reject any dashboard/environment call without a valid token,
and scope everything by "is this environment's user_id the requester".
No fine-grained permissions in v1.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.models import environments as envs_model
from app.models import users
from app.security import decode_token


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_token(token)
    user = users.get_by_id(user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return user


def get_owned_environment(environment_id: int,
                          user: dict = Depends(get_current_user)) -> dict:
    env = envs_model.get(environment_id)
    if env is None:
        raise HTTPException(status_code=404, detail="environment not found")
    if env["user_id"] != user["id"]:
        # 404, not 403: do not reveal other users' environments exist
        raise HTTPException(status_code=404, detail="environment not found")
    return env
