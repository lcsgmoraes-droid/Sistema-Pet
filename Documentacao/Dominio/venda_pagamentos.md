---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — venda_pagamentos

Ver [[Venda]], [[operadoras_cartao]], [[operadoras_cartao_taxas]].

## Definição
Forma(s) de pagamento usada(s) numa [[Venda]] (pode haver mais de uma por venda). Carrega também os dados de conciliação com gateway online (Mercado Pago etc.).

## Confirmado no código
- Modelo: `vendas_models.py:580-685` (`VendaPagamento`).
- Colunas: `venda_id`, `forma_pagamento` (string livre), `status_conciliacao` (nao_conciliado/conciliado), campos de gateway (`gateway_provider`, `gateway_payment_id`, `gateway_fee_amount`, `gateway_net_amount`, `gateway_gross_amount`).
- ⚠️ **Padrão de "FK fantasma"**: `forma_pagamento_id`, `operadora_id` e `taxa_cartao_regra_id` são `Integer` **sem `ForeignKey()`**, apesar do nome sugerir vínculo real com `formas_pagamento.id`/[[operadoras_cartao]]`.id`/[[operadoras_cartao_taxas]]`.id`. O comentário no código em `operadora_id` (linha 607-609) diz literalmente `# was: ForeignKey('operadoras_cartao.id') - tabela não existe` — **comentário desatualizado**: a tabela existe hoje (ver [[operadoras_cartao]]), mas o FK nunca foi restaurado.
- Relationship `operadora_cartao` está comentada no código com `# TODO: Criar modelo OperadoraCartao` (linha 646) — também desatualizado, o modelo existe.

## Relacionamentos
- FK de saída real: só `vendas.id` (CASCADE).
- `forma_pagamento_id`/`operadora_id`/`taxa_cartao_regra_id` referenciam informalmente `formas_pagamento`/[[operadoras_cartao]]/[[operadoras_cartao_taxas]], mas sem constraint de banco.
- Sem referências de entrada.

## Utilizado por
- Criação: `vendas/finalizacao_pagamentos.py:422` (resolve `operadora_id`/taxa nas linhas 302-406).
- `clientes/financeiro_baixa_lote_routes.py:219`, `routes/ecommerce_webhooks_sales.py:131` (webhook de pagamento e-commerce).

## Não identificado
- 🟠 Dívida técnica confirmada: três campos que deveriam ser FK são inteiros soltos — indício de refactor/migração incompleta entre o módulo de vendas e o de operadoras de cartão. Recomenda-se ao time avaliar restaurar as constraints.
