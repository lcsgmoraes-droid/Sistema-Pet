---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_evolucoes_internacao

Ver [[vet_internacoes]], [[vet_internacao_procedimentos_agenda]].

## Definição
Registro periódico de sinais vitais durante uma internação.

## Confirmado no código
- Modelo: `veterinario_models.py:656-680` (`EvolucaoInternacao`).
- ⚠️ FK fantasma: `user_id` é `Integer` (NOT NULL) sem `ForeignKey()` — inconsistente com o padrão do resto do arquivo, onde quase todo `user_id` tem FK real para `users.id`.

## Relacionamentos
- FK de saída real: `internacao_id → vet_internacoes.id`.
- Referenciada por: [[vet_internacao_procedimentos_agenda]]`.procedimento_evolucao_id`.

## Utilizado por
- `veterinario_internacao_routes_parts/historico_routes.py`, `mutacao_routes.py`.

## Não identificado
- `user_id` deveria ser FK real e não é.
