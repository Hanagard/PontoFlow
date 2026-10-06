# Arquitetura — PontoFlow

## Decisão 1: manter FastAPI + MongoDB em vez de Node + PostgreSQL + Prisma

O prompt-mestre (§4) preferia Node/Postgres/Prisma. O ambiente de execução provisiona **FastAPI + MongoDB + supervisor** já rodando, sem PostgreSQL disponível. Migrar exigiria provisionar um banco e um runtime novos fora do template — risco de infraestrutura alto e sem ganho funcional para o MVP. A decisão foi aprovada pelo usuário.

Consequência: a integridade que um ORM relacional daria por *foreign keys* é garantida por:
- validação explícita de relações nos routers (jornada pertence à empresa, funcionário pertence à empresa);
- índices únicos compostos (`company_id + cpf`, `company_id + matricula`, `email`);
- `company_id` em **todo** documento, sempre derivado da sessão.

## Camadas

```
UI (src/pages, src/components)
  ↓  hooks/serviços (src/hooks, TanStack Query)
  ↓  API tipada (src/lib/api.ts → /api relativo, proxy do Vite)
  ↓  routers FastAPI (backend/routers/*) — autenticação + autorização + validação
  ↓  domínio (backend/lib/calc.py, timeutil.py, validators.py) — puro e testável
  ↓  persistência (backend/lib/db.py, motor)
```

Nenhuma regra de negócio vive em componente React. O frontend não calcula saldo, atraso, hora extra nem o próximo evento permitido — tudo chega pronto do backend.

## Backend

| Módulo | Responsabilidade |
|---|---|
| `server.py` | bootstrap, CORS, headers de segurança, handler central de erros, montagem dos routers em `api_router` (`/api`) |
| `lib/db.py` | cliente motor, handle `db`, `INDEXES` + `ensure_indexes()` |
| `lib/security.py` | bcrypt, JWT de sessão, cookie httpOnly, `get_current_user`, `require_roles` |
| `lib/tenancy.py` | escopo por empresa, resolução de funcionário acessível, jornada do funcionário |
| `lib/timeutil.py` | relógio do servidor, conversões de fuso, limites de dia local em UTC |
| `lib/calc.py` | sequência de registros, jornada prevista, resumo do dia, totais, CSV |
| `lib/validators.py` | CPF (dígitos verificadores), máscara de CPF, HH:MM |
| `lib/audit.py` | escrita append-only da trilha de auditoria |
| `routers/*` | um `APIRouter` por recurso, todos montados sob `/api` |
| `models/*` | modelos Pydantic v2 de request/response |

## Fronteira tipada

Não há codegen. Cada modelo Pydantic tem uma interface TS escrita à mão em `frontend/src/lib/types.ts`, mantida em sincronia na mesma edição. `yarn typecheck` é o portão que revela divergência de uso.

## Decisões de segurança

- Autorização só no backend; o guard de rota do React é navegação, não segurança.
- `company_id`/`employee_id` enviados pelo cliente são ignorados quando o papel é `funcionario`.
- Rate limit em `POST /auth/login` por e-mail+IP (8 tentativas / 5 min).
- Mensagem de login genérica para e-mail inexistente e senha errada (sem enumeração de contas).
- CPF completo nunca sai do backend — apenas mascarado.
- Handler global converte exceção não tratada em `500` com mensagem neutra; stack trace só no log.

## Preparação para evolução

- **GPS/geofence**: `time_records` já aceita `latitude`/`longitude`/`accuracy`; falta a política configurável por empresa e a validação de raio no backend.
- **Multiempresa/SaaS**: `companies` é a raiz do tenant e `POST /auth/signup` já cria empresa + admin; planos/cobrança entram como coleção nova sem alterar o modelo atual.
- **PWA**: `manifest.webmanifest` + meta tags já instaláveis; registro offline deliberadamente ausente (§27) por exigir estratégia de sincronização segura.
