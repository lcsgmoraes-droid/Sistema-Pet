---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_pacote_movimentos

Ver [[banho_tosa_pacote_creditos]], [[banho_tosa_atendimentos]].

## Definição
Ledger de uso/estorno/cancelamento de créditos de um pacote, com saldo após cada movimento.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/pacotes.py:72-100` (`BanhoTosaPacoteMovimento`).
- Colunas: `saldo_apos`.
- `movimento_origem_id` é auto-referência (self-FK) para estorno de um movimento anterior.

## Relacionamentos
- FKs de saída: `credito_id → banho_tosa_pacote_creditos.id` (CASCADE), `atendimento_id → banho_tosa_atendimentos.id` (nullable), `movimento_origem_id → banho_tosa_pacote_movimentos.id` (self, estorno), `created_by → users.id`.

## Utilizado por
- Fluxo de uso/estorno de crédito de pacote.

## Não identificado
- Nada notável.
