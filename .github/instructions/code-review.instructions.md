---
applyTo: "backend/**/*.py,frontend/src/**/*.{js,jsx,ts,tsx},app-mobile/**/*.{ts,tsx,js,jsx},scripts/**/*.{ps1,sh},docs/**/*.md"
---
# Regras de Revisao de Codigo

Objetivo: revisar com foco em risco real e regressao.

## Ordem de prioridade

1. Bugs e regressao de comportamento.
2. Seguranca e dados sensiveis.
3. Integridade de deploy/fluxo operacional.
4. Testes ausentes para mudancas relevantes.
5. Clareza e manutencao do codigo.

## O que verificar sempre

- A mudanca realmente resolve o problema descrito.
- Nao quebra fluxo existente em backend e frontend.
- Segue regras do fluxo unico DEV -> PROD do projeto.
- Mudancas de frontend que exigem build foram tratadas corretamente.
- Mensagem final explica risco residual e proximos passos.

## Como reportar achados

- Trazer primeiro os problemas por severidade (alto, medio, baixo).
- Incluir arquivo e linha quando possivel.
- Ser objetivo: problema, impacto e correcao sugerida.
- Se nao houver achados, declarar explicitamente "sem achados criticos" e listar risco residual.
