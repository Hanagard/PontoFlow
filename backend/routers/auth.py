"""Authentication routes. Signup is opt-in; login/signup limits are shared via MongoDB."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from lib.audit import AuditActor, write_audit
from lib.db import db
from lib.rate_limit import clear_rate_limit, is_rate_limited
from lib.security import (
    SESSION_COOKIE, UserContext, client_ip, create_session_token, get_current_user,
    hash_password, session_cookie_kwargs, verify_password,
)
from lib.timeutil import now_utc

router = APIRouter(prefix="/auth", tags=["auth"])
LOGIN_LIMIT = 8
LOGIN_WINDOW = 300
SIGNUP_LIMIT = 3
SIGNUP_WINDOW = 3600


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
    company_name: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)
    timezone: str = "America/Belem"


def _signup_enabled() -> bool:
    return os.environ.get("ALLOW_PUBLIC_SIGNUP", "false").strip().lower() == "true"


@router.post("/login", response_model=MeOut)
async def login(payload: LoginIn, request: Request, response: Response):
    email = payload.email.lower().strip()
    ip = client_ip(request) or "unknown"
    identity = f"{email}|{ip}"
    if await is_rate_limited("login", identity, LOGIN_LIMIT, LOGIN_WINDOW):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        if user:
            await write_audit(
                company_id=user["company_id"], actor=None, action="LOGIN_FALHA",
                resource="user", resource_id=user["id"], ip=ip,
                user_agent=request.headers.get("user-agent"),
            )
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    if user.get("status") != "ativo":
        raise HTTPException(status_code=403, detail="Usuário inativo. Procure o administrador.")

    await clear_rate_limit("login", identity, LOGIN_WINDOW)
    response.set_cookie(value=create_session_token(user["id"]), **session_cookie_kwargs())
    company = await db.companies.find_one({"id": user["company_id"]}) or {}
    await write_audit(
        company_id=user["company_id"],
        actor=AuditActor(id=user["id"], name=user["name"], role=user["role"]),
        action="LOGIN", resource="user", resource_id=user["id"], ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    return MeOut(
        id=user["id"], name=user["name"], email=user["email"], role=user["role"],
        company_id=user["company_id"], company_name=company.get("name", ""),
        timezone=company.get("timezone", "America/Belem"), employee_id=user.get("employee_id"),
    )


@router.post("/signup", response_model=MeOut)
async def signup(payload: SignupIn, request: Request, response: Response):
    if not _signup_enabled():
        raise HTTPException(status_code=403, detail="Cadastro público desabilitado. Solicite acesso ao administrador.")
    ip = client_ip(request) or "unknown"
    if await is_rate_limited("signup", ip, SIGNUP_LIMIT, SIGNUP_WINDOW):
        raise HTTPException(status_code=429, detail="Limite de cadastros atingido. Tente novamente mais tarde.")

    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")

    company_id = uuid.uuid4().hex
    user_id = uuid.uuid4().hex
    company_name = payload.company_name.strip()
    name = payload.name.strip()
    # Insert the company and admin; compensate company creation if user insertion fails.
    await db.companies.insert_one({
        "id": company_id, "name": company_name, "cnpj": None,
        "timezone": payload.timezone, "status": "ativa", "created_at": now_utc(),
    })
    try:
        await db.users.insert_one({
            "id": user_id, "company_id": company_id, "name": name, "email": email,
            "password_hash": hash_password(payload.password), "role": "admin",
            "employee_id": None, "status": "ativo", "created_at": now_utc(),
        })
    except Exception:
        await db.companies.delete_one({"id": company_id})
        raise

    actor = AuditActor(id=user_id, name=name, role="admin")
    await write_audit(company_id=company_id, actor=actor, action="EMPRESA_CRIADA",
                      resource="company", resource_id=company_id, after={"name": company_name}, ip=ip)
    await write_audit(company_id=company_id, actor=actor, action="USUARIO_CRIADO",
                      resource="user", resource_id=user_id, after={"email": email, "role": "admin"}, ip=ip)
    response.set_cookie(value=create_session_token(user_id), **session_cookie_kwargs())
    return MeOut(id=user_id, name=name, email=email, role="admin", company_id=company_id,
                 company_name=company_name, timezone=payload.timezone, employee_id=None)


@router.get("/me", response_model=MeOut)
async def me(user: UserContext = Depends(get_current_user)):
    company = await db.companies.find_one({"id": user.company_id}) or {}
    return MeOut(
        id=user.id, name=user.name, email=user.email, role=user.role,
        company_id=user.company_id, company_name=company.get("name", ""),
        timezone=company.get("timezone", "America/Belem"), employee_id=user.employee_id,
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
            action="LOGOUT", resource="user", resource_id=token_user.id,
            ip=client_ip(request),
        )
    return {"ok": True}
