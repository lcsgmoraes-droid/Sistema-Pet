---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — conciliacao_metricas

Ver [[conciliacao_recebimentos]].

## Definição
Métrica diária de taxa de amarração automática entre recebimentos e vendas — KPI de saúde do módulo de conciliação de recebimento.

## Confirmado no código
- Modelo: `conciliacao_recebimento_models.py:156-282` (`ConciliacaoMetrica`).
- Colunas: `taxa_amarracao_automatica`, `alerta_saude` ('OK'/'CRÍTICO', threshold 90%), `recebimentos_orfaos`.

## Relacionamentos
- FK de saída: `criado_por_id → users.id` (NOT NULL, sem `ondelete`).
- Sem referências de entrada.

## Utilizado por
- `conciliacao_services_recebimentos.py`.

## Não identificado
- Nada notável.
