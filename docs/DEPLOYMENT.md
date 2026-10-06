# Deploy — PontoFlow

## Componentes

| Serviço | Porta | Processo |
|---|---|---|
| frontend (Vite/React) | 3000 | `yarn dev` (dev) / build estático servido pelo mesmo origin (prod) |
| backend (FastAPI) | 8001 | `uvicorn server:app --host 0.0.0.0 --port 8001` |
| MongoDB | 27017 | `mongod` |

No pod de desenvolvimento os três rodam sob **supervisor**:

```bash
sudo supervisorctl status frontend backend mongodb
sudo supervisorctl restart frontend backend     # só após mudar .env, requirements.txt ou vite.config.ts
```

## Variáveis de ambiente

Copie `backend/.env.example` para `backend/.env` e preencha:

| Variável | Significado |
|---|---|
| `MONGO_URL` | string de conexão do MongoDB |
| `DB_NAME` | nome do banco |
| `CORS_ORIGINS` | origens permitidas, separadas por vírgula (**não** use `*` em produção) |
| `SESSION_SECRET` | segredo HS256 da sessão (≥32 caracteres aleatórios) |
| `APP_TZ` | fuso padrão da plataforma (`America/Belem`) |

Gere o segredo com `python -c "import secrets; print(secrets.token_hex(32))"`.
`backend/.env` **nunca** vai para o repositório.

## Instalação local

```bash
# backend
cd backend && pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# frontend
cd frontend && yarn install && yarn dev
```

## Build de produção

```bash
cd frontend && yarn build        # gera dist/
cd backend && uvicorn server:app --host 0.0.0.0 --port 8001
```

Sirva `frontend/dist` e o backend **sob o mesmo domínio**, com `/api/*` roteado para a porta 8001. Como o frontend usa apenas caminhos relativos, nada precisa ser reconfigurado no cliente. Em origem única, ajuste também:

1. `CORS_ORIGINS` para o domínio real;
2. `secure=True` no cookie de sessão (`backend/lib/security.py::session_cookie_kwargs`) quando o tráfego for 100% HTTPS.

## Primeiro acesso

Sem dados, crie a empresa e o primeiro administrador por `POST /api/auth/signup`. Para avaliar com dados de exemplo:

```bash
cd /app/backend && python seed.py   # idempotente; recria só a empresa de demonstração
```

## Verificações antes de publicar

```bash
cd /app/backend  && python -c 'import server' && pytest
cd /app/frontend && yarn typecheck && yarn lint && yarn build
```

## Observabilidade

Logs: `/var/log/supervisor/backend.err.log`, `backend.out.log`, `frontend.err.log`. O handler global de erros registra o traceback completo no log e devolve mensagem neutra ao usuário.

## Backup

Os dados vivem no MongoDB: use `mongodump`/`mongorestore` do banco indicado em `DB_NAME`. A coleção `audit_logs` é append-only e deve ser incluída em toda rotina de backup por ser a trilha legal de alterações.

## Segurança obrigatória em produção

- Defina `APP_ENV=production`.
- Defina `SESSION_SECRET` com pelo menos 64 caracteres aleatórios; o backend rejeita segredo ausente/fraco em produção.
- Defina `CORS_ORIGINS` com as origens HTTPS exatas do aplicativo; não use `*`.
- O cookie `pf_session` passa a usar `Secure` automaticamente em produção.
- Não envie `backend/.env`, `frontend/.env`, credenciais de demonstração ou `node_modules` no pacote de produção.
- `VITE_DEMO_MODE` deve permanecer `false` em produção.
- Execute `python seed.py` somente em ambiente de demonstração/teste controlado.
