"""JWT + bcrypt helpers (Section 12 confirmations 1-2).

Stateless JWT in the Authorization header — fits the existing stateless
polling API. bcrypt used directly (not via passlib): passlib is unmaintained
and fragile on Python 3.13+/3.14; bcrypt 5.x works natively.
"""

from __future__ import annotations

import time
import uuid

import bcrypt
import jwt

# Demo-scale gate, not production auth (Section 4.1): a static local secret
# is acceptable for v1. Change per-install if this ever leaves localhost.
JWT_SECRET = "chainbreak-local-demo-secret"
JWT_ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"),
                         bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"),
                              password_hash.encode("ascii"))
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> int | None:
    """Return user_id for a valid token, else None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None
