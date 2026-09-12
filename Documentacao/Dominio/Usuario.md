---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Usuário (User)

Ver [[Autenticacao]], [[Role-Permission]], [[Tenant]].

## Confirmado no código
- Modelo: `backend/app/models.py` (`User`).
- Pertence a um ou mais `Tenant` via `UserTenant` (relação N:N com `Role` associado por tenant).
- Tem muitas `UserSession` (uma por login ativo, revogável individualmente — ver [[Autenticacao]]).
- Tem muitos `AuditLog`.
- Campos de MFA existem no modelo (`two_factor_enabled`, `two_factor_secret`) mas **não são usados no fluxo de login ativo** — ver [[Autenticacao]] e [[Vulnerabilidades]] item 1.
- Senha armazenada com hash bcrypt (`backend/app/auth/core.py`).
- Pode ser bloqueado temporariamente após 5 tentativas de login falhas (`is_user_locked`, 15 minutos).

## Papel especial: usuário de plataforma
Usuários de `/ops` (staff da própria CorePet, não de um tenant cliente) usam um modelo/contexto de autenticação **separado** (`platform_auth_models.py`, `PlatformAuthContext`) — não confundir com `User` de tenant.

## Utilizado por
- [[Autenticacao]], [[Autorizacao]]
- [[Role-Permission]] (vínculo via `UserTenant`)
- Praticamente toda funcionalidade que registra autoria (ex.: `vendedor_id` em [[Venda]])

## Não identificado
- ❓ Se há expectativa de reativar MFA para este modelo (o schema já suporta).
