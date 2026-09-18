---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — read_receita_mensal

Ver [[read_vendas_resumo_diario]].

## Definição
Read model CQRS de receita mensal agregada.

## Confirmado no código
- Modelo: `read_models/models.py:180-237` (`ReceitaMensal`).
- `UniqueConstraint(tenant_id, mes_referencia)`. Sem FK.

## Relacionamentos
- Sem FK.

## Utilizado por
- Mesmo pipeline CQRS de [[read_vendas_resumo_diario]].

## Não identificado
- Nada notável.
