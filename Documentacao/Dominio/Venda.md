---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Venda

Ver [[PDV-Vendas]], [[Cliente]], [[Produto]], [[Financeiro]].

## Confirmado no código
- Modelo: `backend/app/vendas_models.py` — `Venda`, `VendaItem`, `VendaPagamento`, `VendaBaixa`.
- `Venda`: `cliente_id` → `clientes.id`, `vendedor_id` → `users.id`, `funcionario_id`/`entregador_id` → `clientes.id` (reaproveitamento, ver [[Cliente]]), `caixa_id` → `caixas.id`.
- `VendaItem`: `venda_id` (CASCADE), `produto_id`, `lote_id` → `produto_lotes.id`, `pet_id` → `pets.id`, e um **`tenant_id` explícito adicional** (RESTRICT) — camada extra de proteção multi-tenant diretamente no item, além do isolamento padrão.
- `contas_receber` é relação `viewonly` a partir de `Venda` (uma venda a prazo gera contas a receber, ver [[ContaReceber]]).
- Há uma segunda entidade de pedido para o canal de e-commerce: `Pedido`/`PedidoItem` (`pedido_models.py`), modelada como **aggregate root DDD**, distinta de `Venda` do PDV — ⚠️ são dois modelos de "venda" paralelos conforme o canal (PDV vs. e-commerce), não um único conceito unificado.

## Utilizado por
- [[PDV-Vendas]] (fluxo principal de criação)
- [[Financeiro]] (baixa, contas a receber, comissões)
- [[Bling]], [[Stone]], [[Mercado-Pago]] (conciliação/sincronização de pagamento)
- [[Comissoes]] (cálculo sobre vendas)

## Não identificado
- ❓ Se há (ou há plano de) unificação futura entre `Venda` (PDV) e `Pedido` (e-commerce) num único conceito de "pedido", ou se a separação por canal é definitiva por motivo de modelagem DDD.
