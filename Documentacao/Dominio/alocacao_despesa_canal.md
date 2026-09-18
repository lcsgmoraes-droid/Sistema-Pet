---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — alocacao_despesa_canal

Ver [[dre_detalhe_canais]], [[Usuario]].

## Definição
Regra de rateio de despesa entre canais de venda (proporcional/manual).

## Confirmado no código
- Modelo: `ia/aba7_dre_detalhada_models.py:164-200` (`AlocacaoDespesaCanal`).
- Colunas: `modo_alocacao` (proporcional/manual).

## Relacionamentos
- FK de saída: `usuario_id → users.id` (correta).

## Utilizado por
- `aba7_dre_detalhada_service.py`.

## Não identificado
- Mesma lacuna de registro no Alembic do restante do submódulo `aba7_dre_detalhada`.
