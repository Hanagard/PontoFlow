"""Work schedule (jornada) routes (§13) — jornada fixa e escalas rotativas."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request

from lib.audit import AuditActor, write_audit
from lib.calc import CYCLE_PRESETS, SCHEDULE_KINDS, expected_minutes
from lib.db import db
from lib.security import UserContext, client_ip, get_current_user, require_roles
from lib.timeutil import hhmm, now_utc
from lib.validators import hhmm_valid
from models.schedules import ScheduleCreate, ScheduleOut

router = APIRouter(prefix="/schedules", tags=["schedules"])
ADMINS = ("super_admin", "admin")


def _out(doc: dict) -> ScheduleOut:
    return ScheduleOut(
        id=doc["id"],
        company_id=doc["company_id"],
        name=doc["name"],
        entrada=doc["entrada"],
        inicio_intervalo=doc["inicio_intervalo"],
        fim_intervalo=doc["fim_intervalo"],
        saida=doc["saida"],
        tolerance_minutes=doc.get("tolerance_minutes", 10),
        work_days=doc.get("work_days", [0, 1, 2, 3, 4]),
        kind=doc.get("kind", "fixa"),
        cycle_anchor=doc.get("cycle_anchor"),
        cycle_on_days=doc.get("cycle_on_days"),
        cycle_off_days=doc.get("cycle_off_days"),
        expected_hhmm=hhmm(expected_minutes(doc)),
        created_at=doc.get("created_at") or now_utc(),
    )


@router.get("", response_model=list[ScheduleOut])
async def list_schedules(user: UserContext = Depends(get_current_user)):
    docs = await db.work_schedules.find({"company_id": user.company_id}).sort("name", 1).to_list(200)
    return [_out(d) for d in docs]


@router.post("", response_model=ScheduleOut, status_code=201)
async def create_schedule(payload: ScheduleCreate, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    for field in ("entrada", "inicio_intervalo", "fim_intervalo", "saida"):
        if not hhmm_valid(getattr(payload, field)):
            raise HTTPException(status_code=400, detail=f"Horário inválido em '{field}'. Use o formato HH:MM.")
    if payload.kind not in SCHEDULE_KINDS:
        raise HTTPException(status_code=400, detail="Tipo de jornada inválido.")
    if any(d < 0 or d > 6 for d in payload.work_days):
        raise HTTPException(status_code=400, detail="Dias da semana inválidos.")

    cycle_anchor = cycle_on = cycle_off = None
    if payload.kind in CYCLE_PRESETS:
        if not payload.cycle_anchor:
            raise HTTPException(status_code=400, detail="Informe a data de início do ciclo da escala.")
        try:
            cycle_anchor = date.fromisoformat(payload.cycle_anchor).isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Data de início do ciclo inválida. Use AAAA-MM-DD.")
        preset_on, preset_off = CYCLE_PRESETS[payload.kind]
        cycle_on = payload.cycle_on_days or preset_on
        cycle_off = payload.cycle_off_days or preset_off

    doc = {
        "id": uuid.uuid4().hex,
        "company_id": user.company_id,
        "name": payload.name.strip(),
        "entrada": payload.entrada,
        "inicio_intervalo": payload.inicio_intervalo,
        "fim_intervalo": payload.fim_intervalo,
        "saida": payload.saida,
        "tolerance_minutes": payload.tolerance_minutes,
        "work_days": payload.work_days,
        "kind": payload.kind,
        "cycle_anchor": cycle_anchor,
        "cycle_on_days": cycle_on,
        "cycle_off_days": cycle_off,
        "created_at": now_utc(),
    }
    await db.work_schedules.insert_one(dict(doc))
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="JORNADA_CRIADA",
        resource="work_schedule",
        resource_id=doc["id"],
        after={"name": doc["name"], "kind": doc["kind"], "entrada": doc["entrada"], "saida": doc["saida"]},
        ip=client_ip(request),
    )
    return _out(doc)
