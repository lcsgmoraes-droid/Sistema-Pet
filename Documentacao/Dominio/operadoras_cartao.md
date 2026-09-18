---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — operadoras_cartao

Ver [[venda_pagamentos]], [[operadoras_cartao_taxas]].

## Definição
Operadora de cartão (ex.: Stone, Cielo, Rede) configurada pelo tenant, com integração de API opcional.

## Confirmado no código
⚠️ **Duplicação de modelo confirmada — um dos dois é código morto total.** Duas classes `OperadoraCartao` mapeiam o mesmo `__tablename__ = "operadoras_cartao"`:

| | `operadoras_cartao_models.py` | `operadoras_models.py` (**fonte de verdade**) |
|---|---|---|
| Base | `Base` puro (não tenant-scoped) | `BaseTenantModel` |
| `tenant_id` | `String(100)` manual | UUID herdado |
| Campos próprios | `template_id`, `codigo_estabelecimento`, `taxa_mdr_padrao`, `dias_recebimento_debito/credito` | `max_parcelas`, `api_enabled`, `api_endpoint`, `api_token_encrypted`, `cor`, `icone`, `user_id` |

**Investigação de uso real**: `from app.operadoras_cartao_models import` → **0 ocorrências em todo o repositório** (app, alembic, testes). `from app.operadoras_models import OperadoraCartao` → usado em `conciliacao_aba1_routes.py`, `operadoras_routes.py`, `routes/app_mobile_funcionario_pdv/pagamentos.py`, `vendas/finalizacao_pagamentos.py`, `services/card_operator_defaults.py`, `services/card_fee_service.py`. O Alembic (`alembic/env.py:51`) importa só `operadoras_models`. A migração real (`alembic/versions/zwr20260821a1_card_fee_rules.py:222-267`) cria a tabela física com o schema de `operadoras_models.py` — confirma que `operadoras_cartao_models.py` **nunca foi migrado para o banco**.

**Conclusão**: `operadoras_cartao_models.py` é 100% código morto/órfão — nunca importado em lugar nenhum, e seu schema nem corresponde à tabela física real. Padrão idêntico ao já encontrado em [[locais_estoque]]/[[kit_composicao]] em bloco anterior.

## Relacionamentos
- Referenciada informalmente (sem FK real de banco) por [[venda_pagamentos]]`.operadora_id` — ver detalhes do "FK fantasma" nesse arquivo.
- Referenciada com FK real por [[operadoras_cartao_taxas]]`.operadora_id` (CASCADE).

## Utilizado por
- `operadoras_routes.py`, `services/card_fee_service.py`, `services/card_operator_defaults.py`, `vendas/finalizacao_pagamentos.py:202`.

## Não identificado
- 🔴 **Risco a levar ao time**: mesmo o modelo vencedor tem integração parcial — `venda_pagamentos.operadora_id` e `financeiro_models.FormaPagamento.operadora_id` continuam Integer soltos (sem `ForeignKey` real), e as relationships ORM entre eles estão comentadas no código como "TEMPORARIAMENTE DESABILITADO". Recomenda-se: (a) remover/arquivar `operadoras_cartao_models.py`, (b) avaliar restaurar as FKs reais em `venda_pagamentos`.
