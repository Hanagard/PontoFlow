"""Idempotent demo seed: one company, 4 logins, 5 employees, ~3 weeks of punches.

Run: cd /app/backend && python seed.py
Safe to re-run — it clears only the demo company's documents, never other tenants.
"""

import asyncio
import random
import uuid
from datetime import date, timedelta

from lib.db import db, ensure_indexes
from lib.security import hash_password
from lib.timeutil import local_dt, now_utc

COMPANY_ID = "demo-pontoflow-company"
TZ = "America/Belem"

SCHEDULES = [
    {
        "id": "sched-comercial",
        "name": "Comercial 08:00 - 18:00",
        "entrada": "08:00",
        "inicio_intervalo": "12:00",
        "fim_intervalo": "13:00",
        "saida": "18:00",
        "tolerance_minutes": 10,
        "work_days": [0, 1, 2, 3, 4],
    },
    {
        "id": "sched-administrativo",
        "name": "Administrativo 09:00 - 18:00",
        "entrada": "09:00",
        "inicio_intervalo": "12:30",
        "fim_intervalo": "13:30",
        "saida": "18:00",
        "tolerance_minutes": 5,
        "work_days": [0, 1, 2, 3, 4],
    },
    {
        "id": "sched-escala12x36",
        "name": "Escala 12x36 (Plantão)",
        "entrada": "07:00",
        "inicio_intervalo": "12:00",
        "fim_intervalo": "13:00",
        "saida": "19:00",
        "tolerance_minutes": 10,
        "work_days": [0, 1, 2, 3, 4, 5, 6],
        "kind": "12x36",
        "cycle_on_days": 1,
        "cycle_off_days": 1,
    },
]

EMPLOYEES = [
    {"id": "emp-maria", "name": "Maria Silva", "cpf": "52998224725", "matricula": "0001", "cargo": "Analista de Suporte", "department": "Operações", "schedule_id": "sched-comercial", "email": "maria.silva@pontoflow.com.br"},
    {"id": "emp-joao", "name": "João Pereira", "cpf": "11144477735", "matricula": "0002", "cargo": "Coordenador", "department": "Operações", "schedule_id": "sched-comercial", "email": "gestor@pontoflow.com.br"},
    {"id": "emp-ana", "name": "Ana Costa", "cpf": "15350946056", "matricula": "0003", "cargo": "Assistente Financeiro", "department": "Financeiro", "schedule_id": "sched-administrativo", "email": "ana.costa@pontoflow.com.br"},
    {"id": "emp-carlos", "name": "Carlos Mendes", "cpf": "28625587887", "matricula": "0004", "cargo": "Técnico de Campo", "department": "Operações", "schedule_id": "sched-comercial", "email": "carlos.mendes@pontoflow.com.br"},
    {"id": "emp-lucia", "name": "Lúcia Ramos", "cpf": "66414157060", "matricula": "0005", "cargo": "Analista de RH", "department": "Pessoas", "schedule_id": "sched-administrativo", "email": "lucia.ramos@pontoflow.com.br"},
]

USERS = [
    {"id": "user-admin", "name": "Rafael Almeida", "email": "admin@pontoflow.com.br", "role": "admin", "employee_id": None},
    {"id": "user-super", "name": "Super Administrador", "email": "super@pontoflow.com.br", "role": "super_admin", "employee_id": None},
    {"id": "user-gestor", "name": "João Pereira", "email": "gestor@pontoflow.com.br", "role": "gestor", "employee_id": "emp-joao"},
    {"id": "user-maria", "name": "Maria Silva", "email": "maria.silva@pontoflow.com.br", "role": "funcionario", "employee_id": "emp-maria"},
]
PASSWORD = "Ponto@2026"


