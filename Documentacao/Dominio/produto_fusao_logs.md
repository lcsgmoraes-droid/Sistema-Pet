---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_fusao_logs

Ver [[Produto]], [[produto_sku_aliases]].

## Definição
Log de auditoria de fusão (merge/dedup) entre dois produtos duplicados.

## Confirmado no código
- Modelo: `produto_identity_models.py:24-41` (`ProdutoFusaoLog`).
- Colunas: `principal_id`, `duplicado_id`, `user_id`, `estrategia_estoque`, `motivo`, `antes`/`depois`/`referencias` (JSON).
- Unique `(tenant_id, duplicado_id)`.
- ⚠️ Design deliberado: `principal_id`/`duplicado_id` **propositalmente não são `ForeignKey`** — comentário explícito na linha 32 ("generic history transfer must never rewrite an audit"), para que o log sobreviva mesmo que o produto duplicado seja fisicamente apagado depois.

## Relacionamentos
- FK real: só `user_id → users.id`. `principal_id`/`duplicado_id` são `Integer` soltos por design ("soft FK" intencional, não omissão acidental).
- Sem referências reversas.

## Utilizado por
- `services/produto_merge_safety.py` (log criado ao fundir produtos via `services/produto_merge_service.py`).

## Não identificado
- Nada notável — a ausência de FK é intencional e documentada no próprio código.
