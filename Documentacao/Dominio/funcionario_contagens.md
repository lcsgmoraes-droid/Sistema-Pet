---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — funcionario_contagens

Ver [[Cliente]], [[Produto]], [[funcionario_contagem_itens]].

## Definição
⚠️ Apesar do nome, é um recurso de **estoque/contagem via app mobile do funcionário**, não um dado de RH propriamente dito — cabeçalho de contagem avulsa de estoque.

## Confirmado no código
- Modelo: `funcionario_contagem_models.py:10-41` (`FuncionarioContagem`).
- Colunas: `titulo` (default "Contagem"), `observacao`, `status` (default "salva", string livre sem enum formal).
- `fornecedor_nome_snapshot` — snapshot para não quebrar se o fornecedor mudar/for removido.
- Nota de import: `app/produtos_models.py:29-32` reexporta esta classe como "compatibilidade para imports legados" — não é duplicação real de tabela, mas as rotas mobile importam via esse facade em vez do módulo original.

## Relacionamentos
- FKs de saída (todas reais, com `ForeignKey()`, ao contrário de [[cargos]]): `funcionario_id → clientes.id`, `fornecedor_id → clientes.id` (nullable), `user_id → users.id`.
- Referenciada por: [[funcionario_contagem_itens]]`.contagem_id` (CASCADE).

## Utilizado por
- `routes/app_mobile_funcionario_contagem_routes.py` (criação/consulta/exportação pelo app do funcionário).

## Não identificado
- ❓ Valores possíveis de `status` além de "salva" não foram confirmados (sem enum formal no código).
