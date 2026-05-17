# Auditoria de CI/CD e deploy seguro

Atualizado em: 2026-05-16

Este arquivo acompanha a maturidade de CI/CD e deploy seguro do Sistema Pet.

Guia mestre da maturidade geral do sistema: `docs/MATURIDADE_GERAL_10_10_GUIA.md`.

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
| Feito | Deploy real validado com script seguro, health publico e containers healthy | `scripts/deploy_producao_seguro.sh` |
| Feito | Deploy oficial registra linha do tempo auditavel por etapa sensivel | `backend/logs/deploy_events.jsonl` |

## PRs ja juntados

| PR | Conteudo | Status |
|---|---|---|
| #55 | Deploy Safety em PRs, Backend CI em todo PR e guia CI/CD | Mergeado |
| #57 | Smoke CI com backend, auth basico e build frontend | Mergeado |
| #58 | `Smoke test` obrigatorio na branch protection | Mergeado |
| #64 | Correcao operacional de cupom/carimbos/reabertura de venda | Mergeado e deployado |
| #52/#53/#54 | Dependabot GitHub Actions v6 | Mergeados; sem impacto de runtime |

## Ultimo deploy real validado

Data: 2026-05-16.

Escopo deployado:

- Commit de runtime em producao: `697a8479` (`Corrige cupom e carimbos na reabertura de venda (#64)`).
- Script usado: `cd /opt/petshop && bash scripts/deploy_producao_seguro.sh`.
- Backup operacional criado no servidor: `/opt/petshop/backups/deploy_20260516_175143`.
- Backend reconstruido com imagem `petshop-backend:prod`.
- Frontend gerado em `runtime/frontend/dist`.
- Alembic executado com sucesso.
- Containers finais saudaveis: `backend`, `nginx`, `postgres`, `worker-bling`.
- Health publico validado: `https://mlprohub.com.br/api/health`.
- Watchdog publico validado: `https://mlprohub.com.br/api/health/watchdog`.

Observacao: apos esse deploy, os PRs #52, #53, #54 e #65 atualizaram apenas GitHub Actions/documentacao. Eles ficam na `main`, mas nao mudam codigo de runtime do servidor.

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
| Media | Feito em 2026-05-16; manter continuo | Revisar este guia apos deploy real | Ajusta o procedimento com evidencia operacional |
| Media | Continuo | Manter checks obrigatorios verdes em todo PR | Evita regressao do trilho seguro |
| Baixa | Continuo | Registrar incidentes e rollbacks quando ocorrerem | Mantem historico auditavel |

## Proximo passo recomendado

1. Em todo proximo deploy real autorizado, repetir `release-check`, script seguro no servidor e validacoes de health/watchdog.
2. Conferir no painel Ops ou no arquivo `backend/logs/deploy_events.jsonl` os eventos `running`, `success` ou `failed` do deploy.
3. Manter a `main` protegida pelos checks obrigatorios antes de merge.
