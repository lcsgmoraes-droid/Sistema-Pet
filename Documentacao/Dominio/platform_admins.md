---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — platform_admins

Ver [[platform_admin_sessions]], [[Tenant]].

## Definição
Super-admin da **plataforma CorePet** — nível de acesso acima de qualquer tenant, estruturalmente diferente do "superadmin" que é apenas uma Role dentro de um tenant.

## Confirmado no código
- Modelo: `platform_auth_models.py:10-46` (`PlatformAdmin`). `Base` puro — **sem `tenant_id`**, não passa pelo RBAC de Role/Permission/UserTenant (sempre tenant-scoped).
- Colunas: `email` (unique), `hashed_password`, `is_active`, `reset_token`/`reset_token_expires` (reset armazenado com hash `v2:hash(code):hash(link)`, nunca texto puro), `failed_login_attempts`/`locked_until` (lockout), `last_login_at`/`last_login_ip`.
- Serve para operações de back-office da CorePet sobre tenants: criar propostas comerciais (`BillingOffer`), notas de onboarding, ver erros de todos os tenants.

## Relacionamentos
- Referenciada por: [[platform_admin_sessions]]`.platform_admin_id` (CASCADE), `billing_offers.created_by_platform_admin_id` (nullable), `ops_tenant_onboarding_notes.created_by_platform_admin_id` (RESTRICT, NOT NULL).

## Utilizado por
- `platform_auth.py` (login/refresh/logout/reset de senha, rotas `/platform-auth/*`).
- Dependency `require_platform_admin` protege `routes/ops_tenants_routes.py` (`/admin/tenants`) e `routes/error_events_routes.py`. Routers registrados em `main_routers.py:101,178,181,184,256,430`.

## Não identificado
- Nada notável — bom exemplo de isolamento de nível de acesso, com reset de senha corretamente hasheado.
