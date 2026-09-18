---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_internacao_procedimentos_agenda

Ver [[vet_internacoes]], [[Pet]], [[vet_evolucoes_internacao]].

## Definição
Agenda operacional de medicações/procedimentos de uma internação — como uma "prescrição hospitalar" com horário.

## Confirmado no código
- Modelo: `veterinario_models.py:683-718` (`InternacaoProcedimentoAgenda`).
- Colunas: `quantidade_prevista`/`quantidade_executada`/`quantidade_desperdicio`, `lembrete_minutos`, `status` (agendado/concluido/cancelado).

## Relacionamentos
- FKs de saída: `internacao_id → vet_internacoes.id`, `pet_id → pets.id`, `user_id → users.id`, `procedimento_evolucao_id → vet_evolucoes_internacao.id` (nullable).

## Utilizado por
- `veterinario_internacao_routes_parts/agenda_routes.py`, `routes/app_vet_routes.py:601-610` (lista para app mobile do vet).

## Não identificado
- Segue o mesmo padrão de `insumos`/`estoque_baixado` de [[vet_procedimentos_consulta]] (ver `veterinario_internacao_routes_parts/mutacao_routes.py:281-311`, `_aplicar_baixa_estoque_itens`) — provável ponto real de baixa de estoque para internação, não confirmado a fundo nesta pesquisa.
