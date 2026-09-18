---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedidos_compra

Ver [[pedidos_compra_itens]], [[pedidos_compra_notas_entrada]], [[notas_entrada]], [[Cliente]].

## Definição
Pedido de compra a um fornecedor, com fluxo completo (rascunho → enviado → confirmado → recebido) e confronto opcional contra a NF-e recebida.

## Confirmado no código
- Modelo: `produtos_compras_models.py:28-88` (`PedidoCompra`).
- Colunas: `numero_pedido` (único), `status` (rascunho/enviado/confirmado/recebido_parcial/recebido_total/cancelado), valores (`valor_total`/`frete`/`desconto`/`final`), campos de IA (`sugestao_ia`, `confianca_ia`, `dados_ia`), campos de confronto com NF-e (`nota_entrada_id`, `status_confronto`, `resumo_confronto`, `confronto_finalizado`).
- ⚠️ FK fantasma: `fornecedor_id` é `Integer` sem `ForeignKey()`, resolvido em runtime contra [[Cliente]] (mesmo padrão do módulo financeiro).
- ⚠️ **Dupla fonte de verdade pedido↔nota**: o campo direto `nota_entrada_id` (usado só no fluxo de "confronto") coexiste com a tabela de junção N:N [[pedidos_compra_notas_entrada]] (via "oficial", com `UniqueConstraint`). O código precisa checar os dois lugares (`_pedido_principal_da_nota` em `compras_pendencias_notas.py:97-113`), priorizando o vínculo N:N e caindo para o campo direto como fallback.

## Relacionamentos
- FKs de saída: `nota_entrada_id → notas_entrada.id` (nullable), `user_id → users.id`.
- Referenciada por: [[pedidos_compra_notas_entrada]]`.pedido_compra_id`, [[pedidos_compra_itens]]`.pedido_compra_id`, [[compras_pendencias_fornecedor]]`.pedido_compra_id`.

## Utilizado por
- `pedidos_compra/core_routes.py` (criação/edição), `pedidos_compra/recebimento_routes.py:191-198` (atualiza status no recebimento), `pedidos_compra/confronto_routes.py`/`confronto_calculo.py` (confronto com NF).

## Não identificado
- 🟠 A dupla fonte de verdade pedido↔nota é achado a levar ao time — recomenda-se avaliar deprecar `nota_entrada_id` em favor exclusivo da tabela de junção.
