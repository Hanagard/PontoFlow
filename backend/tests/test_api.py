"""Integration tests for critical endpoints (§24): auth, RBAC, punch sequence, tenant isolation.

These hit the live uvicorn process via the `client` fixture and rely on the demo seed
(cd /app/backend && python seed.py).
"""

import os
from contextlib import contextmanager

import httpx
import pytest

API_URL = f"{os.environ.get('BACKEND_URL', 'http://localhost:8001')}/api"

ADMIN = {"email": "admin@pontoflow.com.br", "password": "Ponto@2026"}
GESTOR = {"email": "gestor@pontoflow.com.br", "password": "Ponto@2026"}
FUNCIONARIO = {"email": "maria.silva@pontoflow.com.br", "password": "Ponto@2026"}


@contextmanager
def session(creds: dict):
    """Authenticated client; the login response sets the httpOnly session cookie on it."""
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        res = c.post("/auth/login", json=creds)
        assert res.status_code == 200, res.text
        yield c


# --- autenticação (§19) ---

def test_login_rejects_wrong_password_without_leaking_account_existence(client):
    res = client.post("/auth/login", json={"email": ADMIN["email"], "password": "errada"})
    assert res.status_code == 401
    assert res.json()["detail"] == "E-mail ou senha inválidos."


def test_login_sets_httponly_cookie_and_returns_no_token(client):
    res = client.post("/auth/login", json=ADMIN)
    assert res.status_code == 200
    body = res.json()
    assert "password" not in body and "token" not in body
    assert body["role"] == "admin"
    assert "pf_session" in res.cookies or any("pf_session" in h for h in res.headers.get_list("set-cookie"))


def test_me_requires_session(client):
    assert client.get("/auth/me").status_code == 401


def test_protected_endpoints_reject_anonymous(client):
    for path in ("/employees", "/dashboard", "/time-records/today", "/timesheet", "/audit-logs"):
        assert client.get(path).status_code == 401, path


# --- autorização por perfil (§6) ---

def test_funcionario_cannot_list_employees_or_dashboard():
    with session(FUNCIONARIO) as c:
        assert c.get("/employees").status_code == 403
        assert c.get("/dashboard").status_code == 403
        assert c.get("/audit-logs").status_code == 403


def test_funcionario_cannot_create_employee():
    with session(FUNCIONARIO) as c:
        res = c.post("/employees", json={"name": "Invasor", "cpf": "52998224725", "matricula": "9999"})
        assert res.status_code == 403


def test_gestor_can_read_team_but_not_create_employee():
    with session(GESTOR) as c:
        assert c.get("/employees").status_code == 200
        res = c.post("/employees", json={"name": "Novo", "cpf": "52998224725", "matricula": "9998"})
        assert res.status_code == 403


def test_funcionario_cannot_read_another_employee_record():
    with session(FUNCIONARIO) as c:
        res = c.get("/employees/emp-carlos")
        assert res.status_code == 403


def test_funcionario_timesheet_is_always_their_own():
    with session(FUNCIONARIO) as c:
        res = c.get("/timesheet", params={"employee_id": "emp-carlos"})
        assert res.status_code == 200
        assert res.json()["employee_id"] == "emp-maria"  # o filtro do cliente é ignorado


# --- sequência de registros e horário do servidor (§8/§9) ---

def test_today_status_is_server_derived():
    with session(FUNCIONARIO) as c:
        res = c.get("/time-records/today")
        assert res.status_code == 200
        body = res.json()
        assert body["timezone"] == "America/Belem"
        assert body["next_type"] in ("entrada", "inicio_intervalo", "fim_intervalo", "saida", None)
        assert body["server_hhmm"]


def test_punch_sequence_advances_and_blocks_duplicates():
    with session(FUNCIONARIO) as c:
        # Clean slate is not guaranteed; drive from whatever the server says is next.
        for _ in range(4):
            status = c.get("/time-records/today").json()
            if status["next_type"] is None:
                break
            expected = status["next_type"]
            res = c.post("/time-records", json={})
            assert res.status_code == 201, res.text
            assert res.json()["type"] == expected  # o servidor escolhe o tipo, não o cliente
        # Day complete -> any further punch is a clear 400, never a silent duplicate.
        assert c.get("/time-records/today").json()["next_type"] is None
        res = c.post("/time-records", json={})
        assert res.status_code == 400
        assert "completa" in res.json()["detail"].lower()


def test_client_cannot_inject_timestamp():
    with session(FUNCIONARIO) as c:
        res = c.post("/time-records", json={"timestamp": "1999-01-01T00:00:00Z", "type": "saida"})
        # Either the day is already complete (400) or the punch is created with the server clock.
        assert res.status_code in (201, 400)
        if res.status_code == 201:
            assert not res.json()["timestamp"].startswith("1999")


# --- solicitações de ajuste (§12) ---

