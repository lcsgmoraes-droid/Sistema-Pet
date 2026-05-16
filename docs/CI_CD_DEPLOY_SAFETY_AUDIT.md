# Auditoria de CI/CD e deploy seguro

Atualizado em: 2026-05-16

Este arquivo acompanha a maturidade de CI/CD e deploy seguro do Sistema Pet.

## Nota atual

Nota inicial estimada: 7/10.

Nota atual estimada: 10/10.

Meta: 10/10 antes de automatizar qualquer deploy de producao.

## Feito

| Status | Item | Referencia |
|---|---|---|
| Feito | Branch protection da `main` ja exige `MCP tests` | GitHub branch protection |
| Feito | CI dos MCPs roda em todo PR | `.github/workflows/mcp-ci.yml` |
| Feito | Backend CI passa a rodar em todo PR para `main` e `develop` | `.github/workflows/backend-ci.yml` |
| Feito | Check de deploy safety roda em todo PR para `main` | `.github/workflows/deploy-safety.yml` |
| Feito | Branch protection da `main` exige `MCP tests`, `Fluxo unico safety`, `Quality Gate` e `Smoke test` | GitHub branch protection |
| Feito | Smoke CI valida backend, auth basico e build frontend | `.github/workflows/smoke-ci.yml` |
| Feito | Validador local bloqueia multiplas heads Alembic, artefatos e arquivos proibidos | `scripts/validar_fluxo.ps1` |
| Feito | Rollback operacional simples documentado | `docs/PRODUCAO_ROLLBACK_CHECKLIST.md` |
| Feito | Checklist de deploy com backup, health e rollback criado | `docs/PRODUCAO_ROLLBACK_CHECKLIST.md` |

## PRs ja juntados

| PR | Conteudo | Status |
|---|---|---|
| #55 | Deploy Safety em PRs, Backend CI em todo PR e guia CI/CD | Mergeado |
| #57 | Smoke CI com backend, auth basico e build frontend | Mergeado |
| #58 | `Smoke test` obrigatorio na branch protection | Mergeado |

## Checks que devem proteger a `main`

| Check | Motivo |
|---|---|
| `MCP tests` | Garante maturidade e funcionamento dos MCPs locais |
| `Fluxo unico safety` | Garante trilho basico DEV -> PROD antes do merge |
| `Quality Gate` | Garante suite backend multitenant e import smoke |
| `Smoke test` | Garante smoke de backend/auth e build de frontend |

## O que falta para manter 10/10

| Prioridade | Status | Item | Motivo |
|---|---|---|---|
| Media | Continuo | Revisar este guia apos o proximo deploy real | Ajusta o procedimento com evidencia operacional |
| Media | Continuo | Manter checks obrigatorios verdes em todo PR | Evita regressao do trilho seguro |
| Baixa | Continuo | Registrar incidentes e rollbacks quando ocorrerem | Mantem historico auditavel |

## Proximo passo recomendado

1. Usar `docs/PRODUCAO_ROLLBACK_CHECKLIST.md` no proximo deploy real autorizado.
2. Revisar o checklist com base no resultado real do deploy.
