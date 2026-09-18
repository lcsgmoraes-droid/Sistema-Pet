---
tipo: funcionalidade
atualizado: 2026-09-12
---

# Comissões

Ver [[Funcionalidades]], [[Venda]], [[Financeiro]].

## Identificação

- **Menu:** Financeiro → Comissões (submenu: Configuração, Demonstrativo, Abertas, Fechamentos, Relatórios)
- **Rota frontend:** `/comissoes`
- **Módulo de rota:** `frontend/src/app/routes/CommissionRoutes.jsx`

## Objetivo

Cálculo, fechamento e demonstrativo de comissão de vendedores/funcionários sobre vendas realizadas.

## Backend (confirmado)

`comissoes_routes.py`, `comissoes_demonstrativo_routes.py`, `comissoes_avancadas_routes.py`, `comissoes_diagnostico_routes.py`, `routers/relatorios_comissoes.py`, `routes/acertos_routes.py`. Modelos: `comissoes_models.py`, `comissoes_avancadas_models.py`.

## Dependências

[[Venda]] (base de cálculo), [[Usuario]] (vendedor), [[Financeiro]] (categorias financeiras, fechamento).

## Não identificado

- ❓ Regras exatas de percentual/faixa de comissão (parametrização por produto/categoria/vendedor) não foram extraídas a fundo nesta rodada — apenas a existência dos módulos foi confirmada.
