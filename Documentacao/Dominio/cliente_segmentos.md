---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — cliente_segmentos

Ver [[Cliente]].

## Definição
Segmentação de cliente (VIP/Ouro/Prata/Bronze/Inativo) com métricas RFM/LTV/ticket médio, usada em dashboards de análise de clientes.

## Confirmado no código
- Modelo: `segmentacao_models.py:16-68` (`ClienteSegmento`). Comentário no código indica origem em levantamento de "tabelas órfãs" (`RELATORIO_SCHEMA_TABELAS_ORFAS.md - Fase 5.4`).
- Colunas: `segmento` (VIP/Ouro/Prata/Bronze/Inativo), `metricas` (JSONB obrigatório), `tags` (JSONB opcional), `observacoes`.
- `__table_args__` inclui `extend_existing=True` — mas só há uma definição de classe Python, diferente do padrão de duplicação real achado no módulo fiscal; parece defensivo/histórico.

## Relacionamentos
- FKs de saída: `cliente_id → clientes.id`, `user_id → users.id`.
- Sem referências de entrada.

## Utilizado por
- 🟠 **Padrão "ORM só para leitura, escrita via SQL cru" confirmado**: leitura via ORM em `clientes/crud_routes.py:804-846` (dashboards `vip_em_risco`/`novos_promissores`), mas a escrita real é 100% SQL cru em `services/segmentacao_service.py:301-357` (`SELECT`/`UPDATE`/`INSERT` via `text()`), **nunca** via `ClienteSegmento(...)` do ORM. Exposto por `api/endpoints/segmentacao.py`.

## Não identificado
- 🟠 Risco de dessincronia: qualquer nova coluna/constraint adicionada só no model ORM (ou vice-versa) pode dessincronizar silenciosamente, já que o INSERT/UPDATE real não passa pelo mapeamento SQLAlchemy.
