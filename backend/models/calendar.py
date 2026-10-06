"""Holiday and schedule-assignment models (calendário da empresa + escalas)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from lib.timeutil import now_utc

HolidayKind = Literal["nacional", "estadual", "municipal", "facultativo"]


class HolidayCreate(BaseModel):
    date: str  # YYYY-MM-DD
    name: str = Field(min_length=2, max_length=120)
    kind: HolidayKind = "municipal"


class HolidayOut(BaseModel):
    id: str
    company_id: str
    date: str
    name: str
    kind: HolidayKind
    weekday: str
    created_at: datetime = Field(default_factory=now_utc)


class HolidayImportOut(BaseModel):
    year: int
    imported: int
    skipped: int
    holidays: list[HolidayOut]


class AssignmentCreate(BaseModel):
    """Escala: a jornada que vale para um funcionário dentro de um período."""

    employee_id: str
    schedule_id: str
    start_date: str  # YYYY-MM-DD
    end_date: str | None = None  # aberto = vigente até nova atribuição
    note: str | None = Field(default=None, max_length=200)


class AssignmentOut(BaseModel):
    id: str
    company_id: str
    employee_id: str
    employee_name: str
    schedule_id: str
    schedule_name: str
    start_date: str
    end_date: str | None = None
    note: str | None = None
    active: bool
    created_at: datetime = Field(default_factory=now_utc)
