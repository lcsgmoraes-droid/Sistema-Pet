---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_recorrencias

Ver [[Cliente]], [[Pet]], [[banho_tosa_servicos]], [[banho_tosa_pacote_creditos]].

## Definição
Agenda recorrente de banho/tosa (ex.: a cada 30 dias), com canal de lembrete.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/pacotes.py:103-127` (`BanhoTosaRecorrencia`).
- Colunas: `proxima_execucao`, `canal_lembrete`.

## Relacionamentos
- FKs de saída: `cliente_id → clientes.id`, `pet_id → pets.id`, `servico_id → banho_tosa_servicos.id` (nullable), `pacote_credito_id → banho_tosa_pacote_creditos.id` (nullable).

## Utilizado por
- Lembretes automáticos de recorrência.

## Não identificado
- Nada notável.
