---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — read_performance_parceiro

Ver [[read_vendas_resumo_diario]], [[Cliente]].

## Definição
Read model CQRS de performance mensal de um funcionário/parceiro de vendas.

## Confirmado no código
- Modelo: `read_models/models.py:96-162` (`PerformanceParceiro`).
- `funcionario_id` sem FK. `UniqueConstraint(tenant_id, funcionario_id, mes_referencia)`.

## Relacionamentos
- Sem FK real.

## Utilizado por
- Mesmo pipeline CQRS de [[read_vendas_resumo_diario]] — atualizado por handlers de evento de venda.

## Não identificado
- `funcionario_id` deveria ser FK real (para `clientes.id`, seguindo o padrão "parceiro = Cliente").
