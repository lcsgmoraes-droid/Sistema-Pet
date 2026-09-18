---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedidos_integrados

Ver [[pedidos]], [[pedidos_integrados_itens]], [[Bling]].

## Definição
Pedido importado via integração externa (Bling, que por sua vez agrega marketplaces) — "fonte da verdade para reserva de estoque" (docstring). ⚠️ **Conceito totalmente distinto de [[pedidos]]** apesar do nome parecido.

## Confirmado no código
- Modelo: `pedido_integrado_models.py:6-34` (`PedidoIntegrado`).
- Colunas: `pedido_bling_id`/`pedido_bling_numero`, `canal` (resolvido do payload do Bling via `_resolver_canal_pedido()`), `status` (aberto/confirmado/expirado/cancelado), `payload` (JSON bruto).
- Método `calcular_expiracao(dias=15)`.
- ✅ **Nenhuma FK ou relação de schema com [[pedidos]]** — são dois pipelines paralelos e independentes, resolvendo problemas de domínio diferentes.

## Relacionamentos
- Sem FK de saída.
- Referenciada por: [[pedidos_integrados_itens]]`.pedido_integrado_id`.

## Utilizado por
- Criado em `integracao_bling_pedido_webhook_processor.py:537-552` a partir do webhook do Bling.
- Deduplicação: `services/pedido_integrado_consolidation_service.py` (`_consolidar_pedido_duplicado_por_numero_loja`).

## Não identificado
- ⚠️ **Nunca vira [[Venda]]/[[ContaReceber]]** — diferente de [[pedidos]], serve exclusivamente para reserva/baixa de estoque e conciliação fiscal com o Bling. Vale destacar essa diferença para qualquer pessoa nova lendo o schema, já que os nomes ("pedidos" vs "pedidos_integrados") sugerem parentesco que não existe estruturalmente.
