---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedido_dashboard_read

Ver [[pedido_checkout_read]].

## Definição
🔴 **Read model CQRS órfão.** Tabela agregada única (sem tenant/dimensão temporal — parece um singleton global de totais), com projeção nunca disparada.

## Confirmado no código
- Modelo: `domain/read_models/pedido_dashboard_read.py:6-16` (`PedidoDashboardRead`).
- Projeção em `domain/projections/pedido_dashboard_projection.py`.

## Relacionamentos
- Sem FK.

## Utilizado por
- 🔴 Nenhum uso real — nenhum módulo importa a projeção; não há handler de evento nem rota que a dispare.

## Não identificado
- Mesma categoria de achado de [[pedido_checkout_read]] — scaffolding CQRS abandonado.
