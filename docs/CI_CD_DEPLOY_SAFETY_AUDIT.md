# Auditoria de CI/CD e deploy seguro

Atualizado em: 2026-05-16

Este arquivo acompanha a maturidade de CI/CD e deploy seguro do Sistema Pet.

## Nota atual

Nota inicial estimada: 7/10.

Nota atual estimada: 8,5/10.

Meta: 10/10 antes de automatizar qualquer deploy de producao.

## Feito

| Status | Item | Referencia |
|---|---|---|
| Feito | Branch protection da `main` ja exige `MCP tests` | GitHub branch protection |
| Feito | CI dos MCPs roda em todo PR | `.github/workflows/mcp-ci.yml` |
| Feito | Backend CI passa a rodar em todo PR para `main` e `develop` | `.github/workflows/backend-ci.yml` |
| Feito | Check de deploy safety roda em todo PR para `main` | `.github/workflows/deploy-safety.yml` |
| Feito | Validador local bloqueia multiplas heads Alembic, artefatos e arquivos proibidos | `scripts/validar_fluxo.ps1` |

## Checks que devem proteger a `main`

| Check | Motivo |
|---|---|
| `MCP tests` | Garante maturidade e funcionamento dos MCPs locais |
| `Fluxo unico safety` | Garante trilho basico DEV -> PROD antes do merge |
| `Quality Gate` | Garante suite backend multitenant e import smoke |

## O que falta para 10/10

| Prioridade | Status | Item | Motivo |
|---|---|---|---|
| Alta | Pendente | Exigir `Fluxo unico safety` e `Quality Gate` na branch protection | Impede merge sem checks de deploy/backend |
| Alta | Pendente | Criar smoke test pos-merge para backend, auth e frontend build | Garante que a `main` continua executavel |
| Media | Pendente | Documentar rollback operacional simples | Reduz risco em incidente de producao |
| Media | Pendente | Criar checklist de deploy com backup, health e rollback | Evita passos manuais esquecidos |

## Proximo passo recomendado

1. Mergear o PR deste ajuste.
2. Atualizar branch protection da `main` para exigir `Fluxo unico safety` e `Quality Gate`.
3. Criar smoke test pos-merge para API, auth basico e build frontend.
