"""Auth API (Section 9.1): signup / login / logout — JWT, deliberately
minimal per Section 4.1. No OAuth, roles, email verification, or password
reset in v1.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.models import users
from app.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


@router.post("/signup", status_code=201)
def signup(req: AuthRequest):
    if users.get_by_email(req.email) is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    user = users.create(req.email, hash_password(req.password))
    return _session(user)


@router.post("/login")
def login(req: AuthRequest):
    user = users.get_by_email(req.email)
    if user is None or not verify_password(req.password,
                                           user["password_hash"]):
        # Same message for unknown email and wrong password (no user probing)
        raise HTTPException(status_code=401, detail="invalid email or password")
    return _session(user)


@router.post("/logout")
def logout():
    # Stateless JWT: the client discards the token. Kept as an endpoint for
    # API symmetry with Section 9.1.
    return {"ok": True}


def _session(user: dict) -> dict:
    return {
        "token": create_token(user["id"]),
        "user": {"id": user["id"], "email": user["email"]}, #credentials
    }
