---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — duplicatas_ignoradas

Ver [[Produto]].

## Definição
Par de produtos marcado como "não é duplicata" — evita que o detector de duplicatas de catálogo sugira o mesmo par de novo. Módulo de catálogo/estoque, não financeiro, apesar de listado neste bloco de pesquisa.

## Confirmado no código
- Modelo: `duplicatas_ignoradas_models.py:13-42` (`DuplicataIgnorada`).
- `UniqueConstraint("tenant_id", "produto_id_1", "produto_id_2")`.
- ⚠️ A unicidade **não normaliza a ordem do par**: apesar do docstring dizer "sempre salvar em ordem: menor ID primeiro", isso é responsabilidade da aplicação, não da constraint — `(5,3)` e `(3,5)` não colidiriam no banco se a aplicação não garantir a ordenação.

## Relacionamentos
- FKs de saída: `produto_id_1 → produtos.id` (NOT NULL), `produto_id_2 → produtos.id` (NOT NULL), `usuario_id → users.id` (nullable).
- Sem referências de entrada.

## Utilizado por
- `racoes_sugestoes_duplicatas_routes.py`.

## Não identificado
- 🟡 Risco de duplicidade de linha se a aplicação não garantir consistentemente a ordenação do par — vale checar o service correspondente.
