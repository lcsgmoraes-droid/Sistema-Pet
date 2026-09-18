---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — formas_pagamento_taxas

Ver [[configuracao_impostos]].

## Definição
Taxa percentual cobrada por número de parcelas para uma forma de pagamento (ex.: cartão de crédito em 3x tem taxa X%).

## Confirmado no código
- Modelo: `formas_pagamento_models.py:23-55` (`FormaPagamentoTaxa`).
- Colunas: `forma_pagamento_id` (FK real), `parcelas` (Integer), `taxa_percentual` (Numeric 5,2).
- `__table_args__ = {"extend_existing": True}` — indício de que o módulo foi remodelado mais de uma vez ao longo do histórico do projeto.

## Relacionamentos
- FK de saída: `formas_pagamento.id` (tabela definida em `financeiro/models_catalogos.py`, fora deste bloco).
- Sem referências de entrada.

## Utilizado por
- CRUD completo: `formas_pagamento_routes_parts/taxas_routes.py:23-171`.
- `utils/pdv_indicadores.py:100-103` (cálculo de indicadores do PDV).
- `criar_tabelas_formas_pagamento.py` (script de seed/setup).

## Não identificado
- Nada notável além do `extend_existing=True`.
