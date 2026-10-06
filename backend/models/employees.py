"""Employee models (§7) — CPF is only shown masked in lists; full value nowhere in UI."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from lib.timeutil import now_utc


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    cpf: str = Field(min_length=11, max_length=20)
    matricula: str = Field(min_length=1, max_length=32)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    cargo: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=80)
    schedule_id: str | None = None
    status: Literal["ativo", "inativo"] = "ativo"
    hired_at: str | None = None  # YYYY-MM-DD
    # Optional login creation in the same transaction of the employee creation flow.
    create_login: bool = False
    login_password: str | None = Field(default=None, max_length=72)


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    cargo: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=80)
    schedule_id: str | None = None
    status: Literal["ativo", "inativo"] | None = None
    hired_at: str | None = None
    matricula: str | None = Field(default=None, min_length=1, max_length=32)


class EmployeeOut(BaseModel):
    id: str
    company_id: str
    user_id: str | None = None
    name: str
    cpf: str
    cpf_masked: str
    matricula: str
    email: str | None = None
    phone: str | None = None
    cargo: str | None = None
    department: str | None = None
    schedule_id: str | None = None
    schedule_name: str | None = None
    status: str = "ativo"
    hired_at: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
