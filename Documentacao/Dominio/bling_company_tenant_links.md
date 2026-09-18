---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — bling_company_tenant_links

Ver [[Tenant]], [[vet_partner_link]], [[bling_connections]].

## Definição
Índice global cross-tenant: `companyId` do Bling autenticado no webhook → tenant CorePet. Resolve o tenant **antes** de qualquer contexto de tenant estar disponível.

## Confirmado no código
- Modelo: `bling_connection_models.py:74-89` (`BlingCompanyTenantLink`). `Base` puro (deliberadamente não tenant-scoped) — mesmo padrão cross-tenant de [[vet_partner_link]].
- PK é o próprio `company_id` (String); `tenant_id` é UUID `unique=True` (1↔1, não FK real para `tenants.id`).
- ✅ Checagem explícita de conflito: ao salvar uma conexão, se `company_id` mudou, remove o link antigo e valida que a empresa Bling não está vinculada a outro tenant — só 1 tenant pode reivindicar cada `company_id`.

## Relacionamentos
- Sem FK real (tenant_id é UUID solto, por design do padrão cross-tenant).

## Utilizado por
- `services/bling_connection_service.py` — `resolve_bling_webhook_tenant()` (resolve tenant a partir do `company_id` no fluxo de webhook), `connected_bling_tenant_ids()` (lista tenants conectados, usado por schedulers/monitoramento).

## Não identificado
- Confirma que é padrão cross-tenant deliberado, não erro de modelagem — mesma categoria de [[vet_partner_link]], vale considerar as duas juntas numa eventual auditoria de isolamento multi-tenant.
