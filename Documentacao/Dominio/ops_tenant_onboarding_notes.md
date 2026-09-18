---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ops_tenant_onboarding_notes

Ver [[Tenant]], [[platform_admins]], [[ops_alerts]].

## Definição
Nota imutável de acompanhamento de onboarding de um tenant, feita por admin de plataforma. ✅ Única tabela do arquivo `ops_models.py` com FKs reais e imutabilidade reforçada por CHECK — padrão mais rigoroso que as demais tabelas `ops_*`.

## Confirmado no código
- Modelo: `ops_models.py:153-188` (`OpsTenantOnboardingNote`).
- `note` com `CheckConstraint(length BETWEEN 3 AND 1000)` no próprio banco.

## Relacionamentos
- FKs de saída (ambas reais, diferente do resto do arquivo): `tenant_id → tenants.id` (CASCADE), `created_by_platform_admin_id → platform_admins.id` (RESTRICT).

## Utilizado por
- `services/ops_tenants_service.py`, `routes/ops_tenants_routes.py` (registrado em `main_routers.py:181-182,258`).

## Não identificado
- Assimetria de padrão FK dentro do próprio `ops_models.py` — as outras 4 tabelas do arquivo não têm FK real de `tenant_id`. Decisão de design (telemetria cross-tenant vs. nota vinculada a um tenant específico), mas vale ter registrado.