async def main() -> None:
    scope = {"company_id": COMPANY_ID}
    for collection in ("users", "employees", "work_schedules", "time_records", "time_adjustment_requests", "audit_logs"):
        await db[collection].delete_many(scope)
    await db.companies.delete_many({"id": COMPANY_ID})

    await db.companies.insert_one(
        {"id": COMPANY_ID, "name": "PontoFlow Demonstração LTDA", "cnpj": "12.345.678/0001-90", "timezone": TZ, "status": "ativa", "created_at": now_utc()}
    )
    await db.work_schedules.insert_many([{**s, "company_id": COMPANY_ID, "created_at": now_utc(), "kind": s.get("kind", "fixa"), "cycle_anchor": (date.today() - timedelta(days=30)).isoformat() if s.get("kind") else None} for s in SCHEDULES])

    # Calendário: feriados nacionais do ano corrente e do próximo (§ feriados)
    from lib.holidays import national_holidays

    holiday_docs = []
    for year in (date.today().year, date.today().year + 1):
        for holiday in national_holidays(year):
            holiday_docs.append(
                {
                    "id": uuid.uuid4().hex,
                    "company_id": COMPANY_ID,
                    "date": holiday["date"],
                    "name": holiday["name"],
                    "kind": holiday["kind"],
                    "created_at": now_utc(),
                }
            )
    # Feriado municipal de exemplo (Círio de Nazaré, Belém)
    holiday_docs.append(
        {
            "id": uuid.uuid4().hex,
            "company_id": COMPANY_ID,
            "date": f"{date.today().year}-10-15",
            "name": "Aniversário da Cidade (municipal)",
            "kind": "municipal",
            "created_at": now_utc(),
        }
    )
    seen: set[str] = set()
    unique_holidays = []
    for doc in holiday_docs:
        if doc["date"] in seen:
            continue
        seen.add(doc["date"])
        unique_holidays.append(doc)
    await db.holidays.insert_many(unique_holidays)

    # Escala: Carlos no plantão 12x36 nos últimos 30 dias (§ escalas)
    await db.schedule_assignments.insert_one(
        {
            "id": uuid.uuid4().hex,
            "company_id": COMPANY_ID,
            "employee_id": "emp-carlos",
            "schedule_id": "sched-escala12x36",
            "start_date": (date.today() - timedelta(days=30)).isoformat(),
            "end_date": None,
            "note": "Plantão noturno — escala rotativa",
            "created_by": "user-admin",
            "created_at": now_utc(),
        }
    )

    hired = (date.today() - timedelta(days=400)).isoformat()
    await db.employees.insert_many(
        [
            {
                **e,
                "company_id": COMPANY_ID,
                "user_id": next((u["id"] for u in USERS if u["employee_id"] == e["id"]), None),
                "phone": "(91) 98888-0000",
                "status": "ativo",
                "hired_at": hired,
                "created_at": now_utc(),
                "updated_at": now_utc(),
            }
            for e in EMPLOYEES
        ]
    )
    await db.users.insert_many(
        [
            {**u, "company_id": COMPANY_ID, "password_hash": hash_password(PASSWORD), "status": "ativo", "created_at": now_utc()}
            for u in USERS
        ]
    )

    schedules = {s["id"]: s for s in SCHEDULES}
    random.seed(7)
    records = []
    today = date.today()
    for offset in range(1, 22):  # past 3 weeks, excluding today so the demo punch flow starts clean
        day = today - timedelta(days=offset)
        if day.weekday() > 4:
            continue
        for employee in EMPLOYEES:
            schedule = schedules[employee["schedule_id"]]
            # Carlos misses one day (falta) and leaves one day incomplete — the dashboard needs real variety.
            if employee["id"] == "emp-carlos" and offset == 3:
                continue
            punches = ["entrada", "inicio_intervalo", "fim_intervalo", "saida"]
            if employee["id"] == "emp-carlos" and offset == 5:
                punches = ["entrada", "inicio_intervalo", "fim_intervalo"]
            for punch_type in punches:
                base = schedule["entrada"] if punch_type == "entrada" else schedule[punch_type] if punch_type in schedule else schedule["saida"]
                drift = random.randint(-3, 14) if punch_type == "entrada" else random.randint(-5, 12)
                hours, minutes = map(int, base.split(":"))
                total = hours * 60 + minutes + drift
                stamp = local_dt(day, f"{total // 60:02d}:{total % 60:02d}", TZ)
                records.append(
                    {
                        "id": uuid.uuid4().hex,
                        "company_id": COMPANY_ID,
                        "employee_id": employee["id"],
                        "type": punch_type,
                        "timestamp": stamp,
                        "timezone": TZ,
                        "origin": "web",
                        "device": "seed",
                        "ip": "127.0.0.1",
                        "status": "valido",
                        "adjusted": False,
                        "created_at": stamp,
                    }
                )
    if records:
        await db.time_records.insert_many(records)

    # Two pending requests so the approval queue is not empty on first login.
    pending_day = (today - timedelta(days=2)).isoformat()
    await db.time_adjustment_requests.insert_many(
        [
            {
                "id": uuid.uuid4().hex,
                "company_id": COMPANY_ID,
                "employee_id": "emp-carlos",
                "employee_name": "Carlos Mendes",
                "target_date": (today - timedelta(days=5)).isoformat(),
                "type": "saida",
                "kind": "correcao",
                "requested_time": "18:05",
                "previous_time": None,
                "record_id": None,
                "reason": "Esqueci de registrar a saída, encerrei o atendimento às 18:05.",
                "status": "pendente",
                "created_by": "user-maria",
                "created_at": now_utc(),
            },
            {
                "id": uuid.uuid4().hex,
                "company_id": COMPANY_ID,
                "employee_id": "emp-ana",
                "employee_name": "Ana Costa",
                "target_date": pending_day,
                "type": "entrada",
                "kind": "correcao",
                "requested_time": "09:00",
                "previous_time": None,
                "record_id": None,
                "reason": "Cheguei no horário, porém o sistema estava indisponível para registro.",
                "status": "pendente",
                "created_by": "user-maria",
                "created_at": now_utc(),
            },
        ]
    )

    await db.audit_logs.insert_one(
        {
            "id": uuid.uuid4().hex,
            "company_id": COMPANY_ID,
            "actor_id": "user-admin",
            "actor_name": "Rafael Almeida",
            "actor_role": "admin",
            "action": "EMPRESA_CRIADA",
            "resource": "company",
            "resource_id": COMPANY_ID,
            "before": None,
            "after": {"name": "PontoFlow Demonstração LTDA"},
            "ip": "127.0.0.1",
            "user_agent": "seed",
            "created_at": now_utc(),
        }
    )

    await ensure_indexes()
    print(f"seed ok: {len(EMPLOYEES)} funcionários, {len(records)} registros, senha de todos: {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
