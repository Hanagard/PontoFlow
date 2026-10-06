"""Alertas de pendência do dia (§ Fase 15.5) — o gestor vê quem esqueceu de bater o ponto.

Tudo é derivado no servidor a partir dos registros de hoje, da escala vigente e do
calendário de feriados. Não há estado persistido: o alerta existe enquanto a pendência
existir, e desaparece no instante em que o funcionário registra o ponto que falta.
"""

from fastapi import APIRouter, Depends

from lib.calc import TYPE_LABELS, day_summary, next_allowed_type
from lib.db import db
from lib.security import UserContext, require_roles
from lib.tenancy import company_tz, holiday_map, schedule_resolver
from lib.timeutil import day_bounds_utc, hhmm_of, local_today, now_utc, parse_hhmm
from models.hoursbank import Alert, AlertsOut

router = APIRouter(tags=["alerts"])
MANAGERS = ("super_admin", "admin", "gestor")

# Minutos após o fim da jornada antes de cobrar a saída — evita alarme no segundo seguinte.
GRACE_AFTER_SHIFT = 30
# Minutos de intervalo antes de considerá-lo esquecido em aberto.
MAX_INTERVAL = 150


@router.get("/alerts", response_model=AlertsOut)
async def alerts(user: UserContext = Depends(require_roles(*MANAGERS))):
    tz = await company_tz(user.company_id)
    today = local_today(tz)
    now = now_utc()
    now_minutes = int(hhmm_of(now, tz).split(":")[0]) * 60 + int(hhmm_of(now, tz).split(":")[1])
    start, end = day_bounds_utc(today, tz)

    employees = await db.employees.find({"company_id": user.company_id, "status": "ativo"}).sort("name", 1).to_list(500)
    records = await db.time_records.find(
        {"company_id": user.company_id, "timestamp": {"$gte": start, "$lt": end}}
    ).sort("timestamp", 1).to_list(5000)
    holidays = await holiday_map(user.company_id, today, today)
    holiday = holidays.get(today.isoformat())

    by_employee: dict[str, list[dict]] = {}
    for record in records:
        by_employee.setdefault(record["employee_id"], []).append(record)

    items: list[Alert] = []
    for employee in employees:
        docs = by_employee.get(employee["id"], [])
        resolve = await schedule_resolver(employee)
        schedule = resolve(today)
        summary = day_summary(today, docs, schedule, tz, holiday=holiday)
        if not summary["is_workday"]:
            continue  # folga ou feriado: nada a cobrar

        types = {d["type"] for d in docs}
        next_type = next_allowed_type(types)
        shift_end = parse_hhmm(schedule["saida"]) if schedule else None
        shift_start = parse_hhmm(schedule["entrada"]) if schedule else None

        # 1. Saída não registrada após o fim da jornada — a pendência pedida pelo usuário.
        if next_type == "saida" and shift_end is not None and now_minutes >= shift_end + GRACE_AFTER_SHIFT:
            items.append(
                Alert(
                    employee_id=employee["id"],
                    employee_name=employee["name"],
                    department=employee.get("department"),
                    kind="saida_nao_registrada",
                    severity="alta",
                    title="Saída não registrada",
                    detail=f"Jornada encerrava às {schedule['saida']} e a saída não foi registrada. Entrada às {summary['entrada']['hhmm'] or '—'}.",
                    date=today.isoformat(),
                    reference_hhmm=schedule["saida"],
                )
            )
        # 2. Intervalo aberto há muito tempo.
        elif next_type == "fim_intervalo":
            opened = summary["inicio_intervalo"]["hhmm"]
            opened_minutes = parse_hhmm(opened) if opened else None
            if opened_minutes is not None and now_minutes - opened_minutes >= MAX_INTERVAL:
                items.append(
                    Alert(
                        employee_id=employee["id"],
                        employee_name=employee["name"],
                        department=employee.get("department"),
                        kind="intervalo_aberto",
                        severity="media",
                        title="Intervalo em aberto",
                        detail=f"Saiu para intervalo às {opened} e ainda não registrou o retorno.",
                        date=today.isoformat(),
                        reference_hhmm=opened,
                    )
                )
        # 3. Nenhum registro em dia útil, já passado o horário de entrada.
        elif next_type == "entrada" and shift_start is not None and now_minutes >= shift_start + GRACE_AFTER_SHIFT:
            items.append(
                Alert(
                    employee_id=employee["id"],
                    employee_name=employee["name"],
                    department=employee.get("department"),
                    kind="sem_registro",
                    severity="alta" if now_minutes >= (shift_end or 1440) else "media",
                    title="Sem registro hoje",
                    detail=f"Entrada prevista às {schedule['entrada']} e nenhum registro foi feito até agora.",
                    date=today.isoformat(),
                    reference_hhmm=schedule["entrada"],
                )
            )

    # 4. Solicitações de ajuste pendentes — pendência de decisão do próprio gestor.
    pending = await db.time_adjustment_requests.find(
        {"company_id": user.company_id, "status": "pendente"}
    ).sort("created_at", -1).to_list(100)
    for request_doc in pending:
        items.append(
            Alert(
                employee_id=request_doc["employee_id"],
                employee_name=request_doc.get("employee_name", "—"),
                department=None,
                kind="solicitacao_pendente",
                severity="baixa",
                title="Solicitação aguardando decisão",
                detail=f"{TYPE_LABELS.get(request_doc['type'], request_doc['type'])} de {'/'.join(reversed(request_doc['target_date'].split('-')))} às {request_doc['requested_time']}.",
                date=request_doc["target_date"],
                reference_hhmm=request_doc["requested_time"],
            )
        )

    order = {"alta": 0, "media": 1, "baixa": 2}
    items.sort(key=lambda a: (order[a.severity], a.employee_name))
    return AlertsOut(
        local_date=today.isoformat(),
        server_time=now,
        total=len(items),
        high=sum(1 for a in items if a.severity == "alta"),
        alerts=items,
    )
