"""Time record + adjustment request models (§10, §12)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from lib.timeutil import now_utc

RecordType = Literal["entrada", "inicio_intervalo", "fim_intervalo", "saida"]


class PunchCreate(BaseModel):
    """The client sends NO timestamp — the server owns the official time (§9)."""

    observacao: str | None = Field(default=None, max_length=300)
    latitude: float | None = None
    longitude: float | None = None
    accuracy: float | None = None


class TimeRecordOut(BaseModel):
    id: str
    company_id: str
    employee_id: str
    type: RecordType
    type_label: str
    timestamp: datetime
    timezone: str
    hhmm: str
    local_date: str
    origin: str = "web"
    status: str = "valido"
    observacao: str | None = None
    adjusted: bool = False
    created_at: datetime = Field(default_factory=now_utc)


class PunchStatusOut(BaseModel):
    """Everything the employee console needs, all server-derived."""

    server_time: datetime
    server_hhmm: str
    local_date: str
    timezone: str
    employee_name: str
    schedule_name: str | None = None
    schedule_label: str | None = None
    next_type: RecordType | None = None
    next_label: str | None = None
    status_label: str
    records: list[TimeRecordOut]
    worked_hhmm: str | None = None
    expected_hhmm: str | None = None


class AdjustmentCreate(BaseModel):
    target_date: str  # YYYY-MM-DD
    type: RecordType
    requested_time: str  # HH:MM (company timezone)
    reason: str = Field(min_length=5, max_length=500)


class AdjustmentDecision(BaseModel):
    decision: Literal["aprovada", "rejeitada"]
    note: str | None = Field(default=None, max_length=500)


class AdjustmentOut(BaseModel):
    id: str
    company_id: str
    employee_id: str
    employee_name: str
    target_date: str
    type: RecordType
    type_label: str
    requested_time: str
    previous_time: str | None = None
    reason: str
    status: Literal["pendente", "aprovada", "rejeitada", "cancelada"]
    decided_by_name: str | None = None
    decision_note: str | None = None
    decided_at: datetime | None = None
    created_at: datetime = Field(default_factory=now_utc)
