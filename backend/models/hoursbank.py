"""Banco de horas and pendency-alert models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HoursBankMonth(BaseModel):
    competence: str
    label: str
    worked_minutes: int
    worked_hhmm: str | None = None
    expected_minutes: int
    expected_hhmm: str | None = None
    balance_minutes: int
    balance_hhmm: str | None = None
    overtime_minutes: int
    overtime_hhmm: str | None = None
    faltas: int
    incompletas: int
    closed: bool
    closed_at: datetime | None = None
    closed_by_name: str | None = None
    recalculated_balance_minutes: int | None = None


class HoursBankTotals(BaseModel):
    accumulated_minutes: int
    accumulated_hhmm: str | None = None
    credit_minutes: int
    credit_hhmm: str | None = None
    debit_minutes: int
    debit_hhmm: str | None = None
    to_compensate_minutes: int
    to_compensate_hhmm: str | None = None
    direction: Literal["credito", "debito", "zerado"]
    closed_months: int


class HoursBankOut(BaseModel):
    employee_id: str
    employee_name: str
    matricula: str | None = None
    department: str | None = None
    months: list[HoursBankMonth]
    totals: HoursBankTotals


class HoursBankBoardRow(BaseModel):
    employee_id: str
    employee_name: str
    matricula: str | None = None
    department: str | None = None
    current_competence: str
    current_balance_minutes: int
    current_balance_hhmm: str | None = None
    accumulated_minutes: int
    accumulated_hhmm: str | None = None
    to_compensate_hhmm: str | None = None
    direction: Literal["credito", "debito", "zerado"]
    closed_months: int


class HoursBankBoardOut(BaseModel):
    competence: str
    label: str
    months_considered: int
    rows: list[HoursBankBoardRow]


class CloseCompetenceIn(BaseModel):
    competence: str = Field(pattern=r"^\d{4}-\d{2}$")
    employee_id: str | None = None  # omitido = fecha para todos os funcionários ativos


class CloseCompetenceOut(BaseModel):
    competence: str
    label: str
    closed: int
    reopened: bool = False


class Alert(BaseModel):
    """Pendência do dia que o gestor precisa resolver."""

    employee_id: str
    employee_name: str
    department: str | None = None
    kind: Literal["saida_nao_registrada", "sem_registro", "intervalo_aberto", "jornada_incompleta", "solicitacao_pendente"]
    severity: Literal["alta", "media", "baixa"]
    title: str
    detail: str
    date: str
    reference_hhmm: str | None = None


class AlertsOut(BaseModel):
    local_date: str
    server_time: datetime
    total: int
    high: int
    alerts: list[Alert]
