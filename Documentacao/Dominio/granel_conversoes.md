---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — granel_conversoes

Ver [[produto_granel_vinculos]], [[Produto]], [[estoque_movimentacoes]].

## Definição
Log imutável de cada conversão granel executada (pacote fechado → kg a granel), com snapshot de estoque antes/depois. É o registro de auditoria de [[produto_granel_vinculos]] em ação.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:150-180` (`GranelConversao`).
- Colunas: `produto_granel_id`/`produto_origem_id`, `quantidade_origem`, `peso_por_unidade_kg`, `quantidade_granel_kg`, snapshot `estoque_origem_anterior/novo` e `estoque_granel_anterior/novo`, `documento`, `status` (default `"confirmado"`), `user_id` (NOT NULL — diferente do vínculo, que é nullable).

## Relacionamentos
- FKs de saída: `produto_granel_id → produtos.id`, `produto_origem_id → produtos.id`, `user_id → users.id`.
- Sem referências reversas de outras tabelas.

## Utilizado por
- `estoque/granel.py:348` (`executar_conversao_granel`, cria o registro).
- `pedidos_compra/sugestao_queries.py`.

## Não identificado
- Nada notável.
