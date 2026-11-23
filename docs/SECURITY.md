# Segurança — PontoFlow

## Autenticação e autorização
- Senhas armazenadas como hash bcrypt.
- JWT HS256 em cookie httpOnly, SameSite=Lax e Secure em produção.
- `SESSION_SECRET` obrigatório em produção (mínimo 64 caracteres).
- Identidade, papel e empresa derivados da sessão no backend.

## Força bruta e abuso
- Login: 8 tentativas por e-mail+IP em 5 minutos.
- Cadastro público desabilitado por padrão; quando habilitado, 3 tentativas por IP/hora e senha mínima de 12 caracteres.
- Contadores em MongoDB com TTL, compartilhados entre instâncias e reinícios.
- Para produção, manter signup desabilitado ou adicionar CAPTCHA/verificação.

## Proxy e IP
- `X-Forwarded-For` ignorado por padrão.
- Configure `TRUSTED_PROXY_IPS` com IPs/CIDRs de proxies sob seu controle. O proxy deve sanitizar o cabeçalho.

## Produção
- HTTPS obrigatório, `APP_ENV=production`, segredo forte e CORS com origens exatas.
- Não usar seed nem credenciais de demonstração em produção.
- Backup/restore, monitoramento, retenção e revisão independente são pré-requisitos de go-live.

## Privacidade
CPF é mascarado nas listagens. GPS, selfie e biometria não estão habilitados como fluxo de coleta. Não registrar senhas, hashes ou CPF completo em logs.
