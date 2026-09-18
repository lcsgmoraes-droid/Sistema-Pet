---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — fluxo_caixa

Ver [[Usuario]], [[indices_saude_caixa]], [[projecao_fluxo_caixa]].

## Definição
Lançamento do módulo de fluxo de caixa preditivo (IA), realizado/previsto/cancelado.

## Confirmado no código
- Modelo: `ia/aba5_models.py:31-73` (`FluxoCaixa`).
- Colunas: `tipo`/`categoria`/`valor`/`status`, `origem_tipo`/`origem_id` (rastreamento livre, sem FK real). `created_at`/`updated_at` mapeados para colunas em português `criado_em`/`atualizado_em`.
- ⚠️ O próprio arquivo tem strings `SQL_CREATE_*` como "esquema alternativo para criar manualmente se necessário" — sinal de que a tabela pode ter sido criada fora do fluxo normal de migration/ORM em algum momento.

## Relacionamentos
- FK de saída: `usuario_id → users.id`.

## Utilizado por
- `financeiro/fluxo_caixa_routes.py`, `ia/aba5_fluxo_caixa_parts/{acoes,base,indices,projecoes}.py`, `clientes/financeiro_baixa_lote_routes.py`.

## Não identificado
- ⚠️ Não está listada em `alembic/env.py`/`db/base.py` (ver achado geral do módulo `ia/`).
