---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Pet

Ver [[Cliente]], [[Veterinario]], [[Banho-e-Tosa]].

## Confirmado no código
- Modelo: `backend/app/models_cadastros.py` (`Pet`).
- `cliente_id` → `clientes.id` (tutor).
- `user_id` → `users.id` (vínculo com conta de app, quando o tutor tem acesso ao aplicativo).
- Relaciona-se com `Especie`/`Raca` (mesmo arquivo de modelo).
- É referenciado por `VendaItem.pet_id` (venda associada a um pet específico — comum em pet shop para ração/serviço recorrente por animal).

## Utilizado por
- [[Veterinario]] (consultas, exames, prontuário, internações)
- [[Banho-e-Tosa]] (agendamentos)
- [[PDV-Vendas]] (item de venda vinculado a um pet, ex. recorrência de ração)
- App mobile (tutores acompanham o próprio pet)

## Não identificado
- ⚠️ Não identificado no código analisado: rota específica de upload de foto de pet e suas validações de segurança (mencionado como não encontrado pelo agente de segurança) — ❓ necessita validação adicional se esse fluxo existir fora do escopo já coberto.
