"""Audit trail writer (§11) — every relevant change inserts one append-only event.

There is deliberately NO endpoint that updates or deletes audit_logs: common users cannot
erase their own trail, and even admins only get a read view.
"""

from pydantic import BaseModel
from lib.timeutil import now_utc

from lib.db import db

AUDIT_ACTIONS = {
    "LOGIN",
    "LOGIN_FALHA",
    "LOGOUT",
    "USUARIO_CRIADO",
    "PERMISSAO_ALTERADA",
    "EMPRESA_CRIADA",
    "FUNCIONARIO_CRIADO",
    "FUNCIONARIO_ATUALIZADO",
    "JORNADA_CRIADA",
    "JORNADA_ATUALIZADA",
    "PONTO_REGISTRADO",
    "PONTO_CORRIGIDO",
    "SOLICITACAO_CRIADA",
    "SOLICITACAO_APROVADA",
    "SOLICITACAO_REJEITADA",
    "SOLICITACAO_CANCELADA",
    "FERIADO_CRIADO",
    "FERIADOS_IMPORTADOS",
    "FERIADO_REMOVIDO",
    "ESCALA_ATRIBUIDA",
    "ESCALA_REMOVIDA",
    "COMPETENCIA_FECHADA",
    "COMPETENCIA_REABERTA",
}


class AuditActor(BaseModel):
    id: str
    name: str
    role: str


async def write_audit(
    *,
    company_id: str,
    actor: AuditActor | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    if action not in AUDIT_ACTIONS:
        raise ValueError(f"unknown audit action: {action}")
    doc = {
        "id": __import__("uuid").uuid4().hex,
        "company_id": company_id,
        "actor_id": actor.id if actor else None,
        "actor_name": actor.name if actor else "sistema",
        "actor_role": actor.role if actor else "sistema",
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "before": before,
        "after": after,
        "ip": ip,
        "user_agent": (user_agent or "")[:250] or None,
        "created_at": now_utc(),
    }
    await db.audit_logs.insert_one(doc)
