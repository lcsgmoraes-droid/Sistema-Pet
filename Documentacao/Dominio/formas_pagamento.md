---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — formas_pagamento

Ver [[contas_bancarias]], [[operadoras_cartao]], [[formas_pagamento_taxas]], [[venda_pagamentos]].

## Definição
Forma de pagamento configurada pelo tenant (dinheiro, cartão, PIX, boleto, transferência), com regras de taxa e parcelamento.

## Confirmado no código
- Modelo: `financeiro/models_catalogos.py:56-122` (`FormaPagamento`).
- Colunas: `tipo`, `taxa_percentual`, `taxa_fixa`, `prazo_dias`/`prazo_recebimento` (⚠️ campos redundantes, comentário "manter compatibilidade"), `operadora` (string livre), `gera_contas_receber`, `permite_parcelamento`, `max_parcelas`/`parcelas_maximas` (⚠️ mesma redundância), `permite_antecipacao`.
- ⚠️ **FK fantasma confirmada**: `operadora_id` é `Integer` com comentário `# was: ForeignKey('operadoras_cartao.id')` (linha 92-95) dizendo que a tabela "não existe" — **isso está errado/desatualizado**: `operadoras_cartao` existe hoje (ver [[operadoras_cartao]]). A FK nunca foi restaurada; relationship correspondente também está comentada (linha 119).

## Relacionamentos
- FKs de saída reais: `conta_bancaria_destino_id → contas_bancarias.id`, `user_id → users.id`.
- Referenciada por: `formas_pagamento_taxas.forma_pagamento_id`, `movimentacoes_financeiras.forma_pagamento_id`.
- Relationships: `contas_receber`, `pagamentos`, `recebimentos`.

## Utilizado por
- `caixa_routes.py`, `clientes/financeiro_routes.py`, `comissoes_avancadas/pagamento_routes.py`.

## Não identificado
- 🟠 Mesmo achado de [[operadoras_cartao]]: `operadora_id` deveria ser FK real e não é — dívida técnica confirmada em dois lugares diferentes do sistema (aqui e em `venda_pagamentos`).
