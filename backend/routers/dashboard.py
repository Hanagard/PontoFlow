"""Dashboard (§16) + audit log read view (§11)."""

from fastapi import APIRouter, Depends

from lib.calc import day_summary, next_allowed_type
from lib.db import db
from lib.hoursbank import recent_competences
from lib.security import UserContext, require_roles
from lib.tenancy import company_doc, holiday_map, schedule_resolver
from lib.timeutil import day_bounds_utc, hhmm, local_today, now_utc
from models.reports import AuditOut, DashboardOut

router = APIRouter(tags=["dashboard"])
MANAGERS = ("super_admin", "admin", "gestor")


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(user: UserContext = Depends(require_roles(*MANAGERS))):
    company = await company_doc(user.company_id)
    tz = company.get("timezone", "America/Belem")
    day = local_today(tz)
    start, end = day_bounds_utc(day, tz)

    employees = await db.employees.find({"company_id": user.company_id, "status": "ativo"}).to_list(1000)
    records = await db.time_records.find(
        {"company_id": user.company_id, "timestamp": {"$gte": start, "$lt": end}}
    ).to_list(5000)
    pending = await db.time_adjustment_requests.count_documents(
        {"company_id": user.company_id, "status": "pendente"}
    )
    holidays = await holiday_map(user.company_id, day, day)
    holiday = holidays.get(day.isoformat())

    by_employee: dict[str, list[dict]] = {}
    for r in records:
        by_employee.setdefault(r["employee_id"], []).append(r)

    present = on_interval = absent = delayed = incomplete = 0
    overtime_total = balance_total = 0
    for employee in employees:
        docs = by_employee.get(employee["id"], [])
        resolve = await schedule_resolver(employee)
        summary = day_summary(day, docs, resolve(day), tz, holiday=holiday)
        next_type = next_allowed_type({d["type"] for d in docs})
        if next_type == "entrada":
            if summary["is_workday"]:
                absent += 1
        elif next_type == "fim_intervalo":
            on_interval += 1
        elif next_type is None:
            pass
        else:
            present += 1
        if summary["delay_minutes"]:
            delayed += 1
        if summary["status"] == "incompleta":
            incomplete += 1
        overtime_total += summary["overtime_minutes"] or 0
        balance_total += summary["balance_minutes"] or 0

    # Saldo acumulado do banco de horas da empresa na competência corrente.
    competence = recent_competences(day, 1)[0]
    closures = await db.hours_bank_closures.find(
        {"company_id": user.company_id, "competence": competence}
    ).to_list(500)
    hours_bank_total = sum(c.get("balance_minutes", 0) for c in closures)

    return DashboardOut(
        company_name=company.get("name", ""),
        local_date=day.isoformat(),
        server_time=now_utc(),
        employees_active=len(employees),
        present_now=present,
        on_interval=on_interval,
        absent=absent,
        delayed=delayed,
        incomplete_days=incomplete,
        pending_requests=pending,
        overtime_hhmm=hhmm(overtime_total) or "00:00",
        balance_hhmm=hhmm(balance_total) or "00:00",
        today_records=len(records),
        holiday_name=(holiday or {}).get("name"),
        hours_bank_hhmm=hhmm(hours_bank_total) or "00:00",
    )


@router.get("/audit-logs", response_model=list[AuditOut])
async def audit_logs(action: str | None = None, limit: int = 100, user: UserContext = Depends(require_roles(*MANAGERS))):
    query: dict = {"company_id": user.company_id}
    if action:
        query["action"] = action
    docs = await db.audit_logs.find(query).sort("created_at", -1).to_list(min(max(limit, 1), 300))
    return [
        AuditOut(
            id=d["id"],
            company_id=d["company_id"],
            actor_name=d.get("actor_name", "sistema"),
            actor_role=d.get("actor_role", "sistema"),
            action=d["action"],
            resource=d["resource"],
            resource_id=d.get("resource_id"),
            before=d.get("before"),
            after=d.get("after"),
            ip=d.get("ip"),
            created_at=d["created_at"],
        )
        for d in docs
    ]
