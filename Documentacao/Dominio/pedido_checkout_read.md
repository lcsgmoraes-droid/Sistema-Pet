---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedido_checkout_read

Ver [[pedidos]], [[read_vendas_resumo_diario]].

## Definição
🔴 **Read model CQRS órfão.** Projeção de checkout de pedido, definida mas nunca conectada a nenhum handler de evento real.

## Confirmado no código
- Modelo: `read_models/pedido_checkout_read.py:8-21` (`PedidoCheckoutRead`). `Base` puro (não `BaseTenantModel`); `tenant_id` é `String` solto (diferente do padrão UUID típico do resto do sistema).
- Projeção definida em `domain/events/read_model_projection.py`.

## Relacionamentos
- Sem FK.

## Utilizado por
- 🔴 **Nenhum uso real**: nenhum outro arquivo do backend importa o módulo de projeção nem a classe, fora dos dois arquivos citados — a projeção nunca é chamada por um handler de evento real.

## Não identificado
- Contraste direto com [[read_vendas_resumo_diario]] (mesmo padrão CQRS, mas plenamente ativo) — scaffolding não conectado, mesma categoria de achado de [[pedido_dashboard_read]].
