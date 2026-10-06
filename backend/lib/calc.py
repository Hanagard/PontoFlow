"""Domain calculation layer (§14) — ALL jornada math lives here, never in React components.

Pure functions over plain dicts so they are unit-testable without Mongo or HTTP:
records  = [{"type": "entrada", "timestamp": <aware-utc datetime>}, ...]
schedule = {"kind": "fixa", "entrada": "08:00", "inicio_intervalo": "12:00",
            "fim_intervalo": "13:00", "saida": "18:00", "tolerance_minutes": 10,
            "work_days": [0, 1, 2, 3, 4]}
           # rotativa: {"kind": "12x36"|"6x1", "cycle_anchor": "2026-01-05",
           #            "cycle_on_days": 1, "cycle_off_days": 1}
holiday  = {"name": "Natal", "kind": "nacional"} | None
"""

from datetime import date, datetime

from lib.timeutil import hhmm, hhmm_of, parse_hhmm

TYPES = ("entrada", "inicio_intervalo", "fim_intervalo", "saida")
TYPE_LABELS = {
    "entrada": "Entrada",
    "inicio_intervalo": "Saída para Intervalo",
    "fim_intervalo": "Retorno do Intervalo",
    "saida": "Saída",
}
NEXT_TYPE = {"entrada": "inicio_intervalo", "inicio_intervalo": "fim_intervalo", "fim_intervalo": "saida", "saida": None}
WEEKDAYS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

# Rotating shift presets: on/off days per cycle. "fixa" uses work_days instead.
CYCLE_PRESETS = {"12x36": (1, 1), "6x1": (6, 1), "5x2": (5, 2)}
SCHEDULE_KINDS = ("fixa", *CYCLE_PRESETS.keys())


def next_allowed_type(types_so_far: set[str]) -> str | None:
    """Next event the employee is allowed to register (§8).

    The canonical order is entrada -> inicio_intervalo -> fim_intervalo -> saida; the first
    missing type is always the allowed one. Skipping the interval is tolerated (jornada sem
    intervalo), but duplicating an event or going backwards never is — both surface as the
    same clear 400 from the router.
    """
    for t in TYPES:
        if t not in types_so_far:
            return t
    return None


def expected_minutes(schedule: dict | None) -> int:
    """Prevista = (saída - entrada) - intervalo; supports schedules past midnight."""
    if not schedule:
        return 0
    total = (parse_hhmm(schedule["saida"]) - parse_hhmm(schedule["entrada"])) % 1440
    interval = (parse_hhmm(schedule["fim_intervalo"]) - parse_hhmm(schedule["inicio_intervalo"])) % 1440
    return max(0, total - interval)


def cycle_days(schedule: dict) -> tuple[int, int]:
    kind = schedule.get("kind", "fixa")
    if kind in CYCLE_PRESETS:
        preset = CYCLE_PRESETS[kind]
        return int(schedule.get("cycle_on_days") or preset[0]), int(schedule.get("cycle_off_days") or preset[1])
    return 0, 0


def is_scheduled_day(day: date, schedule: dict | None) -> bool:
    """Is this a day the employee is supposed to work, ignoring holidays?

    "fixa" uses the weekday list; rotating shifts (12x36, 6x1, 5x2) count on/off days from
    `cycle_anchor`, so the pattern walks across weekdays exactly like the real scale does.
    """
    if not schedule:
        return day.weekday() < 5
    if schedule.get("kind", "fixa") in CYCLE_PRESETS:
        on, off = cycle_days(schedule)
        if on + off <= 0:
            return False
        try:
            anchor = date.fromisoformat(schedule["cycle_anchor"])
        except (KeyError, TypeError, ValueError):
            anchor = day
        return ((day - anchor).days % (on + off)) < on
    days = schedule.get("work_days")
    return day.weekday() in (set(days) if days else {0, 1, 2, 3, 4})


def is_workday(day: date, schedule: dict | None, holiday: dict | None = None) -> bool:
    """Effective working day: scheduled AND not a holiday that suspends work.

    A `facultativo` (optional) holiday does NOT remove the obligation — only nacional,
    estadual and municipal do. That keeps "ponto facultativo" from silently erasing faltas.
    """
    if holiday and holiday.get("kind") != "facultativo":
        return False
    return is_scheduled_day(day, schedule)


