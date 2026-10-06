# API — PontoFlow

Base: `/api` (o dev server do Vite faz proxy para o backend). Todas as rotas respondem JSON.
Autenticação por cookie httpOnly `pf_session`, enviado automaticamente em requisições same-origin.
Erros seguem `{ "detail": "mensagem em português" }`; validação de corpo retorna `422` com `{ "detail": [...] }`.

Códigos usados: `200` ok · `201` criado · `400` regra de negócio/entrada inválida · `401` sem sessão · `403` sem permissão · `404` não encontrado · `409` conflito (duplicidade) · `422` corpo inválido · `429` rate limit · `500` erro interno (mensagem neutra).

## Autenticação

| Método | Rota | Perfil | Descrição |
|---|---|---|---|
| POST | `/auth/login` | público | `{email, password}` → dados do usuário + cookie de sessão. Rate limit 8/5min por e-mail+IP |
| POST | `/auth/signup` | público | cria empresa + primeiro admin (`{company_name, name, email, password, timezone?}`) |
| GET | `/auth/me` | autenticado | quem sou eu (id, name, role, company_id, company_name, timezone, employee_id) |
| POST | `/auth/logout` | autenticado | limpa o cookie e audita |

## Usuários

| Método | Rota | Perfil |
|---|---|---|
| GET | `/users` | admin, super_admin |
| POST | `/users` | admin, super_admin (`super_admin` só por super_admin) |
| PATCH | `/users/{id}` | admin, super_admin (role/status; não pode desativar a si mesmo) |

## Funcionários

| Método | Rota | Perfil | Notas |
|---|---|---|---|
| GET | `/employees?status=&department=&q=` | admin, gestor, super_admin | CPF sempre mascarado |
| GET | `/employees/{id}` | autenticado | funcionário só o próprio (senão `403`) |
| POST | `/employees` | admin, super_admin | valida CPF; `create_login=true` cria o acesso |
| PATCH | `/employees/{id}` | admin, super_admin | audita antes/depois |

## Jornadas

| Método | Rota | Perfil |
|---|---|---|
| GET | `/schedules` | autenticado |
| POST | `/schedules` | admin, super_admin (valida `HH:MM` e dias 0–6) |

## Registro de ponto

| Método | Rota | Perfil | Notas |
|---|---|---|---|
| GET | `/time-records/today` | autenticado | status do dia: próximo evento permitido, registros, trabalhado/previsto, hora do servidor |
| POST | `/time-records` | funcionário (próprio) | **não aceita timestamp**; o tipo é decidido pelo servidor. Dia completo → `400` |
| GET | `/time-records?employee_id=&start=&end=` | autenticado | funcionário vê só os próprios |
| GET | `/time-records/live` | admin, gestor, super_admin | quadro do dia da equipe |

Exemplo:

```bash
curl -s -X POST /api/time-records -H 'Content-Type: application/json' -d '{}' --cookie "pf_session=…"
# 201 {"type":"entrada","type_label":"Entrada","hhmm":"08:02","timestamp":"...Z", ...}
```

## Espelho e relatórios

| Método | Rota | Perfil | Notas |
|---|---|---|---|
| GET | `/timesheet?employee_id=&start=&end=&status=` | autenticado | funcionário sempre recebe o próprio espelho; período máximo 180 dias |
| GET | `/timesheet/export?...` | autenticado | CSV (`;`, com BOM) gerado no backend |
| GET | `/reports?kind=&start=&end=&department=` | admin, gestor, super_admin | `kind`: `espelho`\|`atrasos`\|`extras`\|`faltas`\|`pendencias` |

## Solicitações de ajuste

| Método | Rota | Perfil | Notas |
|---|---|---|---|
| GET | `/adjustment-requests?status=` | autenticado | funcionário vê só as próprias |
| POST | `/adjustment-requests` | funcionário | `{target_date, type, requested_time, reason}`; data futura → `400`; pendente duplicada → `409` |
| PATCH | `/adjustment-requests/{id}` | admin, gestor, super_admin | `{decision: aprovada\|rejeitada, note?}` — aprovação cria/corrige o registro |
| POST | `/adjustment-requests/{id}/cancel` | autor ou gestão | só pendentes |

## Painel e auditoria

| Método | Rota | Perfil |
|---|---|---|
| GET | `/dashboard` | admin, gestor, super_admin |
| GET | `/audit-logs?action=&limit=` | admin, gestor, super_admin (somente leitura — não existe update/delete) |
