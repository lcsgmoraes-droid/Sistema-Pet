---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — notas_entrada_itens

Ver [[notas_entrada]], [[Produto]], [[compras_pendencias_fornecedor_itens]].

## Definição
Item de linha de uma [[notas_entrada|nota de entrada]], com dados fiscais completos do XML e vínculo (automático/IA) ao produto do catálogo.

## Confirmado no código
- Modelo: `produtos_compras_models.py:240-299` (`NotaEntradaItem`).
- Colunas: dados fiscais (`codigo_produto`, `ncm`, `cest`, `cfop`, `origem`, alíquotas ICMS/PIS/COFINS, `ean`, `ean_tributario`, `lote`, `data_validade`), `produto_id` (nullable) com `vinculado`/`confianca_vinculo` (vínculo via IA/matching), `status` (pendente/vinculado/nao_vinculado/processado), campos de conferência física (`quantidade_conferida`, `quantidade_avariada`, `acao_sugerida`), campos de rateio online.

## Relacionamentos
- FKs de saída: `nota_entrada_id → notas_entrada.id`, `produto_id → produtos.id` (nullable).
- Referenciada por: [[compras_pendencias_fornecedor_itens]]`.nota_entrada_item_id`.

## Utilizado por
- `compras_pendencias_notas.py:128-133` (`_itens_divergentes`, cálculo de divergência de conferência).
- `notas_entrada/processamento_routes.py` (`_montar_lotes_entrada_item`, gera lotes de estoque a partir de itens vinculados).

## Não identificado
- Nada notável.
