# Auditoria de CI/CD e deploy seguro

Atualizado em: 2026-05-16

Este arquivo acompanha a maturidade de CI/CD e deploy seguro do Sistema Pet.

## Nota atual

Nota inicial estimada: 7/10.

Nota atual estimada: 9,5/10.

Meta: 10/10 antes de automatizar qualquer deploy de producao.

## Feito

| Status | Item | Referencia |
|---|---|---|
| Feito | Branch protection da `main` ja exige `MCP tests` | GitHub branch protection |
| Feito | CI dos MCPs roda em todo PR | `.github/workflows/mcp-ci.yml` |
| Feito | Backend CI passa a rodar em todo PR para `main` e `develop` | `.github/workflows/backend-ci.yml` |
| Feito | Check de deploy safety roda em todo PR para `main` | `.github/workflows/deploy-safety.yml` |
| Feito | Branch protection da `main` exige `MCP tests`, `Fluxo unico safety` e `Quality Gate` | GitHub branch protection |
| Feito | Smoke CI valida backend, auth basico e build frontend | `.github/workflows/smoke-ci.yml` |
| Feito | Validador local bloqueia multiplas heads Alembic, artefatos e arquivos proibidos | `scripts/validar_fluxo.ps1` |

## PRs ja juntados

| PR | Conteudo | Status |
|---|---|---|
| #55 | Deploy Safety em PRs, Backend CI em todo PR e guia CI/CD | Mergeado |

## Checks que devem proteger a `main`

| Check | Motivo |
|---|---|
| `MCP tests` | Garante maturidade e funcionamento dos MCPs locais |
| `Fluxo unico safety` | Garante trilho basico DEV -> PROD antes do merge |
| `Quality Gate` | Garante suite backend multitenant e import smoke |
| `Smoke test` | Garante smoke de backend/auth e build de frontend |

## O que falta para 10/10

| Prioridade | Status | Item | Motivo |
|---|---|---|---|
| Alta | Pendente | Exigir `Smoke test` na branch protection depois do primeiro PR verde | Impede merge sem smoke backend/auth/frontend |
| Media | Pendente | Documentar rollback operacional simples | Reduz risco em incidente de producao |
| Media | Pendente | Criar checklist de deploy com backup, health e rollback | Evita passos manuais esquecidos |

## Proximo passo recomendado

1. Mergear o PR do `Smoke CI`.
2. Exigir o check `Smoke test` na branch protection.
3. Documentar rollback operacional simples.
4. Criar checklist de deploy com backup, health e rollback.
