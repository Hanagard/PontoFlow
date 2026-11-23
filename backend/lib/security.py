"""Session auth primitives: bcrypt password hashing + signed httpOnly session cookie."""

import ipaddress
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
    async def dependency(user: UserContext = Depends(get_current_user)) -> UserContext:
        if roles and user.role not in roles:
            raise HTTPException(status_code=403, detail="Você não tem permissão para esta ação.")
        return user
    return dependency


def _trusted_proxy_networks():
    configured = os.environ.get("TRUSTED_PROXY_IPS", "")
    networks = []
    for value in configured.split(","):
        value = value.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            logger.error("Ignoring invalid TRUSTED_PROXY_IPS entry: %s", value)
    return networks


def _is_trusted_proxy(address: str, networks) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return any(ip in network for network in networks)
    except ValueError:
        return False


def client_ip(request: Request) -> str:
    """Trust X-Forwarded-For only when the immediate peer is an explicitly trusted proxy.

    The proxy must overwrite or append X-Forwarded-For safely. Walking from right to left
    skips trusted proxy hops and selects the first untrusted address.
    """
    peer = request.client.host if request.client else ""
    networks = _trusted_proxy_networks()
    if not peer or not _is_trusted_proxy(peer, networks):
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    chain = [part.strip() for part in forwarded.split(",") if part.strip()]
    for address in reversed(chain):
        if not _is_trusted_proxy(address, networks):
            try:
                return str(ipaddress.ip_address(address))
            except ValueError:
                break
    return peer
