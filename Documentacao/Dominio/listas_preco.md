---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — listas_preco

Ver [[Produto]], [[produto_listas_preco]].

## Definição
Lista de preços nomeada (ex.: atacado/varejo/VIP), pensada para precificar produtos de forma diferenciada por canal/segmento.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:318-335` (`ListaPreco`).
- Colunas: `nome`, `descricao`, `user_id` (NOT NULL, criador), `ativo`.

## Relacionamentos
- FK de saída: `user_id → users.id`.
- Referenciada por: [[produto_listas_preco]] (`lista_preco_id`), relationship `produtos`.

## Utilizado por
- ⚠️ **Nenhum endpoint CRUD encontrado.** Único uso confirmado é leitura passiva via `Produto.listas_preco` em `routes/ecommerceai_integration_routes.py:212-213` (serialização) e remapeamento em `services/produto_merge_service.py` ao fundir produtos.

## Não identificado
- ⚠️ Possível feature incompleta/abandonada: modelo e relationships completos, mas sem rota de gestão localizada — pode ser gerenciada só via script/admin não encontrado nesta pesquisa.
