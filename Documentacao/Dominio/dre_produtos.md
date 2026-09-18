---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — dre_produtos

Ver [[dre_periodos]], [[Produto]].

## Definição
Rentabilidade por produto dentro de um período de DRE Inteligente.

## Confirmado no código
- Modelo: `ia/aba7_models.py:105-129` (`DREProduto`).
- `produto_id` sem FK (apenas index).

## Relacionamentos
- FK de saída: `dre_periodo_id → dre_periodos.id` (sem `ondelete`).

## Utilizado por
- Módulo DRE Inteligente.

## Não identificado
- `produto_id` deveria ser FK real.
