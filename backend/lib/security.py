"""Session auth primitives: bcrypt password hashing + signed httpOnly session cookie (JWT HS256).

- Passwords are stored ONLY as bcrypt hashes (never returned by any endpoint).
- The session is an httpOnly cookie ("pf_session") set by POST /auth/login and cleared by
  POST /auth/logout; nothing token-shaped ever reaches the frontend.
- Authorization is enforced server-side via get_current_user / require_roles dependencies.
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext
from pydantic import BaseModel

from lib.db import db

logger = logging.getLogger(__name__)

SESSION_COOKIE = "pf_session"
SESSION_TTL_DAYS = 7
ALGORITHM = "HS256"

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)


def _secret() -> str:
    value = os.environ.get("SESSION_SECRET")
    production = os.environ.get("APP_ENV", "development").strip().lower() == "production"
    if value:
        if production and len(value) < 64:
            raise RuntimeError("SESSION_SECRET must contain at least 64 characters in production.")
        return value
    if production:
        raise RuntimeError("SESSION_SECRET is required in production.")
    logger.warning("SESSION_SECRET not set - using an ephemeral dev secret; sessions reset on restart")
    return secrets.token_hex(32)


def create_session_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def session_cookie_kwargs() -> dict:
    # Development may run over HTTP; production MUST use HTTPS.
    production = os.environ.get("APP_ENV", "development").strip().lower() == "production"
    return {
        "key": SESSION_COOKIE,
        "httponly": True,
        "samesite": "lax",
        "secure": production,
        "max_age": SESSION_TTL_DAYS * 24 * 3600,
        "path": "/",
    }


class UserContext(BaseModel):
    id: str
    company_id: str
    name: str
    email: str
    role: str
    employee_id: str | None = None


async def get_current_user(request: Request) -> UserContext:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    user = await db.users.find_one({"id": payload.get("sub"), "status": "ativo"})
    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    return UserContext(
        id=user["id"],
        company_id=user["company_id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        employee_id=user.get("employee_id"),
    )


def require_roles(*roles: str):
    """Dependency factory: 403 unless the session user's role is in `roles`."""

    async def dependency(user: UserContext = Depends(get_current_user)) -> UserContext:
        if roles and user.role not in roles:
            raise HTTPException(status_code=403, detail="Você não tem permissão para esta ação.")
        return user

    return dependency


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""
