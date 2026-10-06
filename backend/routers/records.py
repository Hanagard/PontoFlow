"""Time record routes (§8, §9, §10) — the punch engine.

Two hard rules enforced here, server-side only:
1. The official timestamp is produced by the server (now_utc()); the client sends none.
2. The next allowed event is decided by the server from today's existing records; an invalid
   sequence (duplicate entrada, saída before entrada, …) is rejected with a clear 400.
"""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from lib.audit import AuditActor, write_audit
from lib.calc import TYPE_LABELS, day_summary, next_allowed_type
from lib.db import db
from lib.security import UserContext, client_ip, get_current_user, require_roles
from lib.tenancy import company_tz, holiday_map, resolve_employee, schedule_resolver
from lib.timeutil import day_bounds_utc, hhmm_of, local_date_of, local_today, now_utc, parse_hhmm
from models.records import PunchCreate, PunchStatusOut, TimeRecordOut

router = APIRouter(prefix="/time-records", tags=["time-records"])
MANAGERS = ("super_admin", "admin", "gestor")


def _record_out(doc: dict, tz: str) -> TimeRecordOut:
    ts = doc["timestamp"]
    return TimeRecordOut(
        id=doc["id"],
        company_id=doc["company_id"],
        employee_id=doc["employee_id"],
        type=doc["type"],
        type_label=TYPE_LABELS[doc["type"]],
        timestamp=ts,
        timezone=doc.get("timezone", tz),
        hhmm=hhmm_of(ts, doc.get("timezone", tz)),
        local_date=local_date_of(ts, doc.get("timezone", tz)).isoformat(),
        origin=doc.get("origin", "web"),
        status=doc.get("status", "valido"),
        observacao=doc.get("observacao"),
        adjusted=bool(doc.get("adjusted")),
        created_at=doc.get("created_at") or ts,
    )


async def _records_of_day(company_id: str, employee_id: str, day: date, tz: str) -> list[dict]:
    start, end = day_bounds_utc(day, tz)
    return await (
        db.time_records.find(
            {"company_id": company_id, "employee_id": employee_id, "timestamp": {"$gte": start, "$lt": end}}
        )
        .sort("timestamp", 1)
        .to_list(50)
    )


def _schedule_label(schedule: dict | None) -> str | None:
    if not schedule:
        return None
    return f"{schedule['entrada']} — {schedule['saida']}"


def _crosses_midnight(schedule: dict | None) -> bool:
    if not schedule:
        return False
    return parse_hhmm(schedule["saida"]) <= parse_hhmm(schedule["entrada"])


def _work_date(now, schedule: dict | None, tz: str) -> date:
    from zoneinfo import ZoneInfo
    local = now.astimezone(ZoneInfo(tz))
    day = local.date()
    if _crosses_midnight(schedule) and local.hour * 60 + local.minute < parse_hhmm(schedule["saida"]):
        return day - timedelta(days=1)
    return day


@router.get("/today", response_model=PunchStatusOut)
async def today_status(employee_id: str | None = None, user: UserContext = Depends(get_current_user)):
    employee = await resolve_employee(user, employee_id)
    tz = await company_tz(user.company_id)
    today = local_today(tz)
    resolve = await schedule_resolver(employee)
    schedule = resolve(today)
    day = today
    # After midnight, keep an unfinished overnight shift attached to the day it started.
    if schedule and _crosses_midnight(schedule):
        previous_day = today - timedelta(days=1)
        previous_schedule = resolve(previous_day)
        previous_docs = await _records_of_day(user.company_id, employee["id"], previous_day, tz)
        if previous_schedule and previous_docs and next_allowed_type({d["type"] for d in previous_docs}) is not None:
            day = previous_day
            schedule = previous_schedule
            docs = previous_docs
        else:
            docs = await _records_of_day(user.company_id, employee["id"], today, tz)
    else:
        docs = await _records_of_day(user.company_id, employee["id"], today, tz)
    holiday = (await holiday_map(user.company_id, day, day)).get(day.isoformat())
    next_type = next_allowed_type({d["type"] for d in docs})
    summary = day_summary(day, docs, schedule, tz, holiday=holiday)

    status_label = {
        "entrada": "Aguardando entrada",
        "inicio_intervalo": "Trabalhando",
        "fim_intervalo": "Em intervalo",
        "saida": "Trabalhando",
    }.get(next_type or "", "Jornada concluída")

    now = now_utc()
    return PunchStatusOut(
        server_time=now,
        server_hhmm=hhmm_of(now, tz),
        local_date=day.isoformat(),
        timezone=tz,
        employee_name=employee["name"],
        schedule_name=(schedule or {}).get("name"),
        schedule_label=_schedule_label(schedule),
        next_type=next_type,
        next_label=TYPE_LABELS.get(next_type) if next_type else None,
        status_label=status_label,
        records=[_record_out(d, tz) for d in docs],
        worked_hhmm=summary["worked_hhmm"],
        expected_hhmm=summary["expected_hhmm"],
    )


