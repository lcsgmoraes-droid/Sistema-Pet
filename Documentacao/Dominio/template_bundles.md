---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — template_bundles

Ver [[template_items]], [[tenant_template_installs]], [[Tenant]].

## Definição
Pacote de template global do sistema (ex.: catálogo padrão de ração aplicado no onboarding de um tenant novo).

## Confirmado no código
- Modelo: `template_models.py:18-38` (`TemplateBundle`). Tabela global (não tenant-scoped).
- `UniqueConstraint(bundle_code, version)`.
- ⚠️ Ligação com [[template_items]]/[[tenant_template_installs]] é feita por `bundle_code`+`version` em **texto**, não por FK real — risco de inconsistência silenciosa se um item referenciar um bundle/versão inexistente (nada impede no banco).

## Relacionamentos
- Sem FK de saída nem de entrada real (ligação lógica por código/versão).

## Utilizado por
- `services/tenant_onboarding_*.py` (`tenant_onboarding_service.py`, `_runner.py`, `_template_contracts.py`, `_item_installs.py`, `_contract.py`).
- `onboard_tenant_defaults` chamado no fluxo de criação de conta (`auth_routes_multitenant.py:67`) — uso real confirmado, não código morto.

## Não identificado
- Ligação por código/versão em vez de FK é ponto sem garantia de integridade referencial do banco.
