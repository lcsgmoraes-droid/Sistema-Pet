---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — tenant_template_installs

Ver [[template_bundles]], [[Tenant]], [[tenant_template_item_installs]].

## Definição
Registro de auditoria de instalação de um bundle de template num tenant.

## Confirmado no código
- Modelo: `template_models.py:71-100` (`TenantTemplateInstall`).
- Colunas: `status` (default "completed"), `dry_run`, `summary` (JSON).
- `UniqueConstraint(tenant_id, bundle_code, bundle_version)` — impede reinstalar o mesmo bundle/versão duas vezes no mesmo tenant.
- ⚠️ `created_by_user_id` é Integer sem `ForeignKey()` — FK fantasma.

## Relacionamentos
- Sem FK de saída real (ligação com [[template_bundles]] também é lógica via código/versão).

## Utilizado por
- Runner de onboarding (`tenant_onboarding_runner.py`/`tenant_onboarding_service.py`).

## Não identificado
- `created_by_user_id` deveria ser FK real.
