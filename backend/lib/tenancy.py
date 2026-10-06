"""Tenant helpers — the single place that resolves company scope and employee access.

company_id ALWAYS comes from the session user, never from the request body or query (§19).
"""

from datetime import date

from fastapi import HTTPException

from lib.db import db
from lib.security import UserContext
from lib.timeutil import DEFAULT_TZ


async def company_tz(company_id: str) -> str:
    company = await db.companies.find_one({"id": company_id})
    return (company or {}).get("timezone") or DEFAULT_TZ


async def company_doc(company_id: str) -> dict:
    company = await db.companies.find_one({"id": company_id})
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return company


def scope(user: UserContext, extra: dict | None = None) -> dict:
    """Base Mongo filter bound to the caller's company."""
    query: dict = {"company_id": user.company_id}
    if extra:
        query.update(extra)
    return query


async def resolve_employee(user: UserContext, employee_id: str | None) -> dict:
    """Employee the caller is allowed to act on.

    - funcionario: only their own linked employee, whatever id they pass.
    - gestor/admin/super_admin: any employee inside their own company.
    """
    if user.role == "funcionario":
        if not user.employee_id:
            raise HTTPException(status_code=403, detail="Seu usuário não está vinculado a um funcionário.")
        target = user.employee_id
    else:
        target = employee_id or user.employee_id
        if not target:
            raise HTTPException(status_code=400, detail="Informe o funcionário.")
    employee = await db.employees.find_one({"id": target, "company_id": user.company_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    return employee


async def schedule_for(employee: dict) -> dict | None:
    """Default (contract) schedule of the employee, ignoring period assignments."""
    if not employee.get("schedule_id"):
        return None
    return await db.work_schedules.find_one({"id": employee["schedule_id"], "company_id": employee["company_id"]})


async def assignments_for(employee: dict) -> list[dict]:
    """Escalas (period schedule assignments) of one employee, newest start first."""
    return await (
        db.schedule_assignments.find({"company_id": employee["company_id"], "employee_id": employee["id"]})
        .sort("start_date", -1)
        .to_list(200)
    )


def assignment_on(day: date, assignments: list[dict]) -> dict | None:
    """The assignment covering `day` — latest start wins, open end means still in force."""
    iso = day.isoformat()
    for assignment in assignments:  # already sorted by start_date desc
        if assignment["start_date"] <= iso and (not assignment.get("end_date") or assignment["end_date"] >= iso):
            return assignment
    return None


async def schedule_resolver(employee: dict):
    """Build a `day -> schedule` resolver for one employee.

    Precedence: escala vigente no dia > jornada do contrato. Loads every schedule and
    assignment once, so a 180-day espelho stays a handful of queries instead of hundreds.
    """
    assignments = await assignments_for(employee)
    schedules = await db.work_schedules.find({"company_id": employee["company_id"]}).to_list(300)
    by_id = {s["id"]: s for s in schedules}
    default = by_id.get(employee.get("schedule_id") or "")

    def resolve(day: date) -> dict | None:
        assignment = assignment_on(day, assignments)
        if assignment:
            return by_id.get(assignment["schedule_id"]) or default
        return default

    return resolve


async def holiday_map(company_id: str, start: date, end: date) -> dict[str, dict]:
    """{'YYYY-MM-DD': holiday} for the period — one query, used by the calc layer."""
    docs = await db.holidays.find(
        {"company_id": company_id, "date": {"$gte": start.isoformat(), "$lte": end.isoformat()}}
    ).to_list(500)
    return {d["date"]: d for d in docs}
