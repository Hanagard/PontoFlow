# Roadmap — PontoFlow

## Entregue e presente no código
- Arquitetura FastAPI, MongoDB, React e TypeScript; isolamento multiempresa.
- Autenticação, sessão httpOnly, bcrypt e autorização por perfil.
- Cadastro e administração de empresas, usuários e funcionários.
- Jornadas, registros de ponto, espelho e saldos.
- Solicitações de ajuste, aprovações e trilha de auditoria.
- Painel, relatórios e exportação CSV.
- **Calendário e feriados:** calendário por empresa, feriados e atribuições de escala.
- **Banco de horas:** apuração e fechamento por competência.
- Escalas fixas e ciclos, incluindo suporte a 12x36.
- PWA e interface responsiva.

## Próximas prioridades — segurança e operação
1. Configurar domínio, HTTPS, CORS estrito, proxy confiável e gestão de segredos.
2. Backup/restore testado, monitoramento e política de retenção.
3. CAPTCHA/provedor de verificação se o cadastro público for reativado.
4. Completar testes unitários, integração isolada, frontend, E2E e CI.
5. Testes de carga e revisão independente de segurança.

## Próximas prioridades — produto
1. Exportação XLSX/PDF completa.
2. Notificações por e-mail com provedor.
3. Múltiplos estabelecimentos e contratos.
4. Planos, limites, assinatura e cobrança SaaS.
5. Integrações de RH, API comercial e webhooks.

GPS/geofence, QR Code, selfie/biometria e registro offline exigem controles técnicos, análise LGPD e trilha auditável antes de ativação.
