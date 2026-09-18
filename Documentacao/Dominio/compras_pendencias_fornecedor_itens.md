---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — compras_pendencias_fornecedor_itens

Ver [[compras_pendencias_fornecedor]], [[notas_entrada_itens]], [[Produto]].

## Definição
Item de linha de uma [[compras_pendencias_fornecedor|pendência de fornecedor]] — quantidade divergente encontrada na conferência.

## Confirmado no código
- Modelo: `compras_pendencias_models.py:86-132` (`CompraPendenciaFornecedorItem`).
- Colunas: `quantidade_nf`, `quantidade_recebida`, `quantidade_faltante`, `quantidade_avariada`, `valor_unitario`, `valor_total_divergente`, `status_conferencia` (default `falta`), `acao_sugerida` (default `contatar_fornecedor`), `resolvido`.

## Relacionamentos
- FKs de saída: `pendencia_id → compras_pendencias_fornecedor.id`, `nota_entrada_item_id → notas_entrada_itens.id` (nullable), `produto_id → produtos.id` (nullable).
- Sem referências de entrada.

## Utilizado por
- `compras_pendencias_serializacao.py` (`_sincronizar_itens_pendencia`, importado em `compras_pendencias_criacao_routes.py:29`).

## Não identificado
- Nada notável.
