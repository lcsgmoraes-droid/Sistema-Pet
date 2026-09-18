---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_fotos_clinicas

Ver [[vet_consultas]], [[Pet]].

## Definição
Foto clínica (dermatologia, ferida, pós-operatório) vinculada a uma consulta.

## Confirmado no código
- Modelo: `veterinario_models.py:835-855` (`FotoClinica`). `consulta_id` NOT NULL (diferente de outras tabelas do módulo, aqui é obrigatório).
- Relationship consistente (`back_populates="fotos_clinicas"`) com `ConsultaVet.fotos_clinicas`.

## Relacionamentos
- FKs de saída: `consulta_id → vet_consultas.id`, `pet_id → pets.id`, `user_id → users.id`.

## Utilizado por
- `veterinario_agendamentos.py:275-277` (checa se consulta tem fotos vinculadas).

## Não identificado
- Nada notável.
