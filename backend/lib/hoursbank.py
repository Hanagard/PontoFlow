"""Banco de horas (§ Fase 15.1) — monthly competence aggregation over the daily balance.

A "competence" is a YYYY-MM month. Its balance is the sum of the daily balances already
produced by lib/calc. Closing a competence freezes that number in `hours_bank_closures`,
so later edits to old punches cannot silently rewrite a month the admin already settled.

Accumulated = sum(closed snapshots) + sum(live balance of still-open months).
"""

from datetime import date, timedelta

from lib.timeutil import hhmm

MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def competence_of(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def competence_label(competence: str) -> str:
    year, month = competence.split("-")
    return f"{MONTHS_PT[int(month) - 1]} de {year}"


def competence_bounds(competence: str) -> tuple[date, date]:
    """First and last day of the competence month."""
    year, month = (int(p) for p in competence.split("-"))
    first = date(year, month, 1)
    last = date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)
    return first, last


def recent_competences(today: date, count: int) -> list[str]:
    """The last `count` competences ending at today's month, oldest first."""
    items: list[str] = []
    year, month = today.year, today.month
    for _ in range(count):
        items.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(items))


def month_entry(competence: str, days: list[dict], closure: dict | None) -> dict:
    """One row of the banco de horas for a single employee/month.

    When the competence is closed the frozen snapshot wins over the recalculation —
    that is the whole point of closing it.
    """
    worked = sum(d["worked_minutes"] or 0 for d in days)
    expected = sum(d["expected_minutes"] or 0 for d in days)
    live_balance = sum(d["balance_minutes"] or 0 for d in days)
    overtime = sum(d["overtime_minutes"] or 0 for d in days)
    balance = closure["balance_minutes"] if closure else live_balance

    return {
        "competence": competence,
        "label": competence_label(competence),
        "worked_minutes": worked,
        "worked_hhmm": hhmm(worked),
        "expected_minutes": expected,
        "expected_hhmm": hhmm(expected),
        "balance_minutes": balance,
        "balance_hhmm": hhmm(balance),
        "overtime_minutes": overtime,
        "overtime_hhmm": hhmm(overtime),
        "faltas": sum(1 for d in days if d["status"] == "falta"),
        "incompletas": sum(1 for d in days if d["status"] == "incompleta"),
        "closed": bool(closure),
        "closed_at": closure.get("closed_at") if closure else None,
        "closed_by_name": closure.get("closed_by_name") if closure else None,
        # Divergence between the frozen value and a recalculation — flags retroactive edits.
        "recalculated_balance_minutes": live_balance if closure else None,
    }


def accumulate(months: list[dict]) -> dict:
    """Totals for the banco de horas header: saldo acumulado e quanto há a compensar."""
    accumulated = sum(m["balance_minutes"] for m in months)
    credit = sum(m["balance_minutes"] for m in months if m["balance_minutes"] > 0)
    debit = sum(-m["balance_minutes"] for m in months if m["balance_minutes"] < 0)
    return {
        "accumulated_minutes": accumulated,
        "accumulated_hhmm": hhmm(accumulated),
        "credit_minutes": credit,
        "credit_hhmm": hhmm(credit),
        "debit_minutes": debit,
        "debit_hhmm": hhmm(debit),
        # Positive => horas a receber/compensar pelo funcionário; negative => horas a repor.
        "to_compensate_minutes": abs(accumulated),
        "to_compensate_hhmm": hhmm(abs(accumulated)),
        "direction": "credito" if accumulated > 0 else "debito" if accumulated < 0 else "zerado",
        "closed_months": sum(1 for m in months if m["closed"]),
    }
