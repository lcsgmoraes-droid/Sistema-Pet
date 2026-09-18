---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — read_vendas_resumo_diario

Ver [[Venda]], [[read_performance_parceiro]], [[read_receita_mensal]].

## Definição
Read model CQRS de resumo diário de vendas — só leitura do ponto de vista de domínio, atualizado por handlers de evento. ✅ Padrão CQRS plenamente ativo (diferente de [[pedido_checkout_read]]/[[pedido_dashboard_read]], que são scaffolding não conectado).

## Confirmado no código
- Modelo: `read_models/models.py:36-78` (`VendasResumoDiario`).
- `UniqueConstraint(tenant_id, data)`. Métodos `calcular_ticket_medio`/`to_dict`.

## Relacionamentos
- Sem FK (agregado, não entidade relacional).

## Utilizado por
- Exposta via `app.analytics.api` router (`main_routers.py:514`, tag "Analytics - CQRS Read Models").
- Atualizada por `read_models/handlers_v53_idempotente.py::VendaReadModelHandler` (a partir de eventos `VendaCriada`/`VendaFinalizada`/`VendaCancelada`).

## Não identificado
- Nada notável — bom exemplo de CQRS funcionando de ponta a ponta.
