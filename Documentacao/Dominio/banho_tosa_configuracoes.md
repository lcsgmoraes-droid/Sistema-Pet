---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_configuracoes

Ver [[Tenant]], [[dre_subcategorias]].

## Definição
Parâmetros de custo operacional do módulo (água, energia, toalha, taxas, rateio) usados no cálculo de margem por atendimento.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/cadastros.py:20-47` (`BanhoTosaConfiguracao`).
- ⚠️ FKs fantasmas: `dre_subcategoria_receita_id` e `dre_subcategoria_custo_id`, `Integer` sem `ForeignKey()`, presumivelmente apontando para [[dre_subcategorias]].

## Relacionamentos
- Sem FK de saída real.

## Utilizado por
- `obter_ou_criar_configuracao`, chamada em `agenda_routes.py:195`. Consumida pelos serviços `banho_tosa_custos*.py`.

## Não identificado
- FKs de DRE deveriam ser reais e não são.
