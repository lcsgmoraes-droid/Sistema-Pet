---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — dre_subcategorias

Ver [[dre_categorias]], [[categorias_financeiras]], [[tipo_despesas]], [[movimentacoes_bancarias]], [[regras_conciliacao]], [[regras_classificacao_dre]].

## Definição
Hub central do DRE — quase toda classificação financeira do sistema acaba apontando pra cá. Define regras de rateio de custo (direto/indireto/corporativo) e escopo (loja física/online/ambos).

## Confirmado no código
- Modelo: `dre_plano_contas_models.py:64-93` (`DRESubcategoria`).
- Enums: `tipo_custo` (DIRETO/INDIRETO_RATEAVEL/CORPORATIVO), `base_rateio` (FATURAMENTO/PEDIDOS/PERCENTUAL/MANUAL, nullable), `escopo_rateio` (LOJA_FISICA/ONLINE/AMBOS), `custo_pe` (string livre 'fixo'/'variavel'/null, usado no cálculo de Ponto de Equilíbrio).

## Relacionamentos
- FKs de saída: `categoria_id → dre_categorias.id`, `categoria_financeira_id → categorias_financeiras.id` (SET NULL).
- Referenciada por (hub — muitas): [[categorias_financeiras]]`.dre_subcategoria_id`, [[tipo_despesas]]`.dre_subcategoria_id`, [[movimentacoes_bancarias]]`.categoria_dre_id`, [[regras_conciliacao]]`.categoria_dre_id`, [[regras_classificacao_dre]]`.dre_subcategoria_id`, [[historico_classificacao_dre]]`.dre_subcategoria_id`.

## Utilizado por
- `categorias_routes.py`, `contas_receber_criacao_routes.py`, `dashboard/ponto_equilibrio_margem.py`, `dashboard/ponto_equilibrio_routes.py`.

## Não identificado
- Nada notável — é literalmente o ponto de convergência de todo o sistema de classificação financeira/DRE.
