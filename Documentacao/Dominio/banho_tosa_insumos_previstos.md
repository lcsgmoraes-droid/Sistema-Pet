---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_insumos_previstos

Ver [[banho_tosa_servicos]], [[banho_tosa_parametros_porte]], [[Produto]], [[banho_tosa_insumos_usados]].

## Definição
Receita/BOM do serviço: por combinação serviço×porte, define qual produto (shampoo etc.) e quantidade padrão é esperado consumir.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/operacional.py:130-167` (`BanhoTosaInsumoPrevisto`).
- Flag `baixar_estoque` controla se o insumo previsto efetivamente gera baixa.

## Relacionamentos
- FKs de saída: `servico_id → banho_tosa_servicos.id` (CASCADE), `porte_id → banho_tosa_parametros_porte.id`, `produto_id → produtos.id` — **FK real**, diferente do padrão "insumo em JSON solto" visto no módulo veterinário ([[vet_procedimentos_consulta]]).

## Utilizado por
- Cálculo de custo previsto e geração de [[banho_tosa_insumos_usados]] real no atendimento.

## Não identificado
- Nada notável — bom exemplo de referência tipada, ao contrário do padrão inconsistente achado no módulo veterinário.
