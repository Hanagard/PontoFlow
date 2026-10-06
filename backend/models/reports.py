"""Timesheet (espelho), dashboard and audit response models (§15, §16, §11)."""

from datetime import datetime

from pydantic import BaseModel


class DaySlot(BaseModel):
    timestamp: str | None = None
    hhmm: str | None = None


class TimesheetDay(BaseModel):
    date: str
    weekday: str
    is_workday: bool
    holiday_name: str | None = None
    schedule_name: str | None = None
    entrada: DaySlot
    inicio_intervalo: DaySlot
    fim_intervalo: DaySlot
    saida: DaySlot
    worked_minutes: int | None = None
    worked_hhmm: str | None = None
    expected_minutes: int
    expected_hhmm: str | None = None
    delay_minutes: int
    delay_hhmm: str | None = None
    overtime_minutes: int | None = None
    overtime_hhmm: str | None = None
    balance_minutes: int | None = None
    balance_hhmm: str | None = None
    status: str
    justified: bool = False


class TimesheetSummary(BaseModel):
    total_worked_minutes: int
    total_worked_hhmm: str | None = None
    total_expected_minutes: int
    total_expected_hhmm: str | None = None
    total_balance_minutes: int
    total_balance_hhmm: str | None = None
    total_overtime_minutes: int
    total_overtime_hhmm: str | None = None
    total_delay_minutes: int
    total_delay_hhmm: str | None = None
    faltas: int
    incompletas: int
    feriados: int = 0


class TimesheetOut(BaseModel):
    employee_id: str
    employee_name: str
    matricula: str | None = None
    department: str | None = None
    schedule_name: str | None = None
    timezone: str
    start: str
    end: str
    days: list[TimesheetDay]
    summary: TimesheetSummary


class DashboardOut(BaseModel):
    company_name: str
    local_date: str
    server_time: datetime
    employees_active: int
    present_now: int
    on_interval: int
    absent: int
    delayed: int
    incomplete_days: int
    pending_requests: int
    overtime_hhmm: str
    balance_hhmm: str
    today_records: int
    holiday_name: str | None = None
    alerts_total: int = 0
    alerts_high: int = 0
    hours_bank_hhmm: str = "00:00"


class AuditOut(BaseModel):
    id: str
    company_id: str
    actor_name: str
    actor_role: str
    action: str
    resource: str
    resource_id: str | None = None
    before: dict | None = None
    after: dict | None = None
    ip: str | None = None
    created_at: datetime


class ReportRow(BaseModel):
    employee_id: str
    employee_name: str
    matricula: str | None = None
    department: str | None = None
    worked_hhmm: str
    expected_hhmm: str
    balance_hhmm: str
    overtime_hhmm: str
    delay_hhmm: str
    faltas: int
    incompletas: int


class ReportOut(BaseModel):
    kind: str
    start: str
    end: str
    rows: list[ReportRow]
