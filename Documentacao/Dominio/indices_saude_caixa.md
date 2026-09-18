---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — indices_saude_caixa

Ver [[fluxo_caixa]], [[Usuario]].

## Definição
Cache de índices de saúde financeira calculados (saldo, dias de caixa, score de saúde).

## Confirmado no código
- Modelo: `ia/aba5_models.py:88-121` (`IndicesSaudeCaixa`).
- Colunas: `saldo_atual`, `dias_de_caixa`, `score_saude`.

## Relacionamentos
- FK de saída: `usuario_id → users.id`.

## Utilizado por
- `ia/aba5_fluxo_caixa_parts/indices.py`.

## Não identificado
- Não está listada em `alembic/env.py`/`db/base.py`.
