---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — movimentacoes_financeiras

Ver [[contas_bancarias]], [[categorias_financeiras]], [[formas_pagamento]].

## Definição
Extrato unificado de todas as movimentações financeiras do tenant.

## Confirmado no código
- Modelo: `financeiro/models_caixa.py:56-99` (`MovimentacaoFinanceira`).
- Colunas: `conta_bancaria_id`, `categoria_id` (sem `nullable=False`), `forma_pagamento_id`, `user_id`, `origem_tipo`+`origem_id` (venda/compra/nfe/despesa/... — FK polimórfica intencional, sem `ForeignKey()` real).

## Relacionamentos
- FKs de saída: `contas_bancarias.id`, `categorias_financeiras.id`, `formas_pagamento.id`, `users.id`.
- `origem_id` referencia informalmente venda/compra/nfe/despesa conforme `origem_tipo`, sem constraint de banco.
- Sem referências de entrada (nenhuma tabela tem FK apontando para `movimentacoes_financeiras`).

## Utilizado por
- `contas_bancarias_routes.py`, `financeiro/contas_pagar_manutencao_routes.py`, `financeiro/contas_pagar_pagamento_service.py`.

## Não identificado
- Nada notável além da FK polimórfica já citada.
