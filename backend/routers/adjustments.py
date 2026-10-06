"""Adjustment requests (§12) — employee asks, gestor/admin decides, ponto changes only on approval."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request

from lib.audit import AuditActor, write_audit
from lib.calc import TYPE_LABELS
from lib.db import db
from lib.security import UserContext, client_ip, get_current_user, require_roles
from lib.tenancy import company_tz, resolve_employee
from lib.timeutil import day_bounds_utc, hhmm_of, local_dt, now_utc
from lib.validators import hhmm_valid
from models.records import AdjustmentCreate, AdjustmentDecision, AdjustmentOut

router = APIRouter(prefix="/adjustment-requests", tags=["adjustments"])
APPROVERS = ("super_admin", "admin", "gestor")


def _out(doc: dict) -> AdjustmentOut:
    return AdjustmentOut(
        id=doc["id"],
        company_id=doc["company_id"],
        employee_id=doc["employee_id"],
        employee_name=doc.get("employee_name", ""),
        target_date=doc["target_date"],
        type=doc["type"],
        type_label=TYPE_LABELS[doc["type"]],
        requested_time=doc["requested_time"],
        previous_time=doc.get("previous_time"),
        reason=doc["reason"],
        status=doc["status"],
        decided_by_name=doc.get("decided_by_name"),
        decision_note=doc.get("decision_note"),
        decided_at=doc.get("decided_at"),
        created_at=doc.get("created_at") or now_utc(),
    )


@router.get("", response_model=list[AdjustmentOut])
async def list_requests(status: str | None = None, user: UserContext = Depends(get_current_user)):
    query: dict = {"company_id": user.company_id}
    if user.role == "funcionario":
        employee = await resolve_employee(user, None)
        query["employee_id"] = employee["id"]
    if status:
        query["status"] = status
    docs = await db.time_adjustment_requests.find(query).sort("created_at", -1).to_list(300)
    return [_out(d) for d in docs]


@router.post("", response_model=AdjustmentOut, status_code=201)
async def create_request(payload: AdjustmentCreate, request: Request, user: UserContext = Depends(get_current_user)):
    employee = await resolve_employee(user, None)
    tz = await company_tz(user.company_id)
    if not hhmm_valid(payload.requested_time):
        raise HTTPException(status_code=400, detail="Horário inválido. Use o formato HH:MM.")
    try:
        target = date.fromisoformat(payload.target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida. Use o formato AAAA-MM-DD.")
    from lib.timeutil import local_today

    if target > local_today(tz):
        raise HTTPException(status_code=400, detail="Não é possível solicitar ajuste para uma data futura.")

    start, end = day_bounds_utc(target, tz)
    existing = await db.time_records.find_one(
        {"company_id": user.company_id, "employee_id": employee["id"], "type": payload.type, "timestamp": {"$gte": start, "$lt": end}}
    )
    duplicate = await db.time_adjustment_requests.find_one(
        {"company_id": user.company_id, "employee_id": employee["id"], "target_date": payload.target_date, "type": payload.type, "status": "pendente"}
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Já existe uma solicitação pendente para este registro.")

    doc = {
        "id": uuid.uuid4().hex,
        "company_id": user.company_id,
        "employee_id": employee["id"],
        "employee_name": employee["name"],
        "target_date": payload.target_date,
        "type": payload.type,
        "kind": "correcao",
        "requested_time": payload.requested_time,
        "previous_time": hhmm_of(existing["timestamp"], tz) if existing else None,
        "record_id": existing["id"] if existing else None,
        "reason": payload.reason.strip(),
        "status": "pendente",
        "created_by": user.id,
        "created_at": now_utc(),
    }
    await db.time_adjustment_requests.insert_one(dict(doc))
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="SOLICITACAO_CRIADA",
        resource="time_adjustment_request",
        resource_id=doc["id"],
        after={"date": doc["target_date"], "type": doc["type"], "requested_time": doc["requested_time"]},
        ip=client_ip(request),
    )
    return _out(doc)


@router.patch("/{request_id}", response_model=AdjustmentOut)
async def decide_request(
    request_id: str, payload: AdjustmentDecision, request: Request, user: UserContext = Depends(require_roles(*APPROVERS))
):
    doc = await db.time_adjustment_requests.find_one({"id": request_id, "company_id": user.company_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")
    if doc["status"] != "pendente":
        raise HTTPException(status_code=400, detail="Esta solicitação já foi decidida.")

    tz = await company_tz(user.company_id)
    changes = {
        "status": payload.decision,
        "decided_by": user.id,
        "decided_by_name": user.name,
        "decision_note": payload.note,
        "decided_at": now_utc(),
    }

    if payload.decision == "aprovada":
        target = date.fromisoformat(doc["target_date"])
        official = local_dt(target, doc["requested_time"], tz)
        if doc.get("record_id"):
            previous = await db.time_records.find_one({"id": doc["record_id"], "company_id": user.company_id})
            await db.time_records.update_one(
                {"id": doc["record_id"], "company_id": user.company_id},
                {"$set": {"timestamp": official, "adjusted": True, "adjusted_at": now_utc(), "adjusted_by": user.id}},
            )
            await write_audit(
                company_id=user.company_id,
                actor=AuditActor(id=user.id, name=user.name, role=user.role),
                action="PONTO_CORRIGIDO",
                resource="time_record",
                resource_id=doc["record_id"],
                before={"hhmm": hhmm_of(previous["timestamp"], tz) if previous else None},
                after={"hhmm": doc["requested_time"]},
                ip=client_ip(request),
            )
        else:
            record_id = uuid.uuid4().hex
            await db.time_records.insert_one(
                {
                    "id": record_id,
                    "company_id": user.company_id,
                    "employee_id": doc["employee_id"],
                    "work_date": target.isoformat(),
                    "type": doc["type"],
                    "timestamp": official,
                    "timezone": tz,
                    "origin": "ajuste",
                    "device": None,
                    "ip": None,
                    "observacao": f"Ajuste aprovado por {user.name}",
                    "status": "valido",
                    "adjusted": True,
                    "created_at": now_utc(),
                }
            )
            changes["record_id"] = record_id
            await write_audit(
                company_id=user.company_id,
                actor=AuditActor(id=user.id, name=user.name, role=user.role),
                action="PONTO_CORRIGIDO",
                resource="time_record",
                resource_id=record_id,
                before=None,
                after={"type": doc["type"], "hhmm": doc["requested_time"], "date": doc["target_date"]},
                ip=client_ip(request),
            )

    await db.time_adjustment_requests.update_one({"id": request_id, "company_id": user.company_id}, {"$set": changes})
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="SOLICITACAO_APROVADA" if payload.decision == "aprovada" else "SOLICITACAO_REJEITADA",
        resource="time_adjustment_request",
        resource_id=request_id,
        before={"status": "pendente"},
        after={"status": payload.decision, "note": payload.note},
        ip=client_ip(request),
    )
    updated = await db.time_adjustment_requests.find_one({"id": request_id, "company_id": user.company_id})
    return _out(updated or {**doc, **changes})


@router.post("/{request_id}/cancel", response_model=AdjustmentOut)
async def cancel_request(request_id: str, request: Request, user: UserContext = Depends(get_current_user)):
    doc = await db.time_adjustment_requests.find_one({"id": request_id, "company_id": user.company_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")
    if user.role == "funcionario" and doc["employee_id"] != user.employee_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para esta ação.")
    if doc["status"] != "pendente":
        raise HTTPException(status_code=400, detail="Apenas solicitações pendentes podem ser canceladas.")
    await db.time_adjustment_requests.update_one(
        {"id": request_id, "company_id": user.company_id}, {"$set": {"status": "cancelada", "decided_at": now_utc()}}
    )
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="SOLICITACAO_CANCELADA",
        resource="time_adjustment_request",
        resource_id=request_id,
        before={"status": "pendente"},
        after={"status": "cancelada"},
        ip=client_ip(request),
    )
    updated = await db.time_adjustment_requests.find_one({"id": request_id, "company_id": user.company_id})
    return _out(updated or doc)
