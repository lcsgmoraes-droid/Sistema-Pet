---
tipo: dominio
atualizado: 2026-09-13
---

# Entidade — UserTenant

Ver [[Usuario]], [[Tenant]], [[Role-Permission]], [[Plano]].

## Definição
Vínculo N:N real entre pessoa e loja: `User ↔ Tenant ↔ Role`. É a entidade que confirma o modelo "uma pessoa, múltiplas lojas" — um usuário pode ter uma linha `UserTenant` por tenant ao qual tem acesso, cada uma potencialmente com um `role_id` (perfil) diferente. RBAC é sempre resolvido por tenant, nunca globalmente — ver [[Role-Permission]].

## Confirmado no código
- Modelo: `backend/app/models_authz.py:53-67`, classe `UserTenant(BaseTenantModel)`, tabela `user_tenants`. Campos: `user_id` (FK `users.id`), `role_id` (FK `roles.id`), `is_active` (default `true`), `created_at`; `tenant_id` vem do mixin `BaseTenantModel`.
- ⚠️ Sem `UniqueConstraint(user_id, tenant_id)` — confirmado na migration base (`backend/alembic/versions/bda1c213cae2_base_inicial_completa.py:989-1003`), que só tem índices simples não-únicos em `role_id`, `tenant_id`, `user_id`. Nada no nível de schema impede duas linhas `UserTenant` para o mesmo par usuário+tenant (ex.: com roles diferentes).
- Seleção de tenant no login: `POST /auth/select-tenant` (`backend/app/auth/auth_multitenant_session_routes.py:133-160`) consulta `UserTenant` filtrando `user_id`, `tenant_id` e `is_active=True`; sem match → `403`. Só depois disso o `tenant_id` é gravado no JWT emitido — é o mecanismo citado em [[Autorizacao]] ("tenant_id vem do JWT, validado contra UserTenant ativo antes de ser emitido").
- Mesmo fluxo também checa `tenant.status ∈ {"active","ativo"}` (linhas 155-160) — tenant inativo bloqueia a sessão mesmo com `UserTenant` válido.
- Em seguida, `enforce_simultaneous_session_limit()` (`plan_limits.py:122-161`, chamado na linha 186 do mesmo arquivo) aplica o `simultaneous_sessions_limit` do [[Plano]] do tenant selecionado — em planos de entrada, abrir sessão em outro dispositivo derruba a sessão anterior (comentário explícito no código, linhas 128-132).
- Módulos e planos não têm relação direta com `UserTenant` — são sempre resolvidos por `tenant_id`, então o mesmo usuário pode ver módulos completamente diferentes dependendo de qual tenant está selecionado no momento (JWT ativo).

## Utilizado por
- Login/troca de empresa (`select-tenant`) — ver [[Autenticacao]].
- [[Role-Permission]] — é o join que carrega o `role_id` efetivo por tenant.
- [[Plano]] — limite de sessões simultâneas é aplicado no mesmo fluxo de seleção de tenant.

## Não identificado
- ❓ Não encontrada validação de aplicação que impeça duas linhas `UserTenant` duplicadas para o mesmo par usuário+tenant — a ausência é só de schema; rotas de convite/criação não foram auditadas a fundo aqui (fora do escopo desta pesquisa, focada em licenciamento).
- ❓ Não encontrado estado explícito de "convite pendente" no próprio `UserTenant` (só `is_active` booleano) — fluxo de convite/onboarding pode estar em `auth_multitenant_account_routes.py`, não aprofundado nesta pesquisa.
