---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_perfil_comportamental

Ver [[Pet]].

## Definição
Perfil comportamental do pet (1:1) — descrito no código como alimentando o módulo de Banho e Tosa.

## Confirmado no código
- Modelo: `veterinario_models.py:863-887` (`PerfilComportamental`). `pet_id` unique (1:1 por pet).
- Colunas: `temperamento`, `reacao_animais`, `reacao_pessoas`, `medo_secador`, `medo_tesoura`, `aceita_focinheira`, `comportamento_carro`.

## Relacionamentos
- FKs de saída: `pet_id → pets.id` (unique), `user_id → users.id`.

## Utilizado por
- `veterinario_acompanhamento_routes.py`.

## Não identificado
- ❓ Consumo efetivo por um módulo "Banho e Tosa" não confirmado nesta pesquisa (fora do escopo) — a integração está declarada só na docstring do modelo.
