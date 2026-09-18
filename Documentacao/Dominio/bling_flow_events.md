---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — bling_flow_events

Ver [[pedidos_integrados]], [[bling_flow_incidents]].

## Definição
Evento de auditoria do fluxo de sincronização Bling (pedido/NF), usado no monitor de saúde da integração.

## Confirmado no código
- Modelo: `bling_flow_monitor_models.py:8-33` (`BlingFlowEvent`).
- Colunas: `source`, `event_type`, `entity_type` (default "pedido"), `status` (default "ok"), `severity` (default "info"), `message`/`error_message`, `auto_fix_applied`, `payload` (JSON).
- ⚠️ FKs fantasmas: `pedido_integrado_id` (aponta conceitualmente para [[pedidos_integrados]], sem `ForeignKey()`), `pedido_bling_id`/`nf_bling_id`/`sku` (Strings soltas).

## Relacionamentos
- Sem FK real de saída nem entrada.

## Utilizado por
- Gravado em `services/bling_flow_monitor_incidents.py:97`.
- ⚠️ Achado estrutural: as rotas de leitura estão em `bling_flow_monitor_routes.py`, cujo próprio `APIRouter` **nunca é registrado** — mas não é código morto de verdade, já que `bling_routes.py` importa essas funções handler individualmente e as reexpõe sob seu próprio router registrado (`/bling/monitor/*`). Duplicação estrutural incomum, não uma rota inacessível.

## Não identificado
- Nada além do já citado.
