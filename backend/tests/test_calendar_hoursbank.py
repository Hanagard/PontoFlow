"""Unit tests for the Fase-15 domain additions: feriados, escalas rotativas, banco de horas."""

from datetime import date

from lib.calc import day_summary, is_scheduled_day, is_workday, summarize
from lib.holidays import easter, national_holidays
from lib.hoursbank import accumulate, competence_bounds, competence_label, competence_of, month_entry, recent_competences
from lib.timeutil import local_dt

TZ = "America/Belem"
SCHEDULE = {
    "name": "Comercial",
    "kind": "fixa",
    "entrada": "08:00",
    "inicio_intervalo": "12:00",
    "fim_intervalo": "13:00",
    "saida": "18:00",
    "tolerance_minutes": 10,
    "work_days": [0, 1, 2, 3, 4],
}
MONDAY = date(2026, 1, 5)


def punch(day: date, t: str, kind: str) -> dict:
    return {"type": kind, "timestamp": local_dt(day, t, TZ)}


def full_day(day: date, saida: str = "18:00") -> list[dict]:
    return [
        punch(day, "08:00", "entrada"),
        punch(day, "12:00", "inicio_intervalo"),
        punch(day, "13:00", "fim_intervalo"),
        punch(day, saida, "saida"),
    ]


# --- feriados ---

def test_easter_matches_known_years():
    assert easter(2026) == date(2026, 4, 5)
    assert easter(2027) == date(2027, 3, 28)


def test_national_holidays_include_fixed_and_movable():
    holidays = {h["date"]: h for h in national_holidays(2026)}
    assert holidays["2026-01-01"]["name"] == "Confraternização Universal"
    assert holidays["2026-12-25"]["name"] == "Natal"
    assert holidays["2026-04-03"]["name"] == "Paixão de Cristo"  # 2 dias antes da Páscoa
    assert holidays["2026-02-16"]["kind"] == "facultativo"  # Carnaval


def test_national_holiday_suspends_the_workday():
    holiday = {"name": "Natal", "kind": "nacional"}
    assert is_workday(MONDAY, SCHEDULE, holiday) is False
    assert is_workday(MONDAY, SCHEDULE, None) is True


def test_optional_holiday_keeps_the_obligation():
    """Ponto facultativo não pode apagar falta silenciosamente."""
    assert is_workday(MONDAY, SCHEDULE, {"name": "Carnaval", "kind": "facultativo"}) is True


def test_holiday_without_records_is_feriado_not_falta():
    summary = day_summary(MONDAY, [], SCHEDULE, TZ, holiday={"name": "Natal", "kind": "nacional"})
    assert summary["status"] == "feriado"
    assert summary["holiday_name"] == "Natal"
    assert summary["expected_minutes"] == 0
    assert summarize([summary])["faltas"] == 0


def test_work_on_holiday_is_all_overtime():
    summary = day_summary(MONDAY, full_day(MONDAY), SCHEDULE, TZ, holiday={"name": "Natal", "kind": "nacional"})
    assert summary["expected_minutes"] == 0
    assert summary["worked_minutes"] == 540
    assert summary["overtime_minutes"] == 540
    assert summary["balance_minutes"] == 540


def test_holiday_does_not_count_a_delay():
    summary = day_summary(MONDAY, [punch(MONDAY, "09:30", "entrada")], SCHEDULE, TZ, holiday={"name": "Natal", "kind": "nacional"})
    assert summary["delay_minutes"] == 0


# --- escalas rotativas ---

def test_12x36_alternates_days_from_the_anchor():
    schedule = {**SCHEDULE, "kind": "12x36", "cycle_anchor": "2026-01-05", "cycle_on_days": 1, "cycle_off_days": 1}
    pattern = [is_scheduled_day(date(2026, 1, d), schedule) for d in range(5, 12)]
    assert pattern == [True, False, True, False, True, False, True]


