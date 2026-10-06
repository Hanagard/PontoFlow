"""Company models — the multi-tenant root. Everything else carries company_id (§5)."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from lib.timeutil import now_utc


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    cnpj: str | None = Field(default=None, max_length=32)
    timezone: str = "America/Belem"
    # First admin of the company — onboarding flow so a new company is immediately usable.
    admin_name: str = Field(min_length=2, max_length=120)
    admin_email: EmailStr
    admin_password: str = Field(min_length=6, max_length=72)


class CompanyOut(BaseModel):
    id: str
    name: str
    cnpj: str | None = None
    timezone: str
    status: str = "ativa"
    created_at: datetime = Field(default_factory=now_utc)
