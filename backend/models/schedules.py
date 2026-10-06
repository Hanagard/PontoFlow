"""Work schedule (jornada) models (§13) — wall-clock rules interpreted only by lib/calc."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from lib.timeutil import now_utc

ScheduleKind = Literal["fixa", "12x36", "6x1", "5x2"]


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    entrada: str
    inicio_intervalo: str
    fim_intervalo: str
    saida: str
    tolerance_minutes: int = Field(default=10, ge=0, le=120)
    work_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    # Escala rotativa: "fixa" usa work_days; 12x36/6x1/5x2 contam ciclo a partir da âncora.
    kind: ScheduleKind = "fixa"
    cycle_anchor: str | None = None  # YYYY-MM-DD — primeiro dia de trabalho do ciclo
    cycle_on_days: int | None = Field(default=None, ge=1, le=30)
    cycle_off_days: int | None = Field(default=None, ge=1, le=30)


class ScheduleOut(BaseModel):
    id: str
    company_id: str
    name: str
    entrada: str
    inicio_intervalo: str
    fim_intervalo: str
    saida: str
    tolerance_minutes: int = 10
    work_days: list[int]
    kind: ScheduleKind = "fixa"
    cycle_anchor: str | None = None
    cycle_on_days: int | None = None
    cycle_off_days: int | None = None
    expected_hhmm: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
