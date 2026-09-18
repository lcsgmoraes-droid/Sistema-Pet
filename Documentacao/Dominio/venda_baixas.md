---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — venda_baixas

Ver [[Venda]], [[ContaReceber]].

## Definição
Registro de baixa (total ou parcial) de uma [[Venda]] — historicamente o mecanismo de marcar quanto de uma venda a prazo já foi pago.

## Confirmado no código
- Modelo: `vendas_models.py:688-748` (`VendaBaixa`).
- Colunas: `venda_id`, `valor_baixa`/`valor_anterior`/`valor_restante` (snapshot de saldo), `tipo` (baixa_total/baixa_parcial), `usuario_id`, campos de auditoria de edição/exclusão (`editado`, `editado_por`, `excluido`, `excluido_por`). Sem `updated_at`.

## Relacionamentos
- FKs de saída: `vendas.id` (CASCADE), `users.id` (×3: `usuario_id`, `editado_por`, `excluido_por`).
- Sem referências de entrada. `Venda.baixas` é relationship 1:N cascade delete-orphan.

## Utilizado por
- Leitura: `routes/ecommerce_entregador.py:691,707-709` (usa `venda.baixas` para achar forma de pagamento mais recente).
- ⚠️ **Escrita não confirmada em código de aplicação**: nenhum ponto em `app/` faz `VendaBaixa(...)` via ORM. Os únicos INSERTs encontrados são SQL raw em scripts de seed (`scripts/seed_demo_operacional_sales_finance.py:465`).

## Não identificado
- ❓ **Possível tabela obsoleta do ponto de vista de escrita**: o fluxo real de baixa de venda a prazo hoje parece passar por [[ContaReceber]] (`Venda.contas_receber` é `viewonly`) e por `VendaPagamento` (criado em `financeiro_baixa_lote_routes.py`), não por `VendaBaixa`. Recomenda-se confirmar com o time se este fluxo foi substituído e se a tabela pode ser descontinuada.
