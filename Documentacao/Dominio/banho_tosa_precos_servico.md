---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_precos_servico

Ver [[banho_tosa_servicos]], [[banho_tosa_parametros_porte]].

## Definição
Matriz de precificação serviço×porte×pelagem, com estimativas de água/energia/tempo por combinação — insumo do dashboard de custos.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/cadastros.py:113-142` (`BanhoTosaPrecoServico`).
- `UniqueConstraint` (tenant, servico, porte, pelagem).

## Relacionamentos
- FKs de saída: `servico_id → banho_tosa_servicos.id`, `porte_id → banho_tosa_parametros_porte.id`.

## Utilizado por
- Cadastro de preços do módulo.

## Não identificado
- Nada notável.