def test_adjustment_flow_requires_approval_to_change_ponto():
    with session(FUNCIONARIO) as c:
        created = c.post(
            "/adjustment-requests",
            json={"target_date": "2026-01-05", "type": "saida", "requested_time": "18:10", "reason": "Esqueci de registrar a saída."},
        )
        assert created.status_code in (201, 409)
        if created.status_code == 201:
            assert created.json()["status"] == "pendente"

    with session(FUNCIONARIO) as c:
        res = c.get("/adjustment-requests")
        assert res.status_code == 200
        assert all(r["employee_id"] == "emp-maria" for r in res.json())


def test_funcionario_cannot_approve_own_request():
    with session(GESTOR) as c:
        pending = c.get("/adjustment-requests", params={"status": "pendente"}).json()
    if not pending:
        pytest.skip("sem solicitações pendentes no seed")
    with session(FUNCIONARIO) as c:
        res = c.patch(f"/adjustment-requests/{pending[0]['id']}", json={"decision": "aprovada"})
        assert res.status_code == 403


def test_adjustment_rejects_invalid_time_and_future_date():
    with session(FUNCIONARIO) as c:
        bad_time = c.post(
            "/adjustment-requests",
            json={"target_date": "2026-01-06", "type": "entrada", "requested_time": "99:99", "reason": "teste invalido"},
        )
        assert bad_time.status_code == 400
        future = c.post(
            "/adjustment-requests",
            json={"target_date": "2090-01-01", "type": "entrada", "requested_time": "08:00", "reason": "data futura teste"},
        )
        assert future.status_code == 400


# --- validação de entrada (§23) ---

def test_employee_creation_validates_cpf():
    with session(ADMIN) as c:
        res = c.post("/employees", json={"name": "CPF Ruim", "cpf": "11111111111", "matricula": "7777"})
        assert res.status_code == 400
        assert "CPF" in res.json()["detail"]


def test_schedule_creation_validates_hhmm():
    with session(ADMIN) as c:
        res = c.post(
            "/schedules",
            json={"name": "Jornada Ruim", "entrada": "8h", "inicio_intervalo": "12:00", "fim_intervalo": "13:00", "saida": "18:00"},
        )
        assert res.status_code == 400


def test_employee_list_never_exposes_full_cpf():
    with session(ADMIN) as c:
        employees = c.get("/employees").json()
        assert employees
        for e in employees:
            assert "*" in e["cpf"], e["cpf"]


# --- isolamento entre empresas (§5) ---

def test_cross_company_data_is_invisible():
    other = {"company_name": "Empresa Isolada SA", "name": "Admin Isolado", "email": "isolado@teste-tenant.com.br", "password": "Teste@2026"}
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        res = c.post("/auth/signup", json=other)
        if res.status_code == 409:
            res = c.post("/auth/login", json={"email": other["email"], "password": other["password"]})
        assert res.status_code == 200
        # A brand-new tenant sees zero employees from the demo company, even by direct id.
        assert c.get("/employees").json() == []
        assert c.get("/employees/emp-maria").status_code == 404
        assert c.get("/timesheet", params={"employee_id": "emp-maria"}).status_code in (400, 404)
        assert c.get("/audit-logs").json() != []  # mas vê a própria trilha
        assert all(log["company_id"] != "demo-pontoflow-company" for log in c.get("/audit-logs").json())


# --- auditoria (§11) ---

def test_audit_trail_records_actions_and_has_no_delete_route():
    with session(ADMIN) as c:
        logs = c.get("/audit-logs").json()
        assert logs
        assert any(log["action"] == "LOGIN" for log in logs)
        assert c.delete(f"/audit-logs/{logs[0]['id']}").status_code in (404, 405)


# --- espelho e relatórios (§15/§26) ---

def test_timesheet_returns_days_and_summary():
    with session(ADMIN) as c:
        res = c.get("/timesheet", params={"employee_id": "emp-maria", "start": "2026-01-01", "end": "2026-01-10"})
        assert res.status_code == 200
        body = res.json()
        assert len(body["days"]) == 10
        assert "total_worked_hhmm" in body["summary"]


def test_timesheet_rejects_invalid_period():
    with session(ADMIN) as c:
        res = c.get("/timesheet", params={"employee_id": "emp-maria", "start": "2026-01-10", "end": "2026-01-01"})
        assert res.status_code == 400


def test_csv_export_is_generated_on_the_backend():
    with session(ADMIN) as c:
        res = c.get("/timesheet/export", params={"employee_id": "emp-maria"})
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert "Data;Dia;Entrada" in res.text


def test_reports_and_dashboard_for_manager():
    with session(GESTOR) as c:
        dash = c.get("/dashboard")
        assert dash.status_code == 200
        assert dash.json()["employees_active"] >= 1
        rep = c.get("/reports", params={"kind": "atrasos"})
        assert rep.status_code == 200
        assert rep.json()["kind"] == "atrasos"
        assert c.get("/reports", params={"kind": "inexistente"}).status_code == 400
