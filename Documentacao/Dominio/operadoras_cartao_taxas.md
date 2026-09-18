---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — operadoras_cartao_taxas

Ver [[operadoras_cartao]], [[venda_pagamentos]].

## Definição
Taxa de cartão por bandeira/modalidade/parcelas de uma [[operadoras_cartao|operadora]] — motor de cálculo de custo de cartão na venda.

## Confirmado no código
- Modelo: `operadoras_models.py:109-160` (`OperadoraCartaoTaxa`) — único local que define esta tabela (não existe equivalente no arquivo órfão `operadoras_cartao_models.py`, o que reforça que este último é protótipo abandonado).
- Colunas: `operadora_id`, `bandeira`, `modalidade`, `parcelas` (chave composta de contexto, `UniqueConstraint uq_operadora_taxa_contexto` em `tenant_id, operadora_id, bandeira, modalidade, parcelas`), `taxa_percentual` (Numeric 7,4), `taxa_fixa` (Numeric 10,2), `prazo_recebimento_dias`, `user_id`.
- `CheckConstraint` de `parcelas` (1-24) e `taxa_percentual` (0-100) no próprio banco.

## Relacionamentos
- FKs de saída: `operadoras_cartao.id` (CASCADE), `users.id`.
- Referenciada informalmente (sem FK real) por [[venda_pagamentos]]`.taxa_cartao_regra_id`, preenchido a partir de `resolution.regra_id` em `services/card_fee_service.py:357`.

## Utilizado por
- `services/card_fee_service.py` (`resolve_card_fee` — motor de resolução de taxa por bandeira/modalidade/parcelas).
- `operadoras_routes.py` (`GET/PUT /{operadora_id}/taxas`), `vendas/finalizacao_pagamentos.py`, `routes/app_mobile_funcionario_pdv/pagamentos.py`.

## Não identificado
- Nada notável além do vínculo informal com [[venda_pagamentos]] já documentado lá.
