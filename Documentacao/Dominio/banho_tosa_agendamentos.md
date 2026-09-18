---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_agendamentos

Ver [[Cliente]], [[Pet]], [[banho_tosa_agendamento_servicos]], [[banho_tosa_atendimentos]], [[vet_perfil_comportamental]].

## Definição
Agendamento de banho/tosa, com profissionais designados (banhista, tosador) e snapshot de dados físicos do pet no momento do agendamento.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/agenda.py:19-71` (`BanhoTosaAgendamento`).
- Colunas: `status` (default "agendado"), `origem` (default "balcao"), `restricoes_veterinarias_snapshot` (JSON), `perfil_comportamental_snapshot` (JSON).
- ⚠️ FK fantasma: `taxi_dog_id` sem `ForeignKey()` nem `relationship()` — assimétrico, já que o lado inverso ([[banho_tosa_taxi_dog]]`.agendamento_id`) é FK real.
- ⚠️ **Docstring enganosa confirmada**: apesar do nome `perfil_comportamental_snapshot` sugerir vínculo com [[vet_perfil_comportamental]] (que a própria docstring do veterinário diz "alimentar Banho e Tosa"), esse campo é preenchido só com `pet.porte`/`pet.peso`/`pet.cor_pelagem` — atributos físicos do próprio [[Pet]], não dados comportamentais do módulo veterinário. Não há nenhuma referência real a `vet_perfil_comportamental` em todo o módulo.

## Relacionamentos
- FKs de saída: `cliente_id → clientes.id`, `pet_id → pets.id`, `responsavel_agendamento_user_id → users.id`, `profissional_principal_id → clientes.id`, `banhista_id → clientes.id`, `tosador_id → clientes.id`, `recurso_id → banho_tosa_recursos.id`.
- Referenciada por: [[banho_tosa_agendamento_servicos]]`.agendamento_id`, [[banho_tosa_atendimentos]]`.agendamento_id`, [[banho_tosa_taxi_dog]]`.agendamento_id`.

## Utilizado por
- `banho_tosa_api/agenda_routes.py:163-198` (criação).

## Não identificado
- ⚠️ Divergência entre o que a docstring de `vet_perfil_comportamental` promete e o que o código realmente faz — vale corrigir a docstring ou implementar o vínculo de verdade.
