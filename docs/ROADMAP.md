# Roadmap — PontoFlow

## Entregue (Fases 0–13 do plano)

- **Fase 0 — Análise**: diagnóstico do repositório, stack e riscos; decisão documentada de manter FastAPI + MongoDB (`docs/ARCHITECTURE.md`).
- **Fase 1 — Arquitetura e banco**: camadas UI → hooks → API → routers → domínio → persistência; coleções e índices (`docs/DATABASE.md`).
- **Fase 2 — Autenticação**: bcrypt, sessão em cookie httpOnly, rate limit, `/auth/me`, logout com limpeza de cache.
- **Fase 3 — Empresas e usuários**: tenant raiz, signup de empresa + admin, CRUD de usuários, troca de papel auditada.
- **Fase 4 — Funcionários**: cadastro com validação de CPF, matrícula única, criação opcional de acesso, ativação/desativação.
- **Fase 5 — Jornadas**: horários previstos, tolerância, dias úteis; regras só no domínio.
- **Fase 6 — Registro de ponto**: sequência Entrada → Intervalo → Retorno → Saída validada no servidor, horário oficial do servidor.
- **Fase 7 — Espelho de ponto**: tabela diária com trabalhado/previsto/saldo/status, filtros e totais.
- **Fase 8 — Correções e aprovações**: solicitação, aprovação/rejeição, criação/correção do registro só após aprovação, valor anterior na auditoria.
- **Fase 9 — Dashboard**: ativos, presentes, em intervalo, ausentes, atrasados, incompletas, pendências, extras + quadro do dia.
- **Fase 10 — Relatórios**: espelho por período, atrasos, horas extras, faltas, pendências; exportação CSV gerada no backend.
- **Fase 11 — Auditoria**: trilha append-only com ator, ação, recurso, antes/depois e IP; sem rota de exclusão.
- **Fase 12 — Segurança e testes**: `docs/SECURITY.md`, testes de domínio e de integração (auth, RBAC, sequência, isolamento).
- **Fase 13 — PWA**: manifest instalável, meta tags, layout mobile-first com botão de ponto de alvo amplo.

## Próximas fases

### Fase 14 — Deploy
- Restringir `CORS_ORIGINS` ao domínio real e ativar `secure=True` no cookie.
- Rate limit distribuído (Redis) para múltiplas instâncias.
- Rotina de backup incluindo `audit_logs`.

### Fase 15 — Funcionalidades avançadas (ordem sugerida)

1. **Banco de horas** — acumulado por competência a partir do saldo diário já calculado; fechamento mensal travado.
2. **Feriados e escalas** — coleções `holidays` e `schedule_assignments`; `is_workday` passa a consultar o calendário da empresa.
3. **Jornadas flexíveis / 12x36 / 6x1** — `work_schedules` ganha tipo e múltiplos intervalos; `lib/calc` é o único ponto a alterar.
4. **Exportação XLSX e PDF** — `openpyxl` já instalado; espelho imprimível em HTML para PDF.
5. **Notificações** — alerta de jornada incompleta e de solicitação pendente (e-mail precisa de provedor configurado).
6. **GPS e geofence** — política por empresa (`obrigatório`/`opcional`/`desativado`), locais com latitude/longitude/raio, validação **no backend**.
7. **QR Code** — token de curta duração por local, sempre combinado com sessão autenticada (QR isolado não é mecanismo de segurança).
8. **Consentimento e retenção (LGPD)** — pré-requisito para selfie/biometria; registro de consentimento, prazo de retenção e expurgo.
9. **Múltiplos estabelecimentos e contratos** — `workplaces` e vínculo funcionário ↔ local/contrato.
10. **App mobile / offline seguro** — fila local assinada com sincronização idempotente; não registrar ponto offline sem essa garantia.
11. **SaaS**: planos, limites por plano, assinatura e cobrança; onboarding e página pública.
12. **Integrações de RH / API comercial** — chaves por empresa, escopos e webhooks.

## Fora de escopo por decisão

- **Reconhecimento facial / biometria**: não implementar sem base legal, consentimento e arquitetura de proteção de dados biométricos (§20).
- **Registro offline silencioso**: proibido sem estratégia de sincronização auditável (§27).