def _minutes_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def day_summary(
    day: date,
    records: list[dict],
    schedule: dict | None,
    tz: str,
    justified: bool = False,
    holiday: dict | None = None,
) -> dict:
    """One day of the espelho: worked/expected/delay/overtime/balance/status (§15).

    `records` are ONE employee's punches whose local date (in `tz`) is `day`.
    On a holiday the expected time is zero, so everything worked lands as overtime.
    """
    stamps: dict[str, datetime] = {}
    for r in sorted(records, key=lambda r: r["timestamp"]):
        stamps.setdefault(r["type"], r["timestamp"])

    def slot(t: str) -> dict:
        ts = stamps.get(t)
        return {"timestamp": ts.isoformat() if ts else None, "hhmm": hhmm_of(ts, tz) if ts else None}

    workday = is_workday(day, schedule, holiday)
    exp = expected_minutes(schedule) if workday else 0
    complete = all(t in stamps for t in TYPES)

    worked: int | None = None
    if stamps:
        if complete:
            worked = _minutes_between(stamps["entrada"], stamps["inicio_intervalo"]) + _minutes_between(
                stamps["fim_intervalo"], stamps["saida"]
            )
        else:
            # Partial day: only contiguous segments count (entrada->intervalo, retorno->saida).
            worked = 0
            if "entrada" in stamps and "inicio_intervalo" in stamps:
                worked += _minutes_between(stamps["entrada"], stamps["inicio_intervalo"])
            if "fim_intervalo" in stamps and "saida" in stamps:
                worked += _minutes_between(stamps["fim_intervalo"], stamps["saida"])

    delay = 0
    if schedule and workday and "entrada" in stamps:
        local = stamps["entrada"].astimezone(_tz(tz))
        actual = local.hour * 60 + local.minute
        target = parse_hhmm(schedule["entrada"])
        delay = max(0, actual - target - schedule.get("tolerance_minutes", 0))

    if not stamps:
        if holiday and holiday.get("kind") != "facultativo":
            status = "feriado"
        elif justified:
            status = "justificada"
        elif workday:
            status = "falta"
        else:
            status = "folga"
        worked = 0
    elif complete:
        status = "completa"
    else:
        status = "incompleta"

    overtime = max(0, worked - exp) if (complete and schedule) else None
    balance = (worked - exp) if (complete and schedule) else None

    return {
        "date": day.isoformat(),
        "weekday": WEEKDAYS_PT[day.weekday()],
        "is_workday": workday,
        "holiday_name": (holiday or {}).get("name"),
        "schedule_name": (schedule or {}).get("name"),
        "entrada": slot("entrada"),
        "inicio_intervalo": slot("inicio_intervalo"),
        "fim_intervalo": slot("fim_intervalo"),
        "saida": slot("saida"),
        "worked_minutes": worked,
        "worked_hhmm": hhmm(worked),
        "expected_minutes": exp,
        "expected_hhmm": hhmm(exp),
        "delay_minutes": delay,
        "delay_hhmm": hhmm(delay),
        "overtime_minutes": overtime,
        "overtime_hhmm": hhmm(overtime),
        "balance_minutes": balance,
        "balance_hhmm": hhmm(balance),
        "status": status,
        "justified": justified,
    }


def _tz(tz: str):
    from zoneinfo import ZoneInfo

    return ZoneInfo(tz)


def summarize(days: list[dict]) -> dict:
    """Range totals for the espelho header (§15/§26)."""
    def total(field: str) -> int:
        return sum(d[field] or 0 for d in days if isinstance(d.get(field), int))

    return {
        "total_worked_minutes": total("worked_minutes"),
        "total_expected_minutes": total("expected_minutes"),
        "total_balance_minutes": total("balance_minutes"),
        "total_overtime_minutes": total("overtime_minutes"),
        "total_delay_minutes": total("delay_minutes"),
        "faltas": sum(1 for d in days if d["status"] == "falta"),
        "incompletas": sum(1 for d in days if d["status"] == "incompleta"),
        "feriados": sum(1 for d in days if d["status"] == "feriado"),
    }


def timesheet_csv(days: list[dict], summary: dict) -> str:
    """Espelho as BR-flavored CSV (';' separator + BOM so Excel opens it right)."""
    header = ["Data", "Dia", "Entrada", "Saída Intervalo", "Retorno", "Saída", "Trabalhado", "Previsto", "Atraso", "Extras", "Saldo", "Status", "Observação"]
    lines = [";".join(header)]
    for d in days:
        lines.append(
            ";".join(
                [
                    d["date"],
                    d["weekday"],
                    d["entrada"]["hhmm"] or "",
                    d["inicio_intervalo"]["hhmm"] or "",
                    d["fim_intervalo"]["hhmm"] or "",
                    d["saida"]["hhmm"] or "",
                    d["worked_hhmm"] or "",
                    d["expected_hhmm"] or "",
                    d["delay_hhmm"] or "",
                    d["overtime_hhmm"] or "",
                    d["balance_hhmm"] or "",
                    d["status"],
                    d.get("holiday_name") or "",
                ]
            )
        )
    lines.append("")
    lines.append(";".join(["TOTAIS", "", "", "", "", "", hhmm(summary["total_worked_minutes"]) or "", hhmm(summary["total_expected_minutes"]) or "", hhmm(summary["total_delay_minutes"]) or "", hhmm(summary["total_overtime_minutes"]) or "", hhmm(summary["total_balance_minutes"]) or "", "", ""]))
    return "\ufeff" + "\n".join(lines)
