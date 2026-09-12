---
tipo: funcionalidade
atualizado: 2026-09-12
---

# Produtos / Estoque

Ver [[Funcionalidades]], [[Produto]], [[Bling]].

## Identificação
- **Menu:** Estoque e suprimentos → Produtos/Estoque
- **Rota frontend:** `/produtos`, `/estoque` (submenu: Listar, Relatório de Movimentações, Valorização, Balanço, Alertas, Movimentação Full por NF, Transferência Parceiro, Sinc. Bling)
- **Módulo de rota:** `frontend/src/app/routes/ProductInventoryRoutes.jsx`

## Objetivo
Cadastro de produtos (catálogo, categorias, marcas), controle de estoque (movimentações, lotes/validade, fracionamento, granel), precificação e sincronização com o Catálogo Mestre global e com o Bling.

## Usuários
Perfil `Estoque e Compras` (produtos, entrada de XML, pedidos de compra — sem excluir produtos) e superiores.

## Backend (confirmado)
`produtos_routes.py` + pasta `produtos/` (cadastro, lotes, SKU, imagens, relatórios); ~15 routers `estoque_*` (movimentações, granel, fracionamento, transferência, validade, alertas de negativo); `variacoes_routes.py`; worker dedicado do Catálogo Mestre (`backend/scripts/run_catalogo_mestre_worker.py`).

## Banco de dados
`Produto`, `Categoria`, `Marca`, `Departamento`, `EstoqueMovimentacao`, `ProdutoLote`, `ProdutoImagem` — ver [[Produto]] e [[Banco-de-Dados]].

## Integrações
[[Bling]] (sincronização de estoque/pedidos), [[Fiscal-IntNFe-SEFAZ]] (nota de entrada via XML).

## Segurança
Upload de imagem de produto bem protegido (ver [[API-Security]]); upload de XML de nota de entrada **sem limite de tamanho confirmado** — ver [[Vulnerabilidades]] item 4.

## Dependências
[[PDV-Vendas]] (consome estoque), [[Compras]] (reabastece estoque).

## Pontos de atenção
- Existe um Catálogo Mestre global compartilhado entre tenants além do catálogo próprio de cada empresa — a governança exata dessa relação não foi auditada a fundo (ver [[Produto#Não identificado]]).
- Estoque negativo tem proteção por validade (job semanal, flag `ESTOQUE_VALIDADE_SCHEDULER_ENABLED`) — ver [[Arquitetura]].

## Não identificado
- ⚠️ Contrato detalhado (payload) dos principais endpoints de produto/estoque não foi extraído nesta rodada.
