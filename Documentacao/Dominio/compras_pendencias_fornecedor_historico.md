---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — compras_pendencias_fornecedor_historico

Ver [[compras_pendencias_fornecedor]].

## Definição
Timeline de eventos de uma [[compras_pendencias_fornecedor|pendência de fornecedor]] (mudanças de status, observações).

## Confirmado no código
- Modelo: `compras_pendencias_models.py:135-164` (`CompraPendenciaFornecedorHistorico`).
- Colunas: `tipo` (evento do timeline), `observacao`, `status_anterior`, `status_novo`.

## Relacionamentos
- FKs de saída: `pendencia_id → compras_pendencias_fornecedor.id`, `user_id → users.id`.
- Sem referências de entrada.

## Utilizado por
- Populado via helper `_adicionar_historico` (`compras_pendencias_serializacao.py`, chamado em `compras_pendencias_criacao_routes.py:26`) sempre que o status da pendência muda.

## Não identificado
- Nada notável.
