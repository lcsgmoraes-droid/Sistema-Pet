---
applyTo: "backend/**/*.py,frontend/src/**/*.{js,jsx,ts,tsx},scripts/**/*.{ps1,sh},docker-compose*.yml,.github/**/*.yml"
---
# Regras de Seguranca

Objetivo: evitar vazamento de dados e mudancas arriscadas.

## Segredos e credenciais

- Nunca colocar senha, token, chave API ou URL sensivel em codigo versionado.
- Usar variaveis de ambiente para dados sensiveis.
- Evitar logar dados sensiveis em texto puro.

## Operacoes destrutivas

- Pedir confirmacao antes de comandos destrutivos (drop, truncate, delete em lote, reset).
- Preferir modo seguro: backup, simulacao ou validacao previa.

## API e backend

- Validar entrada sempre (tipos, limites e campos obrigatorios).
- Tratar erros sem expor stack trace para usuario final.
- Garantir autorizacao antes de operacoes sensiveis.

## Infra e deploy

- Nao pular passos de release-check e validacao definidos no projeto.
- Nao executar deploy em producao sem autorizacao explicita do Lucas.
