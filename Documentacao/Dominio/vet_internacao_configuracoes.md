---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_internacao_configuracoes

Ver [[Tenant]].

## Definição
Configuração (1:1 por tenant) do módulo de internação — número de baias disponíveis.

## Confirmado no código
- Modelo: `veterinario_models.py:644-653` (`InternacaoConfig`). Índice unique por tenant. `total_baias` (default 12).

## Relacionamentos
- FK de saída: `user_id → users.id`.

## Utilizado por
- `veterinario_internacao_routes_parts/listagem_config_routes.py`.

## Não identificado
- Nada notável.
