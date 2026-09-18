---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — dre_periodos

Ver [[dre_produtos]], [[dre_categorias_analise]], [[dre_comparacoes]], [[dre_insights]], [[historico_atualizacao_dre]].

## Definição
Período de apuração do DRE Inteligente (IA) — hub deste submódulo.

## Confirmado no código
- Modelo: `ia/aba7_models.py:26-99` (`DREPeriodo`).
- ⚠️ Único deste grupo que usa `TenantScoped, Base` em vez de `BaseTenantModel`, com comentário explicando migração manual de `tenant_id`. `usuario_id` mantido como "dono legado" sem FK.
- Relationship 1:N com [[historico_atualizacao_dre]] (cascade).

## Relacionamentos
- Referenciada por: [[dre_produtos]], [[dre_categorias_analise]], [[dre_comparacoes]] (2×: `periodo1_id`/`periodo2_id`), [[dre_insights]], [[historico_atualizacao_dre]]`.dre_periodo_id`.

## Utilizado por
- `dre_ia_routes_parts/anomalias_export_routes.py`, `dre_ia_routes_parts/base_routes.py`.

## Não identificado
- Inconsistência de base class (`TenantScoped` em vez de `BaseTenantModel`) — reflete migração manual, vale padronizar.
