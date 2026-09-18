---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_exames

Ver [[vet_consultas]], [[Pet]].

## Definição
Exame de um pet, com interpretação assistida por IA (resumo, confiança, alertas).

## Confirmado no código
- Modelo: `veterinario_models.py:517-556` (`ExameVet`).
- Colunas de IA: `interpretacao_ia`, `interpretacao_ia_resumo`, `interpretacao_ia_confianca`, `interpretacao_ia_alertas` (JSON), `interpretacao_ia_payload` (JSON).
- Relationship consistente (`back_populates="exames"`) com `ConsultaVet.exames`.

## Relacionamentos
- FKs de saída: `pet_id → pets.id`, `consulta_id → vet_consultas.id` (nullable), `user_id → users.id`.

## Utilizado por
- `veterinario_exames_routes.py`, `veterinario_exames_arquivos.py` (upload de arquivo/imagem), `veterinario_exames_ia.py` (interpretação por IA).

## Não identificado
- Nada notável.
