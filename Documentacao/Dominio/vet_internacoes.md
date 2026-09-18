---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_internacoes

Ver [[Pet]], [[vet_consultas]], [[vet_evolucoes_internacao]], [[vet_internacao_procedimentos_agenda]], [[vet_orcamentos]].

## Definição
Internação de um pet (status: internado/alta/obito/transferido).

## Confirmado no código
- Modelo: `veterinario_models.py:615-641` (`InternacaoVet`).
- Relationship `evolucoes` com `cascade="all, delete-orphan"`.

## Relacionamentos
- FKs de saída: `pet_id → pets.id`, `consulta_id → vet_consultas.id` (nullable), `veterinario_id → clientes.id` (nullable), `user_id → users.id`.
- Referenciada por: [[vet_evolucoes_internacao]]`.internacao_id`, [[vet_internacao_procedimentos_agenda]]`.internacao_id`, [[vet_orcamentos]]`.internacao_id`.

## Utilizado por
- `veterinario_internacao.py`, `veterinario_internacao_routes.py`/`veterinario_internacao_routes_parts/*` (agenda, histórico, listagem/config, mutação), `routes/app_vet_routes.py`.

## Não identificado
- ❓ Não encontrada geração de [[ContaReceber]]/[[Venda]] diretamente a partir do fechamento de uma internação — o financeiro parece passar pelos procedimentos individuais executados dentro dela ([[vet_internacao_procedimentos_agenda]], mesmo padrão de `insumos`/`estoque_baixado` de [[vet_procedimentos_consulta]]), não por um evento único de "fechar internação". Merece investigação mais profunda se for mexer nesse fluxo.
