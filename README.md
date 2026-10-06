# PontoFlow — Sistema de Controle de Ponto Eletrônico

Plataforma web responsiva de controle de jornada e registro de ponto, multiempresa desde a base e preparada para evoluir como SaaS.

**Stack**: FastAPI + MongoDB (motor, Pydantic v2) no backend · Vite + React 19 + TypeScript strict + Tailwind v4 + shadcn/ui no frontend · camada tipada sobre `/api`.

> A decisão de manter FastAPI + MongoDB (em vez de Node/PostgreSQL/Prisma) está justificada tecnicamente em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Funcionalidades

**Funcionário** — registra Entrada → Saída para Intervalo → Retorno do Intervalo → Saída em sequência validada pelo servidor; consulta o espelho de ponto com saldo; solicita correções com justificativa.

**Gestor** — quadro do dia da equipe, aprovação/rejeição de solicitações, espelho e relatórios.

**Admin da empresa** — cadastro de funcionários (CPF validado, mascarado nas listagens), jornadas, usuários e permissões, painel com indicadores, relatórios, auditoria.

**Super admin** — tudo do admin, mais a criação de outros super administradores.

## Garantias do sistema

| Regra | Onde é imposta |
|---|---|
| Horário oficial é do **servidor** (UTC no banco, fuso da empresa na tela) | `backend/lib/timeutil.py` — o cliente nunca envia timestamp |
| Sequência de registros válida (sem Entrada→Entrada) | `backend/lib/calc.py::next_allowed_type` + `routers/records.py` |
| Isolamento entre empresas | `backend/lib/tenancy.py` — `company_id` vem sempre da sessão |
| Autorização por perfil | `backend/lib/security.py::require_roles` (o guard do React é só navegação) |
| Ponto só muda com aprovação, guardando o valor anterior | `routers/adjustments.py` + auditoria |
| Trilha de auditoria append-only | `backend/lib/audit.py` — não existe rota de update/delete |
| Senha só como hash bcrypt, sessão em cookie httpOnly | `backend/lib/security.py` |

## Rodando

Os serviços sobem sob supervisor no ambiente de desenvolvimento (frontend `3000`, backend `8001`, mongod local). Manualmente:

```bash
cd backend  && pip install -r requirements.txt && uvicorn server:app --host 0.0.0.0 --port 8001 --reload
cd frontend && yarn install && yarn dev
```

Configuração: copie `backend/.env.example` para `backend/.env` (`MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, `SESSION_SECRET`, `APP_TZ`). O `.env` real nunca vai para o repositório.

## Dados de demonstração

```bash
cd backend && python seed.py   # idempotente: recria apenas a empresa de demonstração
```

Cria 1 empresa, 2 jornadas, 5 funcionários, ~3 semanas de registros (com uma falta e um dia incompleto) e 2 solicitações pendentes. Para testes locais, o script informa a senha de demonstração ao terminar. Os botões de acesso rápido só aparecem se `VITE_DEMO_MODE=true`; não execute o seed em produção.

## Testes

```bash
cd backend  && pytest            # domínio (cálculo/sequência/CPF) + integração (auth, RBAC, isolamento)
cd frontend && yarn typecheck    # a única forma de typecheck do frontend
cd frontend && yarn lint
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | camadas, decisões arquiteturais, fronteira tipada |
| [`docs/DATABASE.md`](docs/DATABASE.md) | coleções, campos, índices, migrations |
| [`docs/API.md`](docs/API.md) | todos os endpoints, perfis e códigos de erro |
| [`docs/SECURITY.md`](docs/SECURITY.md) | autenticação, autorização, LGPD, pendências de produção |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | ambientes, variáveis, build, backup |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | fases entregues e próximas (banco de horas, GPS, escalas, SaaS) |
| [`memory/SPEC.md`](memory/SPEC.md) | especificação viva do app |

## Estrutura

```
backend/
  server.py            bootstrap + montagem dos routers em /api
  lib/                 db, security, tenancy, timeutil, calc, validators, audit
  models/              modelos Pydantic v2
  routers/             auth, users, employees, schedules, records, timesheet, adjustments, dashboard
  tests/               test_calc.py (domínio), test_api.py (integração)
  seed.py              dados de demonstração idempotentes
frontend/src/
  pages/               Login, Ponto, Espelho, Solicitacoes, Painel, Funcionarios, Jornadas, Aprovacoes, Relatorios, Auditoria
  components/          layout/AppShell, ponto/*, admin/*, estados e badges
  lib/                 api.ts (fetch tipado), types.ts (espelho dos modelos), session.ts
  hooks/useMe.ts       identidade e papel do usuário
docs/                  documentação técnica
```

## Não implementado por decisão

Localização obrigatória, geofence, selfie, QR Code e biometria **não** estão ativos. Os campos de GPS já existem em `time_records`, mas ativar a coleta exige antes a arquitetura de consentimento, retenção e controle de acesso prevista na LGPD (ver `docs/SECURITY.md` e `docs/ROADMAP.md`). O registro offline também está ausente de propósito: sem estratégia de sincronização auditável, não deve existir.
