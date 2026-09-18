---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — entrega_avaliacoes

Ver [[Venda]], [[Cliente]].

## Definição
Avaliação (nota 1-5 + comentário) de uma entrega, uma por venda.

## Confirmado no código
- Modelo: `rotas_entrega_models.py:175-192` (`EntregaAvaliacao`).
- `UniqueConstraint(tenant_id, venda_id)` — uma avaliação por venda. `CheckConstraint(nota >= 1 AND nota <= 5)` no próprio banco.

## Relacionamentos
- FKs de saída: `venda_id → vendas.id`, `cliente_id → clientes.id`, `user_id → users.id` (relationships unidirecionais, sem `back_populates`).
- Sem referências de entrada.

## Utilizado por
- Escrita: `POST /vendas/{venda_id}/avaliacao-entrega` (checkout e-commerce), exige `venda.tem_entrega` e `status_entrega == "entregue"`.
- Leitura: `rotas_entrega_core_routes.py` (listagem de rotas), `services/customer_order_history.py` (histórico de pedidos do cliente).

## Não identificado
- Nada notável — bom exemplo de constraint de integridade (CHECK de nota) aplicado no próprio banco.
