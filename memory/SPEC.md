# PontoFlow — Especificação viva

Sistema de controle de ponto eletrônico multiempresa. Stack do pod: **FastAPI + MongoDB (motor)** no backend, **Vite + React 19 + TS strict + Tailwind v4 + shadcn/ui** no frontend, unidos pela camada tipada `/api`.

## O que o app faz

- **Funcionário**: registra Entrada → Saída para Intervalo → Retorno do Intervalo → Saída em sequência validada pelo servidor; consulta espelho de ponto e solicita correções.
- **Gestor**: acompanha o quadro do dia da equipe, aprova/rejeita solicitações, consulta espelho e relatórios.
- **Admin da empresa**: tudo do gestor + cadastro de funcionários, jornadas e auditoria.
- **Super admin**: tudo do admin + criação de outros super admins.

## Regras invioláveis (validadas no backend)

1. **Horário oficial é do servidor** (`lib/timeutil.now_utc()`), gravado em UTC *aware*; o cliente nunca envia timestamp. Apresentação converte para o fuso da empresa (`America/Belem`).
2. **Sequência de registros**: o backend calcula o próximo evento permitido (`lib/calc.next_allowed_type`). Dia completo → `400`, nunca duplicata silenciosa.
3. **Isolamento multiempresa**: `company_id` vem sempre da sessão (`lib/tenancy.scope`), nunca do corpo/query. Funcionário só acessa o próprio registro, mesmo passando outro `employee_id`.
4. **Sessão**: cookie httpOnly `pf_session` (JWT HS256, `SESSION_SECRET` no `.env`). Nenhum token em JSON. Senhas só como hash bcrypt.
5. **Auditoria append-only**: não existe rota de update/delete em `audit_logs`.
6. **Ponto só muda com aprovação**: solicitação `pendente` → aprovação cria/corrige o registro e guarda o valor anterior na auditoria.

## Modelo de dados (coleções Mongo, `id` string uuid4)

| Coleção | Campos principais |
|---|---|
| `companies` | id, name, cnpj, timezone, status, created_at |
| `users` | id, company_id, name, email (único), password_hash, role, employee_id, status |
| `employees` | id, company_id, user_id, name, cpf, matricula, email, phone, cargo, department, schedule_id, status, hired_at |
| `work_schedules` | id, company_id, name, entrada, inicio_intervalo, fim_intervalo, saida, tolerance_minutes, work_days |
| `time_records` | id, company_id, employee_id, type, timestamp (UTC), timezone, origin, device, ip, lat/long/accuracy, observacao, status, adjusted |
| `time_adjustment_requests` | id, company_id, employee_id, target_date, type, requested_time, previous_time, record_id, reason, status, decided_by, decided_at |
| `audit_logs` | id, company_id, actor_id/name/role, action, resource, resource_id, before, after, ip, user_agent, created_at |

Índices compostos em `lib/db.py::INDEXES` (company+employee+timestamp, company+status, email único, cpf/matrícula únicos por empresa).

## API (toda sob `/api`, toda autenticada exceto login/signup)

`POST /auth/login` · `POST /auth/signup` · `GET /auth/me` · `POST /auth/logout`
`GET|POST /users` · `PATCH /users/{id}`
`GET|POST /employees` · `GET|PATCH /employees/{id}`
`GET|POST /schedules`
`GET /time-records` · `POST /time-records` · `GET /time-records/today` · `GET /time-records/live`
`GET /timesheet` · `GET /timesheet/export` (CSV) · `GET /reports`
`GET|POST /adjustment-requests` · `PATCH /adjustment-requests/{id}` · `POST /adjustment-requests/{id}/cancel`
`GET /dashboard` · `GET /audit-logs`

## Rotas do frontend

`/login` · `/` (redireciona por perfil) · `/ponto` (funcionário) · `/espelho` (todos) · `/solicitacoes` (funcionário) · `/painel` `/funcionarios` `/aprovacoes` `/relatorios` `/auditoria` (gestão) · `/jornadas` (admin).

## Cálculo de jornada (`backend/lib/calc.py`, puro e testado)

Trabalhado = (entrada→intervalo) + (retorno→saída); previsto = (saída−entrada) − intervalo; atraso só acima da tolerância; saldo e extras apenas em dia completo; dia útil sem registro = `falta` (ou `justificada`), fora dos dias de trabalho = `folga`, parcial = `incompleta`.

## Dados de demonstração

`cd /app/backend && python seed.py` — 1 empresa, 4 logins (ver `memory/test_credentials.md`), 5 funcionários, 2 jornadas, ~3 semanas de registros (com 1 falta e 1 dia incompleto), 2 solicitações pendentes. Hoje fica sem registros para o fluxo de bater ponto começar limpo.

## Testes

- `cd /app/backend && pytest` — `tests/test_calc.py` (domínio: sequência, atraso, extras, saldo, faltas, CPF) e `tests/test_api.py` (auth, RBAC, sequência, isolamento entre empresas, auditoria, espelho, CSV).
- `cd /app/frontend && yarn typecheck`.

## Preparado para o futuro (não implementado)

Campos de GPS já persistidos em `time_records` (lat/long/accuracy) sem política de obrigatoriedade; PWA com manifest instalável; estrutura multiempresa pronta para planos/cobrança. Biometria/selfie **não** implementadas por decisão de privacidade (§20).
