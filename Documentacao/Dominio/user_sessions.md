---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — user_sessions

Ver [[Usuario]], [[platform_admin_sessions]], [[UserTenant]].

## Definição
Sessão ativa de um usuário do tenant — mesmo padrão de allowlist por `jti` de [[platform_admin_sessions]].

## Confirmado no código
- Modelo: `models.py:179-206` (`UserSession`). Comentário explícito no código: "Não usar BaseTenantModel - sessões não são tenant-specific".
- `tenant_id` é UUID **nullable** (diferente de `platform_admin_sessions`, que não tem o campo — aqui existe mas é opcional, coerente com usuário multiempresa que pode ter sessão sem tenant fixado ainda).
- Colunas: `token_jti` (unique), `device_info` (JSON como texto), `expires_at`, `revoked`/`revoked_at`/`revoke_reason`.

## Relacionamentos
- FK de saída: `user_id → users.id`.
- Sem referências de entrada.

## Utilizado por
- `session_manager.py` (único ponto de escrita/leitura: `create_session`, `get_active_sessions`, `get_session_by_jti`, revogação por sessão/por usuário, limpeza de expiradas).
- `tenancy/filters.py`, `services/plan_limits.py` (limite de sessões simultâneas do [[Plano]] — ver [[UserTenant]]), `routes/ecommerce_auth_profiles.py`.

## Não identificado
- Nada notável.
