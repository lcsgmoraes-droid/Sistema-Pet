---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — template_items

Ver [[template_bundles]], [[tenant_template_item_installs]].

## Definição
Item de um [[template_bundles|bundle de template]] global (ex.: linha de catálogo padrão), copiado para tabelas tenant-owned durante o onboarding.

## Confirmado no código
- Modelo: `template_models.py:41-68` (`TemplateItem`).
- Colunas: `item_type` (discrimina o tipo de entidade que o payload representa), `payload` (JSON, obrigatório — conteúdo copiado para a tabela alvo do tenant).
- `UniqueConstraint(bundle_code, bundle_version, item_type, template_code)`.
- ⚠️ Mesma ligação lógica por código/versão (sem FK real) de [[template_bundles]].

## Relacionamentos
- Sem FK de saída nem de entrada real.

## Utilizado por
- Mesmo pipeline de onboarding de [[template_bundles]].

## Não identificado
- Ver achado de [[template_bundles]].
