# PontoFlow — Sistema de Controle de Ponto Eletrônico

Plataforma responsiva de controle de jornada, registro de ponto e gestão multiempresa.

**Stack:** FastAPI + MongoDB/Motor + Pydantic v2 · Vite + React 19 + TypeScript strict + Tailwind v4.

## Funcionalidades disponíveis
- Funcionário: Entrada → Início do intervalo → Retorno → Saída, espelho de ponto e solicitações de ajuste.
- Gestor: visão diária da equipe, aprovações, espelho e relatórios.
- Admin: funcionários, jornadas, usuários, permissões, painel, relatórios e auditoria.
- Calendário e feriados por empresa.
- Banco de horas: apuração e fechamento por competência.
- Escalas fixas e ciclos, incluindo 12x36.
- Multiempresa: isolamento por empresa e autorização no backend.

## Instalação
Configure MongoDB e copie `backend/.env.example` para `backend/.env`. Preencha `MONGO_URL`, `DB_NAME`, `SESSION_SECRET` e `CORS_ORIGINS`.

```bash
cd backend && pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
```
Em outro terminal: `cd frontend && yarn install && yarn dev`.

## Dados de demonstração
Defina uma senha forte e exclusiva via `DEMO_SEED_PASSWORD` (mínimo 12 caracteres) antes de executar `python seed.py`. O seed não imprime a senha e não deve ser executado em produção. O acesso rápido foi removido: credenciais não são compiladas no bundle do frontend.

## Cadastro público
Desabilitado por padrão. Para habilitar em ambiente controlado, defina `ALLOW_PUBLIC_SIGNUP=true`. A rota exige senha de 12 caracteres e limita 3 cadastros por IP/hora. Em produção, mantenha desabilitado ou adicione CAPTCHA.

## Testes
Backend: `pip install -r requirements-dev.txt && pytest`. Testes de integração exigem API e MongoDB de teste; configure `BACKEND_URL` e `PONTOFLOW_TEST_PASSWORD`.
Frontend: `yarn test`, `yarn typecheck`, `yarn lint` e `yarn build`.
E2E: execute Playwright em `tests/` com frontend/backend de teste ativos.

## Documentação
[Arquitetura](docs/ARCHITECTURE.md) · [Banco](docs/DATABASE.md) · [API](docs/API.md) · [Segurança](docs/SECURITY.md) · [Deploy](docs/DEPLOYMENT.md) · [Roadmap](docs/ROADMAP.md)

GPS/geofence, selfie, biometria, notificações externas, cobrança SaaS e operação offline não são anunciados como funcionalidades prontas.
