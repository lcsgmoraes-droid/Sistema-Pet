---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_peso_registros

Ver [[Pet]], [[vet_consultas]].

## Definição
Curva de peso do pet ao longo do tempo.

## Confirmado no código
- Modelo: `veterinario_models.py:813-827` (`PesoRegistro`).

## Relacionamentos
- FKs de saída: `pet_id → pets.id`, `consulta_id → vet_consultas.id` (nullable), `user_id → users.id`.

## Utilizado por
- `veterinario_acompanhamento_routes.py`, `veterinario_agendamentos.py`, `veterinario_consultas_routes.py`.

## Não identificado
- Nada notável.
