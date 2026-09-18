---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — apresentacoes_peso

Ver [[linhas_racao]].

## Definição
Apresentação/peso de embalagem (1kg, 3kg, 10.1kg, 15kg, 20kg) — catálogo auxiliar para classificação de ração.

## Confirmado no código
- Modelo: `opcoes_racao_models.py:122-140` (`ApresentacaoPeso`).
- Diferente das demais tabelas irmãs: usa `peso_kg` (Float, indexado, obrigatório) em vez de `nome`, além de `descricao`/`ordem`/`ativo`.

## Relacionamentos
- Sem FK.

## Utilizado por
- CRUD via `opcoes_racao_routes.py`, `racoes_sugestoes_padronizacao_routes.py`, `racoes_sugestoes_duplicatas_routes.py`, `produtos/atualizacao_lote_routes.py`, `analise_racoes_routes_parts/filtros_routes.py`.

## Não identificado
- Nada notável.
