---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_prescricoes

Ver [[vet_consultas]], [[vet_itens_prescricao]], [[Pet]].

## Definição
Receita médica veterinária vinculada a uma consulta.

## Confirmado no código
- Modelo: `veterinario_models.py:410-439` (`PrescricaoVet`).
- Colunas: `tipo_receituario` (simples/controle_especial_b/a/veterinaria_especial), `hash_receita` (validação/QR).
- ⚠️ `veterinario_id` é nullable — diferente da maioria das outras tabelas do módulo, onde o veterinário responsável é obrigatório.
- Relationship `itens` com `cascade="all, delete-orphan"`.

## Relacionamentos
- FKs de saída: `consulta_id → vet_consultas.id`, `pet_id → pets.id`, `veterinario_id → clientes.id` (nullable), `user_id → users.id`.
- Referenciada por: [[vet_itens_prescricao]]`.prescricao_id`.

## Utilizado por
- Criada em `veterinario_consultas_routes.py` junto com os itens.

## Não identificado
- ❓ Não encontrada geração de PDF de receita em `pdf_veterinario.py` (grep vazio) — pode estar em outro módulo não localizado, ou não existir ainda.
- `veterinario_id` nullable é uma inconsistência potencial a validar com o time.
