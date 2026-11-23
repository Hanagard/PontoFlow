# Segurança — PontoFlow

- Senhas armazenadas como hash bcrypt; sessão JWT em cookie httpOnly, SameSite=Lax e Secure em produção.
- `SESSION_SECRET` obrigatório em produção (mínimo 64 caracteres).
- Identidade, papel e empresa derivados da sessão no backend.
- Login limitado a 8 tentativas por e-mail+IP em 5 minutos.
- Cadastro público desabilitado por padrão; quando habilitado, 3 tentativas por IP/hora e senha mínima de 12 caracteres.
- Contadores persistidos em MongoDB com TTL, compartilhados entre instâncias e reinícios.
- `X-Forwarded-For` ignorado por padrão. Configure `TRUSTED_PROXY_IPS` apenas com IPs/CIDRs de proxies próprios que sanitizem o cabeçalho.
- Produção exige HTTPS, CORS com origens exatas, segredo forte, backup/restore e monitoramento.
- Não usar seed nem credenciais de demonstração em produção.
- CPF é mascarado nas listagens. GPS, selfie e biometria não estão habilitados como fluxo de coleta.
