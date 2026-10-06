"""User (login) models — roles per §6: super_admin | admin | gestor | funcionario."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from lib.timeutil import now_utc

Role = Literal["super_admin", "admin", "gestor", "funcionario"]


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    role: Role
    employee_id: str | None = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: Role
    company_id: str
    employee_id: str | None = None
    status: str = "ativo"
    created_at: datetime = Field(default_factory=now_utc)


class UserUpdate(BaseModel):
    role: Role | None = None
    status: Literal["ativo", "inativo"] | None = None
