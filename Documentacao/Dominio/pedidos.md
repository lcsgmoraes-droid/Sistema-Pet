---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedidos

Ver [[Venda]], [[pedido_itens]], [[Cliente]].

## Definição
Aggregate root do checkout de e-commerce (web/app) — "pedido nasce antes do evento" (docstring). Distinto de [[pedidos_integrados]] (pedido importado do Bling/marketplace — ver nota nesse arquivo).

## Confirmado no código
- Modelo: `pedido_models.py:21-27` (`Pedido`, `pedido_id` público String unique usado como FK-alvo, não a PK Integer).
- Colunas: `cliente_id` (⚠️ FK fantasma, sem `ForeignKey()`), `total` (recalculado por `recalcular_total()`, nunca setado manualmente), `origem`, `status` (default "criado", transita via webhook de pagamento), `payment_provider`/`payment_preference_id`/`payment_url` (Mercado Pago), `tipo_retirada`/`palavra_chave_retirada`, campos de frete/logística, `is_drive`/`drive_chegou_at`/`drive_entregue_at`, `reserva_estoque_iniciada_at`.
- Métodos de domínio DDD: `adicionar_item()`, `recalcular_total()`, validados via `PedidoPolicy`.
- ✅ **Confirma e aprofunda achado prévio de [[Venda]]**: `Pedido` e `Venda` não têm FK entre si — o vínculo é só texto livre (`Venda.observacoes = "Pedido ... {pedido_id}"`) e uma chave de idempotência (`ecommerce-venda:{pedido_id}` em `IdempotencyKey`). `_integrar_venda_ao_motor()` (`ecommerce_webhooks_sales.py:492-568`) cria a `Venda` via `VendaService.criar_venda(...)` a partir dos itens do pedido, e só então dispara `VendaPagamento`, DRE, `ContasReceberService.criar_de_venda` e contas a pagar de taxas de gateway — **fluxo correto Pedido → Venda → ContaReceber**, igual ao padrão de [[banho_tosa_atendimentos]] e diferente do achado do módulo veterinário.

## Relacionamentos
- Sem FK de saída real (`cliente_id` é fantasma).
- Referenciada por: [[pedido_itens]]`.pedido_id` (aponta pra coluna `pedido_id`, não `id`).

## Utilizado por
- `application/checkout_service.py` (`CheckoutService.processar_checkout`) — criação.
- `routes/ecommerce_webhooks_payment.py` (`_apply_payment_status_update`) — pós-pagamento.

## Não identificado
- `cliente_id` deveria ser FK real e não é.
