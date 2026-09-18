---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — whatsapp_ia_metrics

Ver [[Tenant]].

## Definição
Métrica agregada do módulo de IA do WhatsApp (série temporal).

## Confirmado no código
- Modelo: `whatsapp/models.py:219-241` (`WhatsAppMetric`). `tenant_id → tenants.id` real.
- Colunas: `metric_type`, `value` (Float), `metric_metadata`, `timestamp`.

## Relacionamentos
- FK de saída: `tenant_id`.

## Utilizado por
- `whatsapp/analytics.py`/`analytics_simple.py`/`metrics.py`/`analytics_router.py` (registrado em `main_routers.py:623`).

## Não identificado
- Nada notável.