@router.post("", response_model=TimeRecordOut, status_code=201)
async def punch(payload: PunchCreate, request: Request, user: UserContext = Depends(get_current_user)):
    """Register the next valid punch for the session's own employee."""
    employee = await resolve_employee(user, None)
    if employee.get("status") != "ativo":
        raise HTTPException(status_code=403, detail="Funcionário inativo não pode registrar ponto.")
    tz = await company_tz(user.company_id)
    today = local_today(tz)
    resolve = await schedule_resolver(employee)
    schedule_today = resolve(today)
    now = now_utc()
    work_day = _work_date(now, schedule_today, tz)

    # Overnight shifts belong to the date on which the shift started.
    docs = await _records_of_day(user.company_id, employee["id"], work_day, tz)
    if _crosses_midnight(schedule_today) and work_day != today:
        # Include legacy records that predate the work_date field.
        docs = await db.time_records.find(
            {
                "company_id": user.company_id,
                "employee_id": employee["id"],
                "$or": [
                    {"work_date": work_day.isoformat()},
                    {"timestamp": {"$gte": day_bounds_utc(work_day, tz)[0], "$lt": day_bounds_utc(today, tz)[1]}},
                ],
            }
        ).sort("timestamp", 1).to_list(50)

    existing = {d["type"] for d in docs}
    next_type = next_allowed_type(existing)
    if next_type is None:
        raise HTTPException(status_code=400, detail="Sua jornada já está completa. Solicite um ajuste se necessário.")

    doc = {
        "id": uuid.uuid4().hex,
        "company_id": user.company_id,
        "employee_id": employee["id"],
        "work_date": work_day.isoformat(),
        "type": next_type,
        "timestamp": now,  # server clock — the browser's is never used (§9)
        "timezone": tz,
        "origin": "web",
        "device": (request.headers.get("user-agent") or "")[:200] or None,
        "ip": client_ip(request),
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "accuracy": payload.accuracy,
        "observacao": payload.observacao,
        "status": "valido",
        "adjusted": False,
        "created_at": now,
    }
    try:
        await db.time_records.insert_one(dict(doc))
    except DuplicateKeyError:
        # Another request registered the same next event first. The unique index makes
        # the server-side sequence atomic under concurrent clicks/retries.
        raise HTTPException(status_code=409, detail="Este registro já foi efetuado. Atualize o ponto e tente novamente.")
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="PONTO_REGISTRADO",
        resource="time_record",
        resource_id=doc["id"],
        after={"type": next_type, "hhmm": hhmm_of(now, tz), "date": work_day.isoformat()},
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return _record_out(doc, tz)


@router.get("", response_model=list[TimeRecordOut])
async def list_records(
    employee_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user: UserContext = Depends(get_current_user)
):
    tz = await company_tz(user.company_id)
    query: dict = {"company_id": user.company_id}
    if user.role == "funcionario":
        employee = await resolve_employee(user, None)
        query["employee_id"] = employee["id"]
    elif employee_id:
        employee = await resolve_employee(user, employee_id)
        query["employee_id"] = employee["id"]
    if start and end:
        try:
            start_utc, _ = day_bounds_utc(date.fromisoformat(start), tz)
            _, end_utc = day_bounds_utc(date.fromisoformat(end), tz)
        except ValueError:
            raise HTTPException(status_code=400, detail="Período inválido. Use datas no formato AAAA-MM-DD.")
        query["timestamp"] = {"$gte": start_utc, "$lt": end_utc}
    docs = await db.time_records.find(query).sort("timestamp", -1).to_list(500)
    return [_record_out(d, tz) for d in docs]


@router.get("/live", response_model=list[dict])
async def live_board(user: UserContext = Depends(require_roles(*MANAGERS))):
    """Who is where right now — the manager ledger. Derived entirely server-side."""
    tz = await company_tz(user.company_id)
    day = local_today(tz)
    start, end = day_bounds_utc(day, tz)
    employees = await db.employees.find({"company_id": user.company_id, "status": "ativo"}).sort("name", 1).to_list(500)
    records = await db.time_records.find(
        {"company_id": user.company_id, "timestamp": {"$gte": start, "$lt": end}}
    ).sort("timestamp", 1).to_list(2000)
    by_employee: dict[str, list[dict]] = {}
    for r in records:
        by_employee.setdefault(r["employee_id"], []).append(r)

    board = []
    holiday = (await holiday_map(user.company_id, day, day)).get(day.isoformat())
    for employee in employees:
        docs = by_employee.get(employee["id"], [])
        types = {d["type"] for d in docs}
        next_type = next_allowed_type(types)
        state = {
            "entrada": "ausente",
            "inicio_intervalo": "trabalhando",
            "fim_intervalo": "intervalo",
            "saida": "trabalhando",
        }.get(next_type or "", "encerrado")
        resolve = await schedule_resolver(employee)
        summary = day_summary(day, docs, resolve(day), tz, holiday=holiday)
        board.append(
            {
                "employee_id": employee["id"],
                "employee_name": employee["name"],
                "department": employee.get("department"),
                "state": state,
                "entrada": summary["entrada"]["hhmm"],
                "saida": summary["saida"]["hhmm"],
                "worked_hhmm": summary["worked_hhmm"],
                "delay_minutes": summary["delay_minutes"],
                "delay_hhmm": summary["delay_hhmm"],
            }
        )
    return board
