---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — bling_notas_fiscais_cache

Ver [[Bling]].

## Definição
Cache local de NF-e sincronizadas via Bling — tabela mais usada do módulo fiscal, espelho da API do Bling com dados de canal de venda.

## Confirmado no código
- Modelo: `nfe_cache_models.py:16-71` (`BlingNotaFiscalCache`).
- `UniqueConstraint(tenant_id, bling_id, modelo)`, 2 índices compostos para busca por pedido/loja.
- Colunas: `bling_id`, `modelo` (55=NFe padrão), `tipo` ("nfe"), `numero`, `serie`, `status`, `chave` (chave de acesso), `data_emissao`, `valor`; JSON de payload (`cliente`, `loja`, `unidade_negocio`, `resumo_payload`, `detalhe_payload`); campos de canal (`canal`, `canal_label`, `numero_loja_virtual`, `origem_loja_virtual`, `origem_canal_venda`, `numero_pedido_loja`, `pedido_bling_id_ref` — referência textual ao pedido Bling, sem FK); `source` (default "bling_api"), `last_synced_at`.

## Relacionamentos
- Sem FK de saída declarada (referências a pedido/produto são por string/JSON — é um cache de espelho da API externa, não uma entidade relacional própria).
- Sem FK de entrada.

## Utilizado por
- `services/nfe_cache_service.py` (upsert), `services/bling_nf_service.py`, reconciliação (`services/nfe_authorized_reconciliation_service.py`, `nfe_pending_reconciliation_service.py`), monitor de fluxo (`services/bling_flow_monitor_autofix.py`, `bling_flow_monitor_routes.py`), rotas de NF-e (`nfe/documentos.py`, `nfe/operacional_routes.py`, `nfe/listagem_rapida.py`), contexto de movimentação de estoque (`estoque_movimentacoes_context.py`).

## Não identificado
- Nada notável — tabela bem integrada e ativamente mantida, ao contrário das duas de rateio por canal ([[nota_fiscal_rateio_canal]], [[nota_fiscal_item_rateio_canal]]) que tentam resolver problema parecido (canal por NF) mas nunca foram plugadas.
