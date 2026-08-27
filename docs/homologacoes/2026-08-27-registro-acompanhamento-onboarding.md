# Homologacao - registro do acompanhamento de onboarding

Data: 2026-08-27

Ambiente: homologacao local isolada em Docker

## Objetivo

Comprovar a evolucao do banco, a compatibilidade das jornadas existentes e o
salvamento real de responsavel, desbloqueio e satisfacao pela interface.

## Resultado estrutural

- Alembic atualizado para `zxf20260827a1`.
- Quatro colunas `onboarding_*` presentes em `tenants`.
- Satisfacao `NOT NULL` com padrao `not_collected`.
- Restricao `ck_tenants_onboarding_satisfaction` presente.
- Frontend e backend construidos com os Dockerfiles de producao e saudaveis.

## Resultado funcional

- Login administrativo feito com usuario temporario exclusivo da homologacao.
- Aba `Pilotos` carregou com o novo painel lateral.
- Responsavel, data de desbloqueio e satisfacao foram salvos pela API real.
- Empresa ficticia mudou de `acompanhar` para `em dia`.
- Contador `Com proxima acao` mudou de 1 para 0.
- Ultima atualizacao apareceu no formulario.
- Usuario temporario e valores ficticios foram removidos depois da validacao.
- E2E do Plano Basico passou sem regressao.

## Testes focados

- Servico, API, migration, contratos da interface e SLO: 24 aprovados.
- Utilitarios da interface: 7 aprovados.
- Ruff, ESLint, Prettier e `git diff --check`: aprovados.
- Build de producao do frontend: aprovado.

## Limites

Os testes usam somente dados ficticios locais. Nenhum comando remoto ou de
producao foi executado.
