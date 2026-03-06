---
applyTo: "backend/**/*.py,frontend/src/**/*.{js,jsx,ts,tsx},app-mobile/**/*.{ts,tsx,js,jsx}"
---
# Regras de Testes

Objetivo: sempre entregar mudancas com validacao pratica e simples.

## Antes de finalizar qualquer mudanca

- Rodar testes relevantes para o arquivo alterado.
- Se nao houver teste automatizado, validar manualmente e descrever o passo a passo.
- Nunca afirmar "funciona" sem evidencias (comando executado ou passo manual reproduzivel).

## Backend (Python)

- Priorizar testes de regra de negocio, validacao e erros esperados.
- Cobrir caso feliz, caso de erro e caso de borda.
- Quando corrigir bug, adicionar teste que falhava antes da correcao.

## Frontend/App

- Validar estados principais: carregando, sucesso, vazio e erro.
- Confirmar formatacao brasileira de moeda e numero quando houver valor monetario.
- Evitar regressao visual basica em telas alteradas.

## Entrega

Sempre informar de forma objetiva:

1. O que foi testado.
2. Como foi testado (comando ou fluxo manual).
3. O que faltou testar (se houver).
