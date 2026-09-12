---
tipo: integracao
atualizado: 2026-09-12
---

# Integração — iFood

Parte de [[Integracoes]]. Fontes pré-existentes validadas: `docs/INTEGRACAO_IFOOD_FASE1.md` (catálogo), `docs/INTEGRACAO_IFOOD_FASE2_PEDIDOS.md` (pedidos).

## Identificação
- **Finalidade:** sincronização de catálogo e operação de pedidos do delivery iFood.
- **Estado confirmado:** envio real de pedidos ainda bloqueado até homologação do app CorePet junto ao iFood (documentado e coerente com as flags de ativação abaixo).

## Arquivos
`integrations/ifood/client.py`, `orders.py`, `poller.py`; `ifood_integration_models.py`, `ifood_order_models.py`; rotas `routes/ifood_integration_routes.py`, `routes/ifood_order_routes.py`.

## Comunicação
REST + OAuth2 `client_credentials` + **polling de pedidos** (não usa webhook do iFood).

## Autenticação
`IFOOD_CLIENT_ID`/`IFOOD_CLIENT_SECRET`, `IFOOD_API_BASE_URL`, `IFOOD_REQUEST_TIMEOUT_SECONDS`; flags `IFOOD_CATALOG_WRITE_ENABLED`, `IFOOD_ORDER_OPERATIONS_ENABLED`, `IFOOD_ORDER_POLLING_ENABLED`.

## Webhook
Não há — modelo é **polling ativo** (job in-process a cada 30s, ver [[Arquitetura]]). Eventos são persistidos antes do ACK, com unicidade por tenant/ID.

## Falhas, retry e resiliência
- Timeout configurável (padrão 15s), trata HTTP 429.
- 🟡 **Sem política central de retry exponencial** por chamada (lacuna já documentada no catálogo pré-existente).

## Fluxo
```text
Job in-process (30s) → poll pedidos iFood → persiste evento
  → processa pedido no CorePet (estoque, PDV)
  → (quando IFOOD_ORDER_OPERATIONS_ENABLED) confirma/atualiza status de volta ao iFood
```

## Dependências de funcionalidade
[[PDV-Vendas]], [[Produtos-Estoque]] (catálogo sincronizado).

## Não identificado
- ❓ Data/critério prevista para liberar envio real de pedidos (depende de homologação externa pelo iFood, fora do controle do código).
