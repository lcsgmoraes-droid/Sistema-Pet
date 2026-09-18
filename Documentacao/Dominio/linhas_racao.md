---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — linhas_racao

Ver [[Produto]], [[portes_animal]].

## Definição
Cadastro dinâmico de linhas de ração (Premium, Super Premium etc.), por tenant — catálogo auxiliar/taxonomia, sem FK para produto.

## Confirmado no código
- Modelo: `opcoes_racao_models.py:17-35` (`LinhaRacao`). Colunas: `nome`, `descricao`, `ordem`, `ativo`.

## Relacionamentos
- Sem FK de saída nem de entrada — catálogo independente, usado como taxonomia/enum dinâmico.

## Utilizado por
- CRUD completo: `opcoes_racao_routes.py` (`/opcoes-racao/linhas`, registrado em `main_routers.py:288`).
- `analise_racoes_filters.py`, `analise_racoes_schemas.py`, `produtos/racao_routes.py`.

## Não identificado
- Nada notável — mesmo padrão das outras 5 tabelas irmãs de opções de ração.
