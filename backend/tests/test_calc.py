"""Unit tests for the domain calculation layer (§24) — pure functions, no HTTP, no Mongo."""

from datetime import date, datetime, timezone

from lib.calc import day_summary, expected_minutes, next_allowed_type, summarize
from lib.timeutil import hhmm, local_dt, parse_hhmm
from lib.validators import cpf_masked, cpf_valid, hhmm_valid

TZ = "America/Belem"
SCHEDULE = {
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


# --- sequência de registros (§8) ---

def test_next_type_follows_canonical_order():
    assert next_allowed_type(set()) == "entrada"
    assert next_allowed_type({"entrada"}) == "inicio_intervalo"
    assert next_allowed_type({"entrada", "inicio_intervalo"}) == "fim_intervalo"
    assert next_allowed_type({"entrada", "inicio_intervalo", "fim_intervalo"}) == "saida"


def test_next_type_is_none_when_day_is_complete():
    assert next_allowed_type({"entrada", "inicio_intervalo", "fim_intervalo", "saida"}) is None


# --- jornada prevista (§13/§14) ---

def test_expected_minutes_discounts_the_interval():
    assert expected_minutes(SCHEDULE) == 540  # 10h - 1h intervalo = 9h? no: 08->18 = 600 - 60
    assert expected_minutes(None) == 0


def test_expected_minutes_handles_night_shift_past_midnight():
    night = {**SCHEDULE, "entrada": "22:00", "inicio_intervalo": "01:00", "fim_intervalo": "02:00", "saida": "06:00"}
    assert expected_minutes(night) == 420


# --- cálculo do dia (§14) ---

def test_complete_day_on_schedule_has_zero_balance():
    records = [
        punch(MONDAY, "08:00", "entrada"),
        punch(MONDAY, "12:00", "inicio_intervalo"),
        punch(MONDAY, "13:00", "fim_intervalo"),
        punch(MONDAY, "18:00", "saida"),
    ]
    summary = day_summary(MONDAY, records, SCHEDULE, TZ)
    assert summary["status"] == "completa"
    assert summary["worked_minutes"] == 540
    assert summary["balance_minutes"] == 0
    assert summary["delay_minutes"] == 0
    assert summary["overtime_minutes"] == 0


def test_delay_respects_tolerance_then_counts():
    within = day_summary(MONDAY, [punch(MONDAY, "08:08", "entrada")], SCHEDULE, TZ)
    assert within["delay_minutes"] == 0  # 8 min < tolerância de 10
    late = day_summary(MONDAY, [punch(MONDAY, "08:35", "entrada")], SCHEDULE, TZ)
    assert late["delay_minutes"] == 25  # 35 - 10 de tolerância


def test_overtime_counted_when_leaving_late():
    records = [
        punch(MONDAY, "08:00", "entrada"),
        punch(MONDAY, "12:00", "inicio_intervalo"),
        punch(MONDAY, "13:00", "fim_intervalo"),
        punch(MONDAY, "19:30", "saida"),
    ]
    summary = day_summary(MONDAY, records, SCHEDULE, TZ)
    assert summary["overtime_minutes"] == 90
    assert summary["balance_hhmm"] == "01:30"


def test_early_leave_produces_negative_balance():
    records = [
        punch(MONDAY, "08:00", "entrada"),
        punch(MONDAY, "12:00", "inicio_intervalo"),
        punch(MONDAY, "13:00", "fim_intervalo"),
        punch(MONDAY, "17:00", "saida"),
    ]
    summary = day_summary(MONDAY, records, SCHEDULE, TZ)
    assert summary["balance_minutes"] == -60
    assert summary["balance_hhmm"] == "-01:00"
    assert summary["overtime_minutes"] == 0


def test_incomplete_day_is_flagged_and_balance_unknown():
    records = [punch(MONDAY, "08:00", "entrada"), punch(MONDAY, "12:00", "inicio_intervalo")]
    summary = day_summary(MONDAY, records, SCHEDULE, TZ)
    assert summary["status"] == "incompleta"
    assert summary["balance_minutes"] is None
    assert summary["worked_minutes"] == 240


def test_missing_day_on_workday_is_falta_and_justification_changes_status():
    assert day_summary(MONDAY, [], SCHEDULE, TZ)["status"] == "falta"
    assert day_summary(MONDAY, [], SCHEDULE, TZ, justified=True)["status"] == "justificada"


def test_weekend_without_records_is_folga_not_falta():
    saturday = date(2026, 1, 10)
    summary = day_summary(saturday, [], SCHEDULE, TZ)
    assert summary["status"] == "folga"
    assert summary["expected_minutes"] == 0


def test_interval_time_is_not_paid():
    records = [
        punch(MONDAY, "08:00", "entrada"),
        punch(MONDAY, "12:00", "inicio_intervalo"),
        punch(MONDAY, "14:00", "fim_intervalo"),  # 2h de intervalo
        punch(MONDAY, "18:00", "saida"),
    ]
    assert day_summary(MONDAY, records, SCHEDULE, TZ)["worked_minutes"] == 480


# --- totais do período (§15) ---

def test_summarize_accumulates_period_totals():
    complete = [
        punch(MONDAY, "08:00", "entrada"),
        punch(MONDAY, "12:00", "inicio_intervalo"),
        punch(MONDAY, "13:00", "fim_intervalo"),
        punch(MONDAY, "19:00", "saida"),
    ]
    days = [day_summary(MONDAY, complete, SCHEDULE, TZ), day_summary(date(2026, 1, 6), [], SCHEDULE, TZ)]
    totals = summarize(days)
    assert totals["total_overtime_minutes"] == 60
    assert totals["faltas"] == 1


# --- utilidades de tempo e validação (§9/§23) ---

def test_local_dt_converts_company_wall_clock_to_utc():
    assert local_dt(MONDAY, "08:00", TZ) == datetime(2026, 1, 5, 11, 0, tzinfo=timezone.utc)  # Belém = UTC-3


def test_hhmm_roundtrip_and_negative_format():
    assert parse_hhmm("08:30") == 510
    assert hhmm(510) == "08:30"
    assert hhmm(-90) == "-01:30"


def test_cpf_validation_and_masking():
    assert cpf_valid("529.982.247-25")
    assert not cpf_valid("111.111.111-11")
    assert not cpf_valid("123")
    assert cpf_masked("52998224725") == "***.982.***-25"


def test_hhmm_validator_rejects_garbage():
    assert hhmm_valid("23:59")
    assert not hhmm_valid("24:00")
    assert not hhmm_valid("8:00")
    assert not hhmm_valid("")


def test_expected_minutes_supports_overnight_schedule():
    schedule = {"entrada": "22:00", "inicio_intervalo": "02:00", "fim_intervalo": "03:00", "saida": "06:00"}
    from lib.calc import expected_minutes
    assert expected_minutes(schedule) == 420


def test_day_summary_overnight_records_are_calculated_by_real_instants():
    from datetime import datetime, timezone
    from lib.calc import day_summary
    schedule = {"entrada": "22:00", "inicio_intervalo": "02:00", "fim_intervalo": "03:00", "saida": "06:00", "tolerance_minutes": 10, "work_days": [0,1,2,3,4], "kind": "fixa"}
    records = [
        {"type": "entrada", "timestamp": datetime(2026, 10, 5, 22, 0, tzinfo=timezone.utc)},
        {"type": "inicio_intervalo", "timestamp": datetime(2026, 10, 6, 2, 0, tzinfo=timezone.utc)},
        {"type": "fim_intervalo", "timestamp": datetime(2026, 10, 6, 3, 0, tzinfo=timezone.utc)},
        {"type": "saida", "timestamp": datetime(2026, 10, 6, 6, 0, tzinfo=timezone.utc)},
    ]
    summary = day_summary(date(2026, 10, 5), records, schedule, "UTC")
    assert summary["status"] == "completa"
    assert summary["worked_minutes"] == 420
