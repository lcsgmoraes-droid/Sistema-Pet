---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_fotos

Ver [[banho_tosa_atendimentos]].

## Definição
Foto antes/depois do pet num atendimento de banho/tosa.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/operacional.py:114-127` (`BanhoTosaFoto`). Armazenamento tratado em `banho_tosa_fotos_storage.py`.

## Relacionamentos
- FKs de saída: `atendimento_id → banho_tosa_atendimentos.id` (CASCADE), `created_by → users.id`.

## Utilizado por
- `banho_tosa_fotos_storage.py`.

## Não identificado
- Nada notável.
