# Auditoria de CI/CD e deploy seguro

Atualizado em: 2026-05-17

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
| Feito | Comandos manuais sensiveis possuem wrapper auditavel com motivo obrigatorio | `scripts/auditar_comando_producao.sh` |
| Feito | Usuario operacional `petdeploy` criado para status/deploy sem SSH direto como root | `docs/PRODUCAO_DEPLOY_SSH.md` |
| Feito | Deploy completo via `petdeploy` validado com containers saudaveis | `docs/PRODUCAO_DEPLOY_SSH.md` |
| Feito | Rotacao de SSH/secrets documentada | `docs/SEGURANCA_ROTACAO_SSH_SECRETS.md` |
| Feito | Scripts de backup e restore smoke controlado criados para validar dump real sem tocar o banco de producao | `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md` |
| Feito | Restore smoke de dump real validado em container Postgres descartavel | `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md` |

## PRs ja juntados

| PR | Conteudo | Status |
|---|---|---|
| #55 | Deploy Safety em PRs, Backend CI em todo PR e guia CI/CD | Mergeado |
| #57 | Smoke CI com backend, auth basico e build frontend | Mergeado |
| #58 | `Smoke test` obrigatorio na branch protection | Mergeado |
| #64 | Correcao operacional de cupom/carimbos/reabertura de venda | Mergeado e deployado |
| #52/#53/#54 | Dependabot GitHub Actions v6 | Mergeados; sem impacto de runtime |
| #97 | Plano E2E minimo do Plano Basico | Mergeado e deployado |
| #98 | Usuario operacional `petdeploy` e deploy sem root direto | Mergeado e deployado via `petdeploy` |
| #100 | Backup e restore smoke controlado do banco | Mergeado e deployado via `petdeploy` |

## Ultimo deploy real validado

Data: 2026-05-17.

Escopo deployado:

- Commit de runtime em producao: `e950ec9a` (`Adiciona restore smoke de backup do banco`).
- Script usado: `sudo -n /usr/local/sbin/petshop-deploy-producao` via `petdeploy`.
- Backup operacional criado no servidor: `/opt/petshop/backups/deploy_20260517_135349`.
- Backend reconstruido com imagem `petshop-backend:prod`.
- Frontend gerado em `runtime/frontend/dist`.
- Alembic executado com sucesso.
- Containers finais saudaveis: `backend`, `nginx`, `postgres`, `worker-bling`.
- Health publico validado: `https://mlprohub.com.br/api/health`.
- Watchdog interno e health publico validados pelo script de deploy.

Observacao: o deploy via `petdeploy` teve um aviso transitorio do watchdog no
fim porque o backend ainda estava aquecendo o healthcheck interno. A validacao
repetida logo depois confirmou `backend`, `nginx`, `postgres` e `worker-bling`
como `healthy`, com health publico `ok` e watchdog publico `healthy`.

Restore smoke validado:

- Backup real: `/opt/petshop/backups/db/restore_smoke_20260517_135920.dump.gz`.
- Tamanho: `14699879` bytes.
- SHA-256: `5589dd14897a7f5f954fb623cb3a678ba895fdbc528a836eaa89fd87f6be6686`.
- Resultado: `restore_smoke_status=ok`, `public_tables=217`, `alembic_rows=1`.
- Container temporario removido e health/watchdog saudaveis apos o teste.

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

1. Em todo proximo deploy real autorizado, repetir `release-check`, usar `petdeploy` com `/usr/local/sbin/petshop-deploy-producao` e validar health/watchdog.
2. Conferir no painel Ops ou no arquivo `backend/logs/deploy_events.jsonl` os eventos `running`, `success` ou `failed` do deploy.
3. Separar deploy de runtime e docs/workflows para evitar rebuild de servidor quando a mudanca nao afeta aplicacao.
