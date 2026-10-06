"""Employee CRUD (§7) — admin/gestor read, admin writes. Always company-scoped."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from lib.audit import AuditActor, write_audit
from lib.db import db
from lib.security import UserContext, client_ip, get_current_user, hash_password, require_roles
from lib.timeutil import now_utc
from lib.validators import cpf_digits, cpf_masked, cpf_valid
from models.employees import EmployeeCreate, EmployeeOut, EmployeeUpdate

router = APIRouter(prefix="/employees", tags=["employees"])

MANAGERS = ("super_admin", "admin", "gestor")
ADMINS = ("super_admin", "admin")


async def _out(doc: dict) -> EmployeeOut:
    schedule_name = None
    if doc.get("schedule_id"):
        schedule = await db.work_schedules.find_one({"id": doc["schedule_id"]})
        schedule_name = (schedule or {}).get("name")
    return EmployeeOut(
        id=doc["id"],
        company_id=doc["company_id"],
        user_id=doc.get("user_id"),
        name=doc["name"],
        cpf=cpf_masked(doc.get("cpf", "")),  # full CPF never leaves the backend (§7/§20)
        cpf_masked=cpf_masked(doc.get("cpf", "")),
        matricula=doc.get("matricula", ""),
        email=doc.get("email"),
        phone=doc.get("phone"),
        cargo=doc.get("cargo"),
        department=doc.get("department"),
        schedule_id=doc.get("schedule_id"),
        schedule_name=schedule_name,
        status=doc.get("status", "ativo"),
        hired_at=doc.get("hired_at"),
        created_at=doc.get("created_at") or now_utc(),
    )


@router.get("", response_model=list[EmployeeOut])
async def list_employees(
    status: str | None = None,
    department: str | None = None,
    q: str | None = None,
    user: UserContext = Depends(require_roles(*MANAGERS)),
):
    query: dict = {"company_id": user.company_id}
    if status:
        query["status"] = status
    if department:
        query["department"] = department
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"matricula": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.employees.find(query).sort("name", 1).to_list(500)
    return [await _out(d) for d in docs]


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(employee_id: str, user: UserContext = Depends(get_current_user)):
    # A funcionario may only read their own record.
    if user.role == "funcionario" and user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para esta ação.")
    doc = await db.employees.find_one({"id": employee_id, "company_id": user.company_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    return await _out(doc)


@router.post("", response_model=EmployeeOut, status_code=201)
async def create_employee(payload: EmployeeCreate, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    digits = cpf_digits(payload.cpf)
    if not cpf_valid(digits):
        raise HTTPException(status_code=400, detail="CPF inválido.")
    if await db.employees.find_one({"company_id": user.company_id, "cpf": digits}):
        raise HTTPException(status_code=409, detail="Já existe um funcionário com este CPF.")
    if await db.employees.find_one({"company_id": user.company_id, "matricula": payload.matricula.strip()}):
        raise HTTPException(status_code=409, detail="Já existe um funcionário com esta matrícula.")
    if payload.schedule_id and not await db.work_schedules.find_one(
        {"id": payload.schedule_id, "company_id": user.company_id}
    ):
        raise HTTPException(status_code=400, detail="Jornada inválida.")

    employee_id = uuid.uuid4().hex
    doc = {
        "id": employee_id,
        "company_id": user.company_id,
        "user_id": None,
        "name": payload.name.strip(),
        "cpf": digits,
        "matricula": payload.matricula.strip(),
        "email": (payload.email or "").lower().strip() or None,
        "phone": payload.phone,
        "cargo": payload.cargo,
        "department": payload.department,
        "schedule_id": payload.schedule_id,
        "status": payload.status,
        "hired_at": payload.hired_at,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }

    if payload.create_login:
        if not doc["email"] or not payload.login_password or len(payload.login_password) < 6:
            raise HTTPException(status_code=400, detail="Para criar acesso informe e-mail e senha com no mínimo 6 caracteres.")
        if await db.users.find_one({"email": doc["email"]}):
            raise HTTPException(status_code=409, detail="Este e-mail já possui acesso ao sistema.")
        user_id = uuid.uuid4().hex
        await db.users.insert_one(
            {
                "id": user_id,
                "company_id": user.company_id,
                "name": doc["name"],
                "email": doc["email"],
                "password_hash": hash_password(payload.login_password),
                "role": "funcionario",
                "employee_id": employee_id,
                "status": "ativo",
                "created_at": now_utc(),
            }
        )
        doc["user_id"] = user_id

    await db.employees.insert_one(dict(doc))
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="FUNCIONARIO_CRIADO",
        resource="employee",
        resource_id=employee_id,
        after={"name": doc["name"], "matricula": doc["matricula"], "cpf": cpf_masked(digits)},
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return await _out(doc)


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: str, payload: EmployeeUpdate, request: Request, user: UserContext = Depends(require_roles(*ADMINS))
):
    doc = await db.employees.find_one({"id": employee_id, "company_id": user.company_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if changes.get("schedule_id") and not await db.work_schedules.find_one(
        {"id": changes["schedule_id"], "company_id": user.company_id}
    ):
        raise HTTPException(status_code=400, detail="Jornada inválida.")
    if not changes:
        return await _out(doc)
    before = {k: doc.get(k) for k in changes}
    changes["updated_at"] = now_utc()
    await db.employees.update_one({"id": employee_id, "company_id": user.company_id}, {"$set": changes})
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="FUNCIONARIO_ATUALIZADO",
        resource="employee",
        resource_id=employee_id,
        before=before,
        after={k: v for k, v in changes.items() if k != "updated_at"},
        ip=client_ip(request),
    )
    updated = await db.employees.find_one({"id": employee_id, "company_id": user.company_id})
    return await _out(updated or doc)
