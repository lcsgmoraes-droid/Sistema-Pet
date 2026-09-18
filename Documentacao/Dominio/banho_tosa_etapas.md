---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_etapas

Ver [[banho_tosa_atendimentos]], [[Cliente]], [[banho_tosa_recursos]].

## Definição
Linha do tempo operacional do atendimento (check-in, banho, secagem, tosa etc.), com duração prevista x real.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/operacional.py:82-111` (`BanhoTosaEtapa`).
- Colunas: `duracao_minutos`, `duracao_segundos`.

## Relacionamentos
- FKs de saída: `atendimento_id → banho_tosa_atendimentos.id` (CASCADE), `responsavel_id → clientes.id`, `recurso_id → banho_tosa_recursos.id`.

## Utilizado por
- Controle operacional do atendimento em tempo real.

## Não identificado
- Nada notável.
