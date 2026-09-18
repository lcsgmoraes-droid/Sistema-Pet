---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — platform_admin_sessions

Ver [[platform_admins]], [[user_sessions]].

## Definição
Sessão ativa de um [[platform_admins|admin da plataforma]] — allowlist de `jti` revogável, não um hash de token.

## Confirmado no código
- Modelo: `platform_auth_models.py:49-72` (`PlatformAdminSession`).
- Colunas: `token_jti` (unique, gerado no login), `ip_address`/`user_agent`, `expires_at`, `revoked`/`revoked_at`/`revoke_reason`.
- **Padrão de sessão confirmado**: não guarda o JWT nem hash — só o `jti` em texto puro (não é segredo por si, precisa do JWT assinado válido para autenticar). O JWT carrega esse mesmo `jti` como claim; a validação decodifica o JWT e confere no banco se a sessão existe, não está revogada e não expirou. Mesmo padrão de [[user_sessions]] (allowlist por jti), mas em tabela e router completamente separados — reforça o isolamento plataforma vs. tenant.

## Relacionamentos
- FK de saída: `platform_admin_id → platform_admins.id` (CASCADE).

## Utilizado por
- `platform_auth.py` — criação no login, revogação individual no logout, revogação em massa no reset de senha, checagem em toda rota protegida via `get_platform_auth_context`/`require_platform_admin`.

## Não identificado
- Nada notável.
