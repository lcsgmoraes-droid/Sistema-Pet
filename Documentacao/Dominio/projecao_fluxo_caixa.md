---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — projecao_fluxo_caixa

Ver [[fluxo_caixa]], [[Usuario]].

## Definição
Projeção de fluxo de caixa gerada pelo modelo preditivo (Prophet).

## Confirmado no código
- Modelo: `ia/aba5_models.py:132-160` (`ProjecaoFluxoCaixa`).
- Colunas: `valor_entrada_estimada`, `limite_inferior`/`superior`, `vai_faltar_caixa`.

## Relacionamentos
- FK de saída: `usuario_id → users.id`.

## Utilizado por
- `ia/aba5_fluxo_caixa_parts/projecoes.py`.

## Não identificado
- Não está listada em `alembic/env.py`/`db/base.py`.
