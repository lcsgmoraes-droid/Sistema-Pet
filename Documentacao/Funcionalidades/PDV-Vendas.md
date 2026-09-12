---
tipo: funcionalidade
atualizado: 2026-09-12
---

# PDV / Vendas

Ver [[Funcionalidades]], [[Venda]], [[Cliente]], [[Produto]].

## Identificação
- **Menu:** Vendas e relacionamento → PDV/Vendas
- **Rota frontend:** `/pdv`
- **Módulo de rota:** `frontend/src/app/routes/SalesMarketingRoutes.jsx`

## Objetivo
Registrar vendas presenciais (balcão), com busca de produto, aplicação de preço/desconto, múltiplas formas de pagamento e baixa de estoque — o núcleo transacional do sistema.

## Usuários
Perfil `Caixa` (PDV, consulta de produtos, cadastro/edição de clientes — sem excluir vendas/clientes/produtos) e superiores (`Gerente`, `Administrador`). Ver [[Role-Permission]].

## Fluxo (confirmado pela arquitetura geral do sistema)
```text
Operador (Caixa) → tela PDV → busca produto (frontend/src/api.js)
  → vendas_routes.py → vendas/ (criação, finalização) → VendaService
  → grava Venda + VendaItem (tenant_id explícito no item)
  → baixa de estoque (EstoqueMovimentacao)
  → registra VendaPagamento (múltiplas formas)
  → gera ContaReceber se a prazo
```

## Backend (confirmado)
- Rotas: `vendas_routes.py`, submódulos em `vendas/` (criação, finalização, cancelamento, devoluções, pagamentos).
- Caixa: `caixa_routes.py`, `caixa/` (abertura/fechamento).
- Testes de risco crítico já mapeados pelo próprio projeto (`docs/auditorias/testes-ci-cobertura-critica.md`): `backend/tests/domain/test_venda_service.py`, `test_venda_finalizacao_pagamentos.py`, `test_vendas_regras_helpers.py`.

## Banco de dados
`Venda`, `VendaItem` (proteção extra de `tenant_id` explícito), `VendaPagamento`, `VendaBaixa` — ver [[Venda]].

## Integrações
[[Stone]] (conciliação de cartão pós-venda), [[Mercado-Pago]] (se venda originada de e-commerce), [[Bling]] (emissão fiscal via Bling hoje, ver [[Fiscal-IntNFe-SEFAZ]]).

## Segurança
Protegido por [[Autenticacao]] + [[Autorizacao]] padrão do sistema; isolamento de tenant reforçado por coluna `tenant_id` explícita em `VendaItem` além do padrão automático.

## Dependências
[[Produto]] (estoque), [[Cliente]] (comprador), [[ContaReceber]] (venda a prazo), [[Comissoes]] (cálculo pós-venda).

## Pontos de atenção
- Existe um segundo modelo de "venda" para e-commerce (`Pedido`/`PedidoItem`, DDD aggregate) — ver [[Venda#Não identificado]]. Vendas presenciais e vendas online não compartilham a mesma tabela.

## Não identificado
- ⚠️ Detalhe de payload de request/response dos endpoints de `vendas/` não foi extraído linha a linha nesta rodada — este documento descreve o fluxo confirmado pela arquitetura, não o contrato completo de API. Ver [[API]] quando aprofundado.