def test_12x36_works_on_weekends_unlike_a_fixed_schedule():
    schedule = {**SCHEDULE, "kind": "12x36", "cycle_anchor": "2026-01-05", "cycle_on_days": 1, "cycle_off_days": 1}
    sunday = date(2026, 1, 11)  # dia "on" do ciclo
    assert is_scheduled_day(sunday, schedule) is True
    assert is_scheduled_day(sunday, SCHEDULE) is False


def test_6x1_gives_one_rest_day_every_seven():
    schedule = {**SCHEDULE, "kind": "6x1", "cycle_anchor": "2026-01-05", "cycle_on_days": 6, "cycle_off_days": 1}
    pattern = [is_scheduled_day(date(2026, 1, d), schedule) for d in range(5, 19)]
    assert pattern.count(False) == 2  # 14 dias => 2 folgas
    assert pattern[6] is False and pattern[13] is False


def test_rotating_rest_day_is_folga_not_falta():
    schedule = {**SCHEDULE, "kind": "12x36", "cycle_anchor": "2026-01-05", "cycle_on_days": 1, "cycle_off_days": 1}
    off_day = date(2026, 1, 6)
    assert day_summary(off_day, [], schedule, TZ)["status"] == "folga"
    assert day_summary(date(2026, 1, 5), [], schedule, TZ)["status"] == "falta"


def test_12x36_expected_minutes_discount_the_interval():
    schedule = {**SCHEDULE, "kind": "12x36", "entrada": "07:00", "saida": "19:00", "cycle_anchor": "2026-01-05"}
    assert day_summary(date(2026, 1, 5), [], schedule, TZ)["expected_minutes"] == 660  # 12h - 1h


# --- banco de horas ---

def test_competence_helpers():
    assert competence_of(date(2026, 3, 17)) == "2026-03"
    assert competence_label("2026-03") == "Março de 2026"
    assert competence_bounds("2026-02") == (date(2026, 2, 1), date(2026, 2, 28))
    assert competence_bounds("2024-02")[1] == date(2024, 2, 29)  # ano bissexto
    assert competence_bounds("2026-12") == (date(2026, 12, 1), date(2026, 12, 31))


def test_recent_competences_walks_back_across_the_year():
    assert recent_competences(date(2026, 2, 10), 4) == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_month_entry_sums_daily_balances():
    days = [day_summary(MONDAY, full_day(MONDAY, "19:00"), SCHEDULE, TZ)]
    entry = month_entry("2026-01", days, None)
    assert entry["balance_minutes"] == 60
    assert entry["balance_hhmm"] == "01:00"
    assert entry["closed"] is False


def test_closed_competence_freezes_the_balance():
    """Editar um ponto antigo não pode reescrever um mês já fechado."""
    days = [day_summary(MONDAY, full_day(MONDAY, "20:00"), SCHEDULE, TZ)]  # recálculo = +120
    closure = {"balance_minutes": 60, "closed_at": None, "closed_by_name": "Rafael"}
    entry = month_entry("2026-01", days, closure)
    assert entry["balance_minutes"] == 60  # valor congelado prevalece
    assert entry["recalculated_balance_minutes"] == 120  # divergência fica visível
    assert entry["closed"] is True
    assert entry["closed_by_name"] == "Rafael"


def test_accumulate_splits_credit_and_debit():
    months = [
        {"balance_minutes": 120, "closed": True},
        {"balance_minutes": -45, "closed": False},
    ]
    totals = accumulate(months)
    assert totals["accumulated_minutes"] == 75
    assert totals["accumulated_hhmm"] == "01:15"
    assert totals["credit_minutes"] == 120
    assert totals["debit_minutes"] == 45
    assert totals["direction"] == "credito"
    assert totals["closed_months"] == 1


def test_accumulate_reports_debt_direction_and_amount_to_repay():
    totals = accumulate([{"balance_minutes": -90, "closed": False}])
    assert totals["direction"] == "debito"
    assert totals["to_compensate_hhmm"] == "01:30"


def test_accumulate_zeroed():
    totals = accumulate([{"balance_minutes": 60, "closed": False}, {"balance_minutes": -60, "closed": False}])
    assert totals["direction"] == "zerado"
    assert totals["to_compensate_minutes"] == 0
