# Extrato e Faturamento Veterinario MVP Design

## Objetivo

Criar o primeiro extrato financeiro operacional do atendimento veterinario, reunindo consulta e internacao para mostrar o que foi efetivamente utilizado, quanto custou, qual preco de venda sugerido e como isso deve ser agrupado no lancamento comercial.

## Escopo do MVP

- O extrato usa apenas itens ja executados: procedimentos da consulta, lancamentos rapidos de insumo e procedimentos/insumos registrados na internacao.
- Orcamentos continuam sem baixa de estoque e nao entram como custo realizado.
- Cada linha tem agrupador `consulta` ou `internacao`, origem, produto quando existir, quantidade, custo, preco de venda, margem e referencia operacional.
- Procedimentos com valor cobrado contam como linha principal do total. Seus insumos aparecem como detalhe, com custo/preco visiveis, mas sem duplicar o total do procedimento.
- Procedimentos ou lancamentos de insumo sem valor cobrado contam pelos produtos usados, usando o preco de venda atual do cadastro do produto.
- O endpoint aceita selecao de colunas e gera JSON, Excel e PDF.

## Arquitetura

- Backend:
  - `backend/app/veterinario_extratos.py` concentra calculos, colunas e geracao de documentos.
  - `backend/app/veterinario_extratos_routes.py` carrega consulta/internacao do tenant, monta o extrato e expoe JSON/PDF/XLSX.
  - `backend/app/veterinario_routes.py` registra o novo router.
- Frontend:
  - `frontend/src/pages/veterinario/extratos/ExtratoAtendimentoPanel.jsx` mostra resumo, colunas e acoes de exportacao.
  - `frontend/src/pages/veterinario/extratos/extratoUtils.js` centraliza colunas, filtros e nome de arquivo.
  - O painel entra na tela da consulta e no detalhe da internacao, abaixo do orcamento.

## Fluxo de Dados

1. A UI chama `/vet/extratos/atendimento` com `consulta_id` ou `internacao_id`.
2. O backend busca procedimentos realizados e evolucoes de internacao que representam procedimentos executados.
3. Produtos vinculados aos insumos sao carregados para obter codigo, unidade e preco de venda atual.
4. O helper cria linhas contabilizaveis e linhas de detalhe, calcula totais e devolve as colunas disponiveis.
5. PDF/XLSX usam o mesmo payload e respeitam a lista de colunas selecionada.

## Fora do Escopo Desta Etapa

- Criar a venda/conta a receber automaticamente a partir do extrato.
- Persistir extratos emitidos como documentos fiscais/comerciais.
- Definir diaria padrao de internacao por configuracao global.

## Criterios de Aceite

- Consulta com procedimento valorizado mostra total pelo valor do procedimento e detalha insumos sem duplicar.
- Lancamento manual de insumo com valor zero sugere cobranca pelo preco de venda do produto.
- Internacao mostra procedimentos executados e insumos usados no periodo.
- PDF e Excel respeitam a selecao de colunas.
- Testes unitarios cobrem colunas, totais e contrato das rotas.
