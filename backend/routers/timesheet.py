"""Espelho de ponto (§15) + reports (§26) + exportações CSV/PDF. Cálculo em lib/calc."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response

from lib.calc import day_summary, summarize, timesheet_csv
from lib.db import db
from lib.pdf import timesheet_pdf
from lib.security import UserContext, get_current_user, require_roles
from lib.tenancy import company_doc, company_tz, holiday_map, resolve_employee, schedule_resolver
from lib.timeutil import date_range_utc, hhmm, local_date_of, local_today
from lib.validators import cpf_masked
from models.reports import ReportOut, ReportRow, TimesheetOut, TimesheetSummary

router = APIRouter(tags=["timesheet"])
MANAGERS = ("super_admin", "admin", "gestor")


def _parse_range(start: str | None, end: str | None, tz: str) -> tuple[date, date]:
    today = local_today(tz)
    try:
        end_d = date.fromisoformat(end) if end else today
        start_d = date.fromisoformat(start) if start else end_d.replace(day=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Período inválido. Use datas no formato AAAA-MM-DD.")
    if start_d > end_d:
        raise HTTPException(status_code=400, detail="A data inicial não pode ser maior que a final.")
    if (end_d - start_d).days > 180:
        raise HTTPException(status_code=400, detail="Período muito longo. Selecione no máximo 180 dias.")
    return start_d, end_d


async def build_days(company_id: str, employee: dict, start_d: date, end_d: date, tz: str) -> list[dict]:
    """Dias do espelho com a escala vigente em cada data e o calendário de feriados aplicado.

    Também usado pelo banco de horas e pelos relatórios — é o único lugar que monta a série
    diária, para que todas as telas somem exatamente os mesmos números.
    """
    if end_d < start_d:
        return []
    start_utc, end_utc = date_range_utc(start_d, end_d, tz)
    records = await db.time_records.find(
        {"company_id": company_id, "employee_id": employee["id"], "timestamp": {"$gte": start_utc, "$lt": end_utc}}
    ).sort("timestamp", 1).to_list(5000)
    justifications = await db.time_adjustment_requests.find(
        {"company_id": company_id, "employee_id": employee["id"], "status": "aprovada", "kind": "falta_justificada"}
    ).to_list(500)
    justified_days = {j["target_date"] for j in justifications}

    by_day: dict[str, list[dict]] = {}
    for r in records:
        by_day.setdefault(local_date_of(r["timestamp"], tz).isoformat(), []).append(r)

    resolve_schedule = await schedule_resolver(employee)
    holidays = await holiday_map(company_id, start_d, end_d)

    days: list[dict] = []
    cursor = start_d
    while cursor <= end_d:
        key = cursor.isoformat()
        days.append(
            day_summary(
                cursor,
                by_day.get(key, []),
                resolve_schedule(cursor),
                tz,
                justified=key in justified_days,
                holiday=holidays.get(key),
            )
        )
        cursor += timedelta(days=1)
    return days


def _summary_model(raw: dict) -> TimesheetSummary:
    return TimesheetSummary(
        total_worked_minutes=raw["total_worked_minutes"],
        total_worked_hhmm=hhmm(raw["total_worked_minutes"]),
        total_expected_minutes=raw["total_expected_minutes"],
        total_expected_hhmm=hhmm(raw["total_expected_minutes"]),
        total_balance_minutes=raw["total_balance_minutes"],
        total_balance_hhmm=hhmm(raw["total_balance_minutes"]),
        total_overtime_minutes=raw["total_overtime_minutes"],
        total_overtime_hhmm=hhmm(raw["total_overtime_minutes"]),
        total_delay_minutes=raw["total_delay_minutes"],
        total_delay_hhmm=hhmm(raw["total_delay_minutes"]),
        faltas=raw["faltas"],
        incompletas=raw["incompletas"],
        feriados=raw.get("feriados", 0),
    )


async def _schedule_label(employee: dict, day: date) -> str | None:
    resolve = await schedule_resolver(employee)
    schedule = resolve(day)
    return (schedule or {}).get("name")


@router.get("/timesheet", response_model=TimesheetOut)
async def timesheet(
    employee_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    status: str | None = None,
    user: UserContext = Depends(get_current_user),
):
    tz = await company_tz(user.company_id)
    employee = await resolve_employee(user, employee_id)
    start_d, end_d = _parse_range(start, end, tz)
    days = await build_days(user.company_id, employee, start_d, end_d, tz)
    summary = _summary_model(summarize(days))
    if status:
        days = [d for d in days if d["status"] == status]
    return TimesheetOut(
        employee_id=employee["id"],
        employee_name=employee["name"],
        matricula=employee.get("matricula"),
        department=employee.get("department"),
        schedule_name=await _schedule_label(employee, end_d),
        timezone=tz,
        start=start_d.isoformat(),
        end=end_d.isoformat(),
        days=days,  # type: ignore[arg-type]
        summary=summary,
    )


@router.get("/timesheet/export")
async def export_timesheet(
    employee_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user: UserContext = Depends(get_current_user),
):
    """CSV export gerado no backend (§26)."""
    tz = await company_tz(user.company_id)
    employee = await resolve_employee(user, employee_id)
    start_d, end_d = _parse_range(start, end, tz)
    days = await build_days(user.company_id, employee, start_d, end_d, tz)
    csv = timesheet_csv(days, summarize(days))
    filename = f"espelho-{employee['matricula']}-{start_d}-{end_d}.csv"
    return Response(
        content=csv,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/timesheet/pdf")
async def export_timesheet_pdf(
    employee_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user: UserContext = Depends(get_current_user),
):
    """Espelho em PDF, pronto para imprimir e assinar (§26)."""
    tz = await company_tz(user.company_id)
    employee = await resolve_employee(user, employee_id)
    company = await company_doc(user.company_id)
    start_d, end_d = _parse_range(start, end, tz)
    days = await build_days(user.company_id, employee, start_d, end_d, tz)
    pdf = timesheet_pdf(
        company=company,
        employee=employee,
        schedule_name=await _schedule_label(employee, end_d),
        days=days,
        summary=summarize(days),
        start=start_d.isoformat(),
        end=end_d.isoformat(),
        cpf_masked=cpf_masked(employee.get("cpf", "")),
    )
    filename = f"espelho-{employee['matricula']}-{start_d}-{end_d}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports", response_model=ReportOut)
async def reports(
    kind: str = "espelho",
    start: str | None = None,
    end: str | None = None,
    department: str | None = None,
    user: UserContext = Depends(require_roles(*MANAGERS)),
):
    """Uma linha consolidada por funcionário; `kind` define a ênfase da ordenação (§26)."""
    if kind not in ("espelho", "atrasos", "extras", "faltas", "pendencias"):
        raise HTTPException(status_code=400, detail="Tipo de relatório inválido.")
    tz = await company_tz(user.company_id)
    start_d, end_d = _parse_range(start, end, tz)
    query: dict = {"company_id": user.company_id, "status": "ativo"}
    if department:
        query["department"] = department
    employees = await db.employees.find(query).sort("name", 1).to_list(300)

    rows: list[ReportRow] = []
    for employee in employees:
        days = await build_days(user.company_id, employee, start_d, end_d, tz)
        raw = summarize(days)
        rows.append(
            ReportRow(
                employee_id=employee["id"],
                employee_name=employee["name"],
                matricula=employee.get("matricula"),
                department=employee.get("department"),
                worked_hhmm=hhmm(raw["total_worked_minutes"]) or "00:00",
                expected_hhmm=hhmm(raw["total_expected_minutes"]) or "00:00",
                balance_hhmm=hhmm(raw["total_balance_minutes"]) or "00:00",
                overtime_hhmm=hhmm(raw["total_overtime_minutes"]) or "00:00",
                delay_hhmm=hhmm(raw["total_delay_minutes"]) or "00:00",
                faltas=raw["faltas"],
                incompletas=raw["incompletas"],
            )
        )

    key = {
        "atrasos": lambda r: -_mins(r.delay_hhmm),
        "extras": lambda r: -_mins(r.overtime_hhmm),
        "faltas": lambda r: -r.faltas,
        "pendencias": lambda r: -r.incompletas,
        "espelho": lambda r: r.employee_name,
    }[kind]
    rows.sort(key=key)  # type: ignore[arg-type]
    return ReportOut(kind=kind, start=start_d.isoformat(), end=end_d.isoformat(), rows=rows)


def _mins(value: str) -> int:
    sign = -1 if value.startswith("-") else 1
    hours, minutes = value.lstrip("-").split(":")
    return sign * (int(hours) * 60 + int(minutes))
