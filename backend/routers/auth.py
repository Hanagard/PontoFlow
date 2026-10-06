"""Auth routes (§22): POST /auth/login, POST /auth/logout, GET /auth/me.

Session is an httpOnly cookie; no token is ever returned in a JSON body. Login failures are
rate-limited per email+IP to blunt brute force (§19).
"""

import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from lib.audit import AuditActor, write_audit
from lib.db import db
from lib.security import (
    SESSION_COOKIE,
    UserContext,
    client_ip,
    create_session_token,
    get_current_user,
    hash_password,
    session_cookie_kwargs,
    verify_password,
)
from lib.timeutil import now_utc

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_ATTEMPTS = 8
WINDOW_SECONDS = 300
_attempts: dict[str, list[float]] = defaultdict(list)


def _rate_limited(key: str) -> bool:
    now = now_utc().timestamp()
    recent = [t for t in _attempts[key] if now - t < WINDOW_SECONDS]
    _attempts[key] = recent
    return len(recent) >= MAX_ATTEMPTS


def _record_attempt(key: str) -> None:
    _attempts[key].append(now_utc().timestamp())


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class MeOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    company_id: str
    company_name: str
    timezone: str
    employee_id: str | None = None


class SignupIn(BaseModel):
    """Self-service company onboarding — creates the company plus its first admin (§42)."""

    company_name: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    timezone: str = "America/Belem"


@router.post("/login", response_model=MeOut)
async def login(payload: LoginIn, request: Request, response: Response):
    email = payload.email.lower().strip()
    key = f"{email}|{client_ip(request)}"
    if _rate_limited(key):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.")

    user = await db.users.find_one({"email": email})
    # Same generic message for unknown email and wrong password — no account enumeration.
    if not user or not verify_password(payload.password, user["password_hash"]):
        _record_attempt(key)
        if user:
            await write_audit(
                company_id=user["company_id"],
                actor=None,
                action="LOGIN_FALHA",
                resource="user",
                resource_id=user["id"],
                ip=client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    if user.get("status") != "ativo":
        raise HTTPException(status_code=403, detail="Usuário inativo. Procure o administrador.")

    _attempts.pop(key, None)
    response.set_cookie(value=create_session_token(user["id"]), **session_cookie_kwargs())
    company = await db.companies.find_one({"id": user["company_id"]}) or {}
    await write_audit(
        company_id=user["company_id"],
        actor=AuditActor(id=user["id"], name=user["name"], role=user["role"]),
        action="LOGIN",
        resource="user",
        resource_id=user["id"],
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return MeOut(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        company_id=user["company_id"],
        company_name=company.get("name", ""),
        timezone=company.get("timezone", "America/Belem"),
        employee_id=user.get("employee_id"),
    )


@router.post("/signup", response_model=MeOut)
async def signup(payload: SignupIn, request: Request, response: Response):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    company_id = uuid.uuid4().hex
    await db.companies.insert_one(
        {
            "id": company_id,
            "name": payload.company_name.strip(),
            "cnpj": None,
            "timezone": payload.timezone,
            "status": "ativa",
            "created_at": now_utc(),
        }
    )
    user_id = uuid.uuid4().hex
    await db.users.insert_one(
        {
            "id": user_id,
            "company_id": company_id,
            "name": payload.name.strip(),
            "email": email,
            "password_hash": hash_password(payload.password),
            "role": "admin",
            "employee_id": None,
            "status": "ativo",
            "created_at": now_utc(),
        }
    )
    actor = AuditActor(id=user_id, name=payload.name, role="admin")
    await write_audit(company_id=company_id, actor=actor, action="EMPRESA_CRIADA", resource="company", resource_id=company_id, after={"name": payload.company_name}, ip=client_ip(request))
    await write_audit(company_id=company_id, actor=actor, action="USUARIO_CRIADO", resource="user", resource_id=user_id, after={"email": email, "role": "admin"}, ip=client_ip(request))
    response.set_cookie(value=create_session_token(user_id), **session_cookie_kwargs())
    return MeOut(
        id=user_id,
        name=payload.name.strip(),
        email=email,
        role="admin",
        company_id=company_id,
        company_name=payload.company_name.strip(),
        timezone=payload.timezone,
        employee_id=None,
    )


@router.get("/me", response_model=MeOut)
async def me(user: UserContext = Depends(get_current_user)):
    company = await db.companies.find_one({"id": user.company_id}) or {}
    return MeOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        company_id=user.company_id,
        company_name=company.get("name", ""),
        timezone=company.get("timezone", "America/Belem"),
        employee_id=user.employee_id,
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    token_user = None
    try:
        token_user = await get_current_user(request)
    except HTTPException:
        pass
    response.delete_cookie(SESSION_COOKIE, path="/")
    if token_user:
        await write_audit(
            company_id=token_user.company_id,
            actor=AuditActor(id=token_user.id, name=token_user.name, role=token_user.role),
            action="LOGOUT",
            resource="user",
            resource_id=token_user.id,
            ip=client_ip(request),
        )
    return {"ok": True}
