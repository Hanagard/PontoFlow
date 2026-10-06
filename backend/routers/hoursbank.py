"""Banco de horas (§ Fase 15.1) — saldo mensal por competência e fechamento.

O cálculo diário continua em lib/calc; aqui ele é agregado por mês e, no fechamento,
congelado em `hours_bank_closures` para que alterações retroativas não reescrevam um mês
já acertado (a divergência fica visível em `recalculated_balance_minutes`).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request

from lib.audit import AuditActor, write_audit
from lib.db import db
from lib.hoursbank import accumulate, competence_bounds, competence_label, month_entry, recent_competences
from lib.security import UserContext, client_ip, get_current_user, require_roles
from lib.tenancy import company_tz, resolve_employee
from lib.timeutil import hhmm, local_today, now_utc
from models.hoursbank import (
    CloseCompetenceIn,
    CloseCompetenceOut,
    HoursBankBoardOut,
    HoursBankBoardRow,
    HoursBankMonth,
    HoursBankOut,
    HoursBankTotals,
)
from routers.timesheet import build_days

router = APIRouter(prefix="/hours-bank", tags=["hours-bank"])
MANAGERS = ("super_admin", "admin", "gestor")
ADMINS = ("super_admin", "admin")
MAX_MONTHS = 24


async def _closures(company_id: str, employee_id: str) -> dict[str, dict]:
    docs = await db.hours_bank_closures.find({"company_id": company_id, "employee_id": employee_id}).to_list(200)
    return {d["competence"]: d for d in docs}


async def _months_for(company_id: str, employee: dict, competences: list[str], tz: str) -> list[dict]:
    closures = await _closures(company_id, employee["id"])
    today = local_today(tz)
    months: list[dict] = []
    for competence in competences:
        first, last = competence_bounds(competence)
        # Never project the future: an open month only counts up to today.
        days = await build_days(company_id, employee, first, min(last, today), tz)
        months.append(month_entry(competence, days, closures.get(competence)))
    return months


@router.get("", response_model=HoursBankOut)
async def hours_bank(
    employee_id: str | None = None,
    months: int = 6,
    user: UserContext = Depends(get_current_user),
):
    """Extrato do banco de horas. Funcionário sempre recebe o próprio, por `resolve_employee`."""
    if not 1 <= months <= MAX_MONTHS:
        raise HTTPException(status_code=400, detail=f"Informe entre 1 e {MAX_MONTHS} meses.")
    tz = await company_tz(user.company_id)
    employee = await resolve_employee(user, employee_id)
    competences = recent_competences(local_today(tz), months)
    entries = await _months_for(user.company_id, employee, competences, tz)
    totals = accumulate(entries)
    return HoursBankOut(
        employee_id=employee["id"],
        employee_name=employee["name"],
        matricula=employee.get("matricula"),
        department=employee.get("department"),
        months=[HoursBankMonth(**m) for m in entries],
        totals=HoursBankTotals(**totals),
    )


@router.get("/board", response_model=HoursBankBoardOut)
async def hours_bank_board(
    months: int = 6,
    department: str | None = None,
    user: UserContext = Depends(require_roles(*MANAGERS)),
):
    """Quanto cada pessoa tem a compensar — uma linha por funcionário ativo."""
    if not 1 <= months <= MAX_MONTHS:
        raise HTTPException(status_code=400, detail=f"Informe entre 1 e {MAX_MONTHS} meses.")
    tz = await company_tz(user.company_id)
    today = local_today(tz)
    competences = recent_competences(today, months)
    current = competences[-1]

    query: dict = {"company_id": user.company_id, "status": "ativo"}
    if department:
        query["department"] = department
    employees = await db.employees.find(query).sort("name", 1).to_list(300)

    rows: list[HoursBankBoardRow] = []
    for employee in employees:
        entries = await _months_for(user.company_id, employee, competences, tz)
        totals = accumulate(entries)
        current_entry = next((m for m in entries if m["competence"] == current), None)
        rows.append(
            HoursBankBoardRow(
                employee_id=employee["id"],
                employee_name=employee["name"],
                matricula=employee.get("matricula"),
                department=employee.get("department"),
                current_competence=current,
                current_balance_minutes=(current_entry or {}).get("balance_minutes", 0),
                current_balance_hhmm=hhmm((current_entry or {}).get("balance_minutes", 0)),
                accumulated_minutes=totals["accumulated_minutes"],
                accumulated_hhmm=totals["accumulated_hhmm"],
                to_compensate_hhmm=totals["to_compensate_hhmm"],
                direction=totals["direction"],  # type: ignore[arg-type]
                closed_months=totals["closed_months"],
            )
        )
    rows.sort(key=lambda r: r.accumulated_minutes)
    return HoursBankBoardOut(
        competence=current,
        label=competence_label(current),
        months_considered=months,
        rows=rows,
    )


@router.post("/close", response_model=CloseCompetenceOut)
async def close_competence(payload: CloseCompetenceIn, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    """Fecha a competência: congela o saldo do mês. Sem employee_id, fecha para todos os ativos."""
    tz = await company_tz(user.company_id)
    today = local_today(tz)
    first, last = competence_bounds(payload.competence)
    if first > today:
        raise HTTPException(status_code=400, detail="Não é possível fechar uma competência futura.")
    if first.year < 2000:
        raise HTTPException(status_code=400, detail="Competência inválida.")

    if payload.employee_id:
        employees = [await resolve_employee(user, payload.employee_id)]
    else:
        employees = await db.employees.find({"company_id": user.company_id, "status": "ativo"}).to_list(300)

    closed = 0
    for employee in employees:
        if await db.hours_bank_closures.find_one(
            {"company_id": user.company_id, "employee_id": employee["id"], "competence": payload.competence}
        ):
            continue
        days = await build_days(user.company_id, employee, first, min(last, today), tz)
        balance = sum(d["balance_minutes"] or 0 for d in days)
        worked = sum(d["worked_minutes"] or 0 for d in days)
        expected = sum(d["expected_minutes"] or 0 for d in days)
        await db.hours_bank_closures.insert_one(
            {
                "id": __import__("uuid").uuid4().hex,
                "company_id": user.company_id,
                "employee_id": employee["id"],
                "competence": payload.competence,
                "balance_minutes": balance,
                "worked_minutes": worked,
                "expected_minutes": expected,
                "closed_by": user.id,
                "closed_by_name": user.name,
                "closed_at": now_utc(),
            }
        )
        closed += 1

    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="COMPETENCIA_FECHADA",
        resource="hours_bank_closure",
        resource_id=payload.competence,
        after={"competence": payload.competence, "funcionarios": closed, "employee_id": payload.employee_id},
        ip=client_ip(request),
    )
    return CloseCompetenceOut(competence=payload.competence, label=competence_label(payload.competence), closed=closed)


@router.post("/reopen", response_model=CloseCompetenceOut)
async def reopen_competence(payload: CloseCompetenceIn, request: Request, user: UserContext = Depends(require_roles(*ADMINS))):
    """Reabre a competência (descongela o saldo) — ação auditada."""
    query: dict = {"company_id": user.company_id, "competence": payload.competence}
    if payload.employee_id:
        employee = await resolve_employee(user, payload.employee_id)
        query["employee_id"] = employee["id"]
    result = await db.hours_bank_closures.delete_many(query)
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Nenhum fechamento encontrado para esta competência.")
    await write_audit(
        company_id=user.company_id,
        actor=AuditActor(id=user.id, name=user.name, role=user.role),
        action="COMPETENCIA_REABERTA",
        resource="hours_bank_closure",
        resource_id=payload.competence,
        before={"competence": payload.competence, "fechamentos": result.deleted_count},
        ip=client_ip(request),
    )
    return CloseCompetenceOut(
        competence=payload.competence,
        label=competence_label(payload.competence),
        closed=result.deleted_count,
        reopened=True,
    )
