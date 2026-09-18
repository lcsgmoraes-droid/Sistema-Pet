---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — comissoes_itens

Ver [[Venda]], [[Cliente]], [[ContaPagar]], [[comissoes_configuracao]].

## Definição
Comissão calculada item a item de uma venda, por funcionário.

## Confirmado no código
- Modelo ORM: `comissoes_models.py:686-764` (`ComissaoItem`). Docstring explica schema próprio (`data_criacao`/`data_atualizacao`), `tenant_id` do mixin tornado `NOT NULL` pela migration `pm20260609a1` com backfill via venda.
- Colunas: `status` (pendente/fechada/pago/estornado), campos de estorno (`data_estorno`, `motivo_estorno`).
- ⚠️ FKs fantasmas: `venda_item_id`, `produto_id`, `categoria_id`, `subcategoria_id` são `Integer` sem `ForeignKey()`.
- ⚠️ **Colisão de nome de classe**: existe um `ComissaoItem(BaseModel)` **Pydantic** totalmente diferente em `comissoes_avancadas_models.py:79` (schema de request/response da API, não tabela de banco). São coisas distintas — `comissoes_avancadas/conferencia_routes.py` importa a Pydantic, `dre_canais/agregacao.py`/`relatorio_vendas_preloads.py` importam a ORM real. Risco de confusão para quem grepa só "ComissaoItem" sem checar o import.

## Relacionamentos
- FKs de saída reais: `venda_id → vendas.id` (NOT NULL), `funcionario_id → clientes.id` (NOT NULL), `conta_pagar_id → contas_pagar.id` (nullable).

## Utilizado por
- `dre_canais/agregacao.py`, `relatorio_vendas_preloads.py`, `services/acerto_service.py`.

## Não identificado
- Ver colisão de nome já documentada acima.
