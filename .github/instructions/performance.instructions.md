---
applyTo: "backend/**/*.py,frontend/src/**/*.{js,jsx,ts,tsx},app-mobile/**/*.{ts,tsx,js,jsx},docker-compose*.yml"
---
# Regras de Performance

Objetivo: manter sistema rapido sem perder simplicidade.

## Regras gerais

- Priorizar ganhos de alto impacto e baixo risco.
- Medir antes e depois quando possivel (tempo de resposta, uso de CPU/memoria, tamanho de bundle).
- Evitar otimizacoes prematuras sem evidencia.

## Backend

- Evitar N+1 queries e consultas sem indice.
- Paginar listas grandes.
- Selecionar apenas campos necessarios.
- Colocar timeout e tratamento de falha em integracoes externas.

## Frontend/App

- Evitar renderizacoes desnecessarias.
- Carregar dados sob demanda quando a tela for pesada.
- Reduzir trabalho em tempo de digitacao (debounce/throttle quando necessario).
- Evitar bibliotecas grandes sem justificativa clara.

## Entrega

Ao propor otimizar, sempre informar:

1. Gargalo identificado.
2. Solucao aplicada.
3. Impacto esperado ou medido.
