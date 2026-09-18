---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — campanha_validade_exclusoes

Ver [[campanha_validade_automatica]], [[Produto]], [[produto_lotes]].

## Definição
Lista de exclusão da campanha de desconto por validade: permite excluir um produto inteiro ou um lote específico do desconto automático.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:265-289` (`CampanhaValidadeExclusao`).
- Colunas: `produto_id`, `lote_id` (nullable — exclusão pode ser por produto inteiro OU por lote específico), `ativo`, `motivo`, `observacao`.

## Relacionamentos
- FKs de saída: `produto_id → produtos.id` (CASCADE, index), `lote_id → produtos_lotes.id` (CASCADE, index).
- Sem referências reversas.

## Utilizado por
- `services/validade_campanha_service.py`.

## Não identificado
- Nada notável.
