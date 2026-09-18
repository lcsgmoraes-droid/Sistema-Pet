---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_orcamentos

Ver [[Pet]], [[Cliente]], [[vet_consultas]], [[vet_internacoes]], [[vet_orcamento_itens]].

## Definição
Orçamento veterinário — explicitamente documentado no código como "**sem movimentar estoque**" (docstring), puramente estimativo.

## Confirmado no código
- Modelo: `veterinario_models.py:726-766` (`OrcamentoVet`).
- Colunas: `status` (default `rascunho`), `custo_total_estimado`, `preco_total`, `margem_valor`/`margem_percentual`.
- Relationship `itens` com `cascade="all, delete-orphan"`.

## Relacionamentos
- FKs de saída: `user_id → users.id`, `consulta_id → vet_consultas.id` (nullable), `internacao_id → vet_internacoes.id` (nullable), `pet_id → pets.id` (nullable), `cliente_id → clientes.id` (nullable), `veterinario_id → clientes.id` (nullable).
- Referenciada por: [[vet_orcamento_itens]]`.orcamento_id`.

## Utilizado por
- `veterinario_orcamentos.py` (serialização), `veterinario_orcamentos_routes.py` (CRUD completo, resolve `produto_id`/`catalogo_id` dos itens contra [[Produto]]/[[vet_catalogo_procedimentos]] para enriquecer custos).

## Não identificado
- ❓ **Lacuna de fluxo possível**: não foi encontrada rota que converta um orçamento aceito em [[vet_procedimentos_consulta]]/[[Venda]]/[[ContaReceber]] automaticamente — parece ser puramente informativo para apresentar ao tutor, sem trilha de conversão automática confirmada. Vale confirmar com o time se essa conversão é manual ou se há um fluxo não encontrado nesta pesquisa.
