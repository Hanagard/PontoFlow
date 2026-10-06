# Segurança — PontoFlow

## Autenticação

- Senhas apenas como hash **bcrypt** (`passlib`); nenhum endpoint retorna hash ou senha.
- Sessão = **JWT HS256 em cookie httpOnly** (`pf_session`, `SameSite=Lax`, TTL 7 dias), assinado com `SESSION_SECRET` lido de `backend/.env`. Nenhum token trafega no corpo da resposta nem é armazenado pelo frontend.
- `GET /api/auth/me` é a única fonte de verdade sobre identidade/papel.
- Logout limpa o cookie no servidor **e** o cache do react-query no cliente (`lib/session.ts::endSession`), evitando vazamento de dados entre contas no mesmo navegador.

## Autorização

- Enforcement no backend via dependências: `get_current_user` (401) e `require_roles(...)` (403).
- O guard de rota do React é apenas navegação. Remover o guard no cliente não concede acesso a dado algum.
- `role` e `company_id` nunca são lidos do corpo/query: vêm do documento do usuário carregado pela sessão.

## Isolamento multiempresa

- Toda consulta inclui `company_id` da sessão (`lib/tenancy.scope`).
- `resolve_employee` força o `employee_id` da própria sessão quando o papel é `funcionario`, ignorando o id enviado pelo cliente.
- Acesso a recurso de outra empresa retorna `404` (não revela existência).
- Teste de regressão: `backend/tests/test_api.py::test_cross_company_data_is_invisible`.

## Proteção contra força bruta

- `POST /auth/login`: 8 tentativas por e-mail+IP em janela de 5 minutos → `429`.
- Mensagem idêntica para e-mail inexistente e senha errada (sem enumeração de contas).
- Tentativa falha em conta existente gera evento `LOGIN_FALHA` na auditoria.

## Validação de entrada

- Pydantic v2 valida tipo/tamanho antes do handler (`422` automático).
- Validações de domínio no servidor: CPF com dígitos verificadores, `HH:MM`, datas ISO, período máximo de 180 dias, dias da semana 0–6, relações entre entidades (jornada/funcionário pertencem à empresa).
- MongoDB com motor usa documentos BSON parametrizados — não há concatenação de query (classe de risco equivalente a SQL injection não se aplica), e nenhum operador vindo do cliente é interpolado em filtro.

## Dados sensíveis e privacidade (LGPD, §20)

- CPF é armazenado apenas em dígitos e **nunca** retornado inteiro: `EmployeeOut.cpf` e `cpf_masked` trazem `***.982.***-25`.
- Auditoria registra o CPF já mascarado.
- Localização, selfie e biometria **não** estão implementadas. Os campos de GPS existem em `time_records` mas nenhum fluxo os exige; ativar depende de política de consentimento, retenção e controle de acesso ainda não construída.
- Logs não registram senha, hash nem CPF completo.

## Headers e CORS

- Middleware adiciona `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(self)`.
- CORS vem de `CORS_ORIGINS` no `.env` com `allow_credentials=True`. **Em produção, substitua `*` pelo domínio exato** — curinga com credenciais deve ser restringido antes do go-live.

## Tratamento de erros (§25)

Handler global em `server.py` converte exceção não tratada em `500 {"detail": "Erro interno. Tente novamente em instantes."}`; o traceback fica só no log do servidor. No frontend, `errorMessage()` exibe o `detail` do backend — nunca um stack trace.

## Segredos

- `SESSION_SECRET`, `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, `APP_TZ` ficam em `backend/.env`, lidos via `os.environ`. Modelo em `.env.example`.
- Nenhum segredo no frontend: o cliente só conhece caminhos relativos `/api`.

## Pendências conhecidas para produção

1. Restringir `CORS_ORIGINS` ao domínio real e marcar o cookie como `secure` quando servido exclusivamente por HTTPS (`lib/security.session_cookie_kwargs`).
2. Rate limit atual é em memória do processo — mover para Redis ao escalar horizontalmente.
3. Rotação de `SESSION_SECRET` invalida todas as sessões (comportamento esperado, documentar na operação).
