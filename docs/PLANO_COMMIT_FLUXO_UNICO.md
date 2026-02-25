# Plano simples de commits (ordem recomendada)

Este plano evita confusao e deixa o historico limpo.

## Commit 1 - Higiene do repositorio

Objetivo: parar de versionar backups e arquivos locais.

Mensagem sugerida:
- chore(repo): remover backups do git e reforcar regras de ignorar arquivos locais

## Commit 2 - Fluxo unico operacional

Objetivo: padronizar o passo a passo DEV -> PROD.

Arquivos deste bloco:
- .github/assistant-rules.json
- .github/copilot-instructions.md
- .vscode/tasks.json
- FLUXO_UNICO.bat
- scripts/fluxo_unico.ps1
- scripts/validar_fluxo.ps1
- docs/FLUXO_UNICO_DEV_PROD.md
- README.md
- .gitignore

Mensagem sugerida:
- chore(flow): padronizar fluxo unico dev-prod com validacoes e tarefas vscode

## Commit 3 - Merge de migrations

Objetivo: unificar linha de evolucao do banco e remover bloqueio de heads duplicadas.

Arquivo deste bloco:
- backend/alembic/versions/f6c9a1b2d3e4_merge_heads_a8f3_e1a2.py

Mensagem sugerida:
- fix(migrations): unificar heads alembic em uma unica linha

## Regra final

Antes de subir producao, rodar sempre:
1) FLUXO_UNICO.bat check
2) FLUXO_UNICO.bat release-check
3) FLUXO_UNICO.bat prod-up
4) FLUXO_UNICO.bat status
