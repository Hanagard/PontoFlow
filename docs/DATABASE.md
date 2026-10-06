# Banco de dados — PontoFlow (MongoDB)

Todo documento usa `id` string (uuid4), nunca `ObjectId` (não é serializável em JSON).
Todo documento de negócio carrega `company_id` — a chave de isolamento multiempresa.
Datas são `datetime` *aware* em UTC; a conversão para o fuso da empresa acontece na apresentação.

## Coleções

### companies
| Campo | Tipo | Notas |
|---|---|---|
| id | string | único |
| name | string | razão social / nome fantasia |
| cnpj | string? | |
| timezone | string | padrão `America/Belem` |
| status | string | `ativa` |
| created_at | datetime | UTC |

### users (acesso ao sistema)
| Campo | Tipo | Notas |
|---|---|---|
| id | string | único |
| company_id | string | tenant |
| name | string | |
| email | string | **único global** |
| password_hash | string | bcrypt; nunca retornado |
| role | string | `super_admin` \| `admin` \| `gestor` \| `funcionario` |
| employee_id | string? | vínculo com `employees` |
| status | string | `ativo` \| `inativo` |

### employees
`id`, `company_id`, `user_id?`, `name`, `cpf` (11 dígitos, validado), `matricula`, `email?`, `phone?`, `cargo?`, `department?`, `schedule_id?`, `status`, `hired_at?`, `created_at`, `updated_at`.

### work_schedules
`id`, `company_id`, `name`, `entrada`, `inicio_intervalo`, `fim_intervalo`, `saida` (todos `HH:MM`), `tolerance_minutes`, `work_days` (0=segunda … 6=domingo), `created_at`.

### time_records
`id`, `company_id`, `employee_id`, `type` (`entrada`\|`inicio_intervalo`\|`fim_intervalo`\|`saida`), `timestamp` (UTC, **do servidor**), `timezone`, `origin` (`web`\|`ajuste`), `device?`, `ip?`, `latitude?`, `longitude?`, `accuracy?`, `observacao?`, `status`, `adjusted`, `adjusted_at?`, `adjusted_by?`, `created_at`.

### time_adjustment_requests
`id`, `company_id`, `employee_id`, `employee_name`, `target_date` (`YYYY-MM-DD`), `type`, `kind`, `requested_time` (`HH:MM`), `previous_time?`, `record_id?`, `reason`, `status` (`pendente`\|`aprovada`\|`rejeitada`\|`cancelada`), `created_by`, `decided_by?`, `decided_by_name?`, `decision_note?`, `decided_at?`, `created_at`.

### audit_logs (append-only)
`id`, `company_id`, `actor_id?`, `actor_name`, `actor_role`, `action`, `resource`, `resource_id?`, `before?`, `after?`, `ip?`, `user_agent?`, `created_at`.

Ações registradas: `LOGIN`, `LOGIN_FALHA`, `LOGOUT`, `EMPRESA_CRIADA`, `USUARIO_CRIADO`, `PERMISSAO_ALTERADA`, `FUNCIONARIO_CRIADO`, `FUNCIONARIO_ATUALIZADO`, `JORNADA_CRIADA`, `JORNADA_ATUALIZADA`, `PONTO_REGISTRADO`, `PONTO_CORRIGIDO`, `SOLICITACAO_CRIADA`, `SOLICITACAO_APROVADA`, `SOLICITACAO_REJEITADA`, `SOLICITACAO_CANCELADA`.

## Índices (`backend/lib/db.py::INDEXES`)

| Coleção | Índice | Motivo |
|---|---|---|
| users | `email` único | login e unicidade de conta |
| users | `company_id + role` | listagem administrativa |
| employees | `company_id + cpf` único | duplicidade de CPF por empresa |
| employees | `company_id + matricula` único | duplicidade de matrícula |
| employees | `company_id + status + name` | listagem ordenada |
| time_records | `company_id + employee_id + timestamp desc` | espelho e registros do dia |
| time_records | `company_id + timestamp desc` | painel e quadro do dia |
| time_adjustment_requests | `company_id + status + created_at desc` | fila de aprovação |
| audit_logs | `company_id + created_at desc` | trilha cronológica |

Alterar chaves/opções de um índice existente é rejeitado no startup (log + índice antigo mantido): remova com `drop_index` antes.

## Migrations

MongoDB é *schemaless*; o equivalente a migration aqui é `ensure_indexes()` (idempotente, roda no startup) somado a scripts pontuais. O seed de demonstração (`backend/seed.py`) é idempotente e apaga **apenas** os documentos da empresa demo.
