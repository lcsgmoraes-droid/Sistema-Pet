# Classificacao inteligente de racoes

Atualizado em: 2026-08-20

Este documento descreve apenas a implementacao atual. O material historico da
primeira versao permanece recuperavel pelo Git.

## Objetivo

A classificacao identifica, a partir do cadastro do produto, informacoes como
especie, porte, fase do animal, tratamento, sabor ou proteina e peso da
embalagem. O resultado ajuda o cadastro, os alertas e a calculadora de racoes.

## Fontes de codigo

| Responsabilidade | Fonte atual |
|---|---|
| Regras de classificacao | `backend/app/classificador_racao.py` |
| Rotas protegidas por empresa | `backend/app/produtos/racao_routes.py` |
| Normalizacao de produto | `backend/app/produtos/racao.py` |
| Cadastro e apresentacao | `frontend/src/components/ClassificacaoRacaoIA.jsx` |
| Pendencias e classificacao em lote | `frontend/src/components/AlertasRacao.jsx` |
| Calculadora | `backend/app/racao_calculadora/` e `frontend/src/pages/calculadora-racao/` |

## Operacoes principais

- `POST /api/produtos/{produto_id}/classificar-ia`: classifica um produto;
- `POST /api/produtos/classificar-lote`: classifica produtos elegiveis em lote;
- `GET /api/produtos/racao/alertas`: lista cadastros incompletos.

As rotas usam o usuario autenticado e o `tenant_id` da sessao. A consulta do
produto inclui o filtro da empresa antes de ler ou alterar dados.

## Regras de manutencao

- manter a separacao por empresa em qualquer consulta nova;
- preservar a opcao `auto_classificar_nome` e a reclassificacao explicita;
- atualizar este guia quando fontes ou endpoints mudarem;
- validar backend e frontend antes de publicar alteracoes;
- nao registrar chaves de IA, dados reais ou credenciais na documentacao.

## Limites

A classificacao e uma ajuda operacional baseada no nome e nos dados cadastrados.
Ela nao substitui a revisao do cadastro, a informacao do fabricante ou uma
orientacao veterinaria.
