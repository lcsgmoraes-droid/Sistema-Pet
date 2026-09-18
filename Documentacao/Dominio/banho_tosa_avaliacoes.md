---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_avaliacoes

Ver [[banho_tosa_atendimentos]], [[Cliente]], [[Pet]].

## Definição
Avaliação (NPS) de um atendimento de banho/tosa pelo tutor.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/avaliacoes.py:17-45` (`BanhoTosaAvaliacao`).
- Colunas: `nota_nps`, `nota_servico`, `comentario`, `origem`.

## Relacionamentos
- FKs de saída: `atendimento_id → banho_tosa_atendimentos.id` (CASCADE), `cliente_id → clientes.id`, `pet_id → pets.id`.

## Utilizado por
- `banho_tosa_avaliacoes_metrics.py` (agregação de métricas/NPS).

## Não identificado
- Nada notável.
