"""Calendário da empresa: feriados (§ feriados) + escalas por período (§13)."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request

from lib.audit import AuditActor, write_audit
from lib.calc import WEEKDAYS_PT
from lib.db import db
from lib.holidays import national_holidays
from lib.security import UserContext, client_ip, get_current_user, require_roles
from lib.timeutil import local_today, now_utc
from lib.tenancy import company_tz
from models.calendar import AssignmentCreate, AssignmentOut, HolidayCreate, HolidayImportOut, HolidayOut

router = APIRouter(tags=["calendar"])
ADMINS = ("super_admin", "admin")
MANAGERS = ("super_admin", "admin", "gestor")


def _holiday_out(doc: dict) -> HolidayOut:
    return HolidayOut(
        id=doc["id"],
        company_id=doc["company_id"],
        date=doc["date"],
        name=doc["name"],
        kind=doc["kind"],
        weekday=WEEKDAYS_PT[date.fromisoformat(doc["date"]).weekday()],
        created_at=doc.get("created_at") or now_utc(),
    )


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida. Use o formato AAAA-MM-DD.")


# --------------------------------------------------------------------------- feriados


@router.get("/holidays", response_model=list[HolidayOut])
async def list_holidays(year: int | None = None, user: UserContext = Depends(get_current_user)):
    query: dict = {"company_id": user.company_id}
    if year:
        query["date"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}
    docs = await db.holidays.find(query).sort("date", 1).to_list(500)
    return [_holiday_out(d) for d in docs]


@router.post("/holidays", response_model=HolidayOut, status_code=201)
async def create_holiday(payload: HolidayCreate, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    day = _parse_day(payload.date)
    if await db.holidays.find_one({"company_id": user.company_id, "date": payload.date}):
        raise HTTPException(status_code=409, detail="Já existe um feriado cadastrado nesta data.")
    doc = {
        "id": uuid.uuid4().hex,
        "company_id": user.company_id,
        "date": day.isoformat(),
        "name": payload.name.strip(),
        "kind": payload.kind,
        "created_at": now_utc(),
    }
    await db.holidays.insert_one(dict(doc))
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="FERIADO_CRIADO",
        resource="holiday",
        resource_id=doc["id"],
        after={"date": doc["date"], "name": doc["name"], "kind": doc["kind"]},
        ip=client_ip(request),
    )
    return _holiday_out(doc)


@router.post("/holidays/import-national", response_model=HolidayImportOut)
async def import_national(year: int | None = None, request: Request = None, user: UserContext = Depends(require_roles(*ADMINS))):  # type: ignore[assignment]
    """Pré-carrega os feriados nacionais do ano, sem sobrescrever datas já cadastradas."""
    tz = await company_tz(user.company_id)
    target_year = year or local_today(tz).year
    if not 2000 <= target_year <= 2100:
        raise HTTPException(status_code=400, detail="Ano inválido.")

    existing = {
        d["date"]
        for d in await db.holidays.find(
            {"company_id": user.company_id, "date": {"$gte": f"{target_year}-01-01", "$lte": f"{target_year}-12-31"}}
        ).to_list(500)
    }
    new_docs = [
        {
            "id": uuid.uuid4().hex,
            "company_id": user.company_id,
            "date": h["date"],
            "name": h["name"],
            "kind": h["kind"],
            "created_at": now_utc(),
        }
        for h in national_holidays(target_year)
        if h["date"] not in existing
    ]
    if new_docs:
        await db.holidays.insert_many([dict(d) for d in new_docs])
        await write_audit(
            company_id=user.company_id,
            actor=AuditActor(id=user.id, name=user.name, role=user.role),
            action="FERIADOS_IMPORTADOS",
            resource="holiday",
            resource_id=str(target_year),
            after={"year": target_year, "imported": len(new_docs)},
            ip=client_ip(request) if request else None,
        )
    all_docs = await db.holidays.find(
        {"company_id": user.company_id, "date": {"$gte": f"{target_year}-01-01", "$lte": f"{target_year}-12-31"}}
    ).sort("date", 1).to_list(500)
    return HolidayImportOut(
        year=target_year,
        imported=len(new_docs),
        skipped=len(existing),
        holidays=[_holiday_out(d) for d in all_docs],
    )


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: str, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    doc = await db.holidays.find_one({"id": holiday_id, "company_id": user.company_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Feriado não encontrado.")
    await db.holidays.delete_one({"id": holiday_id, "company_id": user.company_id})
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="FERIADO_REMOVIDO",
        resource="holiday",
        resource_id=holiday_id,
        before={"date": doc["date"], "name": doc["name"]},
        ip=client_ip(request),
    )
    return {"ok": True}


# --------------------------------------------------------------------------- escalas


async def _assignment_out(doc: dict, tz: str) -> AssignmentOut:
    employee = await db.employees.find_one({"id": doc["employee_id"], "company_id": doc["company_id"]})
    schedule = await db.work_schedules.find_one({"id": doc["schedule_id"], "company_id": doc["company_id"]})
    today = local_today(tz).isoformat()
    return AssignmentOut(
        id=doc["id"],
        company_id=doc["company_id"],
        employee_id=doc["employee_id"],
        employee_name=(employee or {}).get("name", "—"),
        schedule_id=doc["schedule_id"],
        schedule_name=(schedule or {}).get("name", "—"),
        start_date=doc["start_date"],
        end_date=doc.get("end_date"),
        note=doc.get("note"),
        active=doc["start_date"] <= today and (not doc.get("end_date") or doc["end_date"] >= today),
        created_at=doc.get("created_at") or now_utc(),
    )


@router.get("/schedule-assignments", response_model=list[AssignmentOut])
async def list_assignments(employee_id: str | None = None, user: UserContext = Depends(require_roles(*MANAGERS))):
    query: dict = {"company_id": user.company_id}
    if employee_id:
        query["employee_id"] = employee_id
    docs = await db.schedule_assignments.find(query).sort("start_date", -1).to_list(300)
    tz = await company_tz(user.company_id)
    return [await _assignment_out(d, tz) for d in docs]


@router.post("/schedule-assignments", response_model=AssignmentOut, status_code=201)
async def create_assignment(payload: AssignmentCreate, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    start = _parse_day(payload.start_date)
    end = _parse_day(payload.end_date) if payload.end_date else None
    if end and end < start:
        raise HTTPException(status_code=400, detail="A data final não pode ser menor que a inicial.")
    if not await db.employees.find_one({"id": payload.employee_id, "company_id": user.company_id}):
        raise HTTPException(status_code=400, detail="Funcionário inválido.")
    if not await db.work_schedules.find_one({"id": payload.schedule_id, "company_id": user.company_id}):
        raise HTTPException(status_code=400, detail="Jornada inválida.")

    doc = {
        "id": uuid.uuid4().hex,
        "company_id": user.company_id,
        "employee_id": payload.employee_id,
        "schedule_id": payload.schedule_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat() if end else None,
        "note": payload.note,
        "created_by": user.id,
        "created_at": now_utc(),
    }
    await db.schedule_assignments.insert_one(dict(doc))
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="ESCALA_ATRIBUIDA",
        resource="schedule_assignment",
        resource_id=doc["id"],
        after={"employee_id": doc["employee_id"], "schedule_id": doc["schedule_id"], "start_date": doc["start_date"], "end_date": doc["end_date"]},
        ip=client_ip(request),
    )
    return await _assignment_out(doc, await company_tz(user.company_id))


@router.delete("/schedule-assignments/{assignment_id}")
async def delete_assignment(assignment_id: str, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    doc = await db.schedule_assignments.find_one({"id": assignment_id, "company_id": user.company_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Escala não encontrada.")
    await db.schedule_assignments.delete_one({"id": assignment_id, "company_id": user.company_id})
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="ESCALA_REMOVIDA",
        resource="schedule_assignment",
        resource_id=assignment_id,
        before={"employee_id": doc["employee_id"], "schedule_id": doc["schedule_id"]},
        ip=client_ip(request),
    )
    return {"ok": True}
