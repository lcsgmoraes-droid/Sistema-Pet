---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_agendamentos

Ver [[Pet]], [[Cliente]], [[vet_consultorios]], [[vet_consultas]].

## Definição
Agendamento da agenda veterinária (consulta, retorno, vacina, cirurgia, emergência, exame, internação).

## Confirmado no código
- Modelo: `veterinario_models.py:245-297` (`AgendamentoVet`).
- Colunas: `status` (agendado/confirmado/em_atendimento/finalizado/cancelado/faltou), `tipo`, `pretriagem` (JSON, respondida pelo tutor no app), `is_emergencia`.
- `veterinario_id` aponta para `clientes.id` — **veterinário é modelado como [[Cliente]]** com `tipo_cadastro=veterinario` (convenção de aplicação, sem validação garantida por FK/enum no banco).

## Relacionamentos
- FKs de saída: `pet_id → pets.id`, `cliente_id → clientes.id` (tutor), `veterinario_id → clientes.id`, `consultorio_id → vet_consultorios.id`, `user_id → users.id`, `consulta_id → vet_consultas.id` (consulta gerada), `consulta_origem_id → vet_consultas.id` (consulta de origem em caso de retorno).
- Relationship `consulta` com `back_populates="agendamento"` bidirecional com `ConsultaVet.agendamento`.

## Utilizado por
- `veterinario_agendamentos.py`, `veterinario_agenda_routes.py`/`veterinario_agenda_routes_parts/*`, `routes/app_vet_routes.py`, `veterinario_calendar.py`.

## Não identificado
- Padrão "veterinário = Cliente" não tem validação de tipo garantida a nível de banco — vale nota para o time.
