---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_vacinas_registros

Ver [[Pet]], [[vet_protocolos_vacinas]], [[vet_consultas]].

## Definição
Registro de vacina aplicada em um pet.

## Confirmado no código
- Modelo: `veterinario_models.py:476-509` (`VacinaRegistro`).
- Colunas: `data_proxima_dose` (usado para lembretes/preventivo). Property `veterinario_responsavel` acessa `self.veterinario.nome`.

## Relacionamentos
- FKs de saída: `pet_id → pets.id`, `consulta_id → vet_consultas.id` (nullable), `veterinario_id → clientes.id` (nullable), `user_id → users.id`, `protocolo_id → vet_protocolos_vacinas.id` (nullable).

## Utilizado por
- `veterinario_preventivo.py` (cálculo de próximas doses/lembretes).

## Não identificado
- Nada notável.
