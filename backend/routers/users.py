"""User management (§6) — admin creates logins and changes roles; audited."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from lib.audit import AuditActor, write_audit
from lib.db import db
from lib.security import UserContext, client_ip, hash_password, require_roles
from lib.timeutil import now_utc
from models.users import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
ADMINS = ("super_admin", "admin")


def _out(doc: dict) -> UserOut:
    return UserOut(
        id=doc["id"],
        name=doc["name"],
        email=doc["email"],
        role=doc["role"],
        company_id=doc["company_id"],
        employee_id=doc.get("employee_id"),
        status=doc.get("status", "ativo"),
        created_at=doc.get("created_at") or now_utc(),
    )


@router.get("", response_model=list[UserOut])
async def list_users(user: UserContext = Depends(require_roles(*ADMINS))):
    docs = await db.users.find({"company_id": user.company_id}).sort("name", 1).to_list(300)
    return [_out(d) for d in docs]


@router.post("", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    if payload.role == "super_admin" and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Apenas o super administrador pode criar outro super administrador.")
    if payload.employee_id and not await db.employees.find_one({"id": payload.employee_id, "company_id": user.company_id}):
        raise HTTPException(status_code=400, detail="Funcionário inválido.")

    doc = {
        "id": uuid.uuid4().hex,
        "company_id": user.company_id,
        "name": payload.name.strip(),
        "email": email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "employee_id": payload.employee_id,
        "status": "ativo",
        "created_at": now_utc(),
    }
    await db.users.insert_one(dict(doc))
    if payload.employee_id:
        await db.employees.update_one(
            {"id": payload.employee_id, "company_id": user.company_id}, {"$set": {"user_id": doc["id"]}}
        )
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="USUARIO_CRIADO",
        resource="user",
        resource_id=doc["id"],
        after={"email": email, "role": payload.role},
        ip=client_ip(request),
    )
    return _out(doc)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: UserUpdate, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    doc = await db.users.find_one({"id": user_id, "company_id": user.company_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if doc["id"] == user.id and payload.status == "inativo":
        raise HTTPException(status_code=400, detail="Você não pode desativar o seu próprio usuário.")
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not changes:
        return _out(doc)
    before = {k: doc.get(k) for k in changes}
    await db.users.update_one({"id": user_id, "company_id": user.company_id}, {"$set": changes})
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="PERMISSAO_ALTERADA",
        resource="user",
        resource_id=user_id,
        before=before,
        after=changes,
        ip=client_ip(request),
    )
    return _out({**doc, **changes})
