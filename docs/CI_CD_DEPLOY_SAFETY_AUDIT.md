# Auditoria de CI/CD e deploy seguro

Atualizado em: 2026-06-19

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
| Feito | Backend CI possui `ruff format` global bloqueante para backend e testes, sem excecao dos testes de transacao legados | `.github/workflows/backend-ci.yml`, `tests/test_backend_ci_workflow_contract.py` |
| Feito | Analise automatica do SonarCloud possui configuracao propria para ignorar caminhos sem runtime e manter exclusoes de duplicacao alinhadas ao `sonar-project.properties` | `.sonarcloud.properties`, `tests/test_sonarcloud_config_contract.py` |
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
| Feito | Deploy seguro detecta mudancas sem impacto de runtime e pula rebuild/restart | `scripts/deploy_producao_seguro.sh` |
| Feito | Caminho sem rebuild validado em producao sem recriar containers | `scripts/deploy_producao_seguro.sh` |
| Feito | Backend CI valida migrations Alembic em Postgres descartavel para banco limpo e historico controlado | `.github/workflows/backend-ci.yml`, `scripts/ci_migration_smoke.py` |
| Feito | Matriz de cobertura critica separa checks rapidos obrigatorios de suites longas | `docs/auditorias/testes-ci-cobertura-critica.md` |
| Feito | Suite E2E longa do Plano Basico possui workflow manual/agendado separado dos checks obrigatorios | `.github/workflows/e2e-long.yml` |

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
| #106 | Migration Smoke no Backend CI com Postgres descartavel | Mergeado |
| #107 | Fechamento Testes/CI 10/10 com matriz critica e E2E longo | Mergeado |
| #108 | Compose de producao repassa `OPS_ALERT_*` para o backend | Mergeado e deployado via `petdeploy` |
| #110 | Alerta Ops por e-mail operacional | Mergeado e deployado via `petdeploy` |

## Ultimo deploy real validado

Data: 2026-05-17.

Escopo deployado:

- Commit de runtime em producao: `56c59119` (`Adiciona alerta Ops por email`).
- Script usado: `sudo -n /usr/local/sbin/petshop-deploy-producao` via `petdeploy`.
- Backup operacional criado no servidor: `/opt/petshop/backups/deploy_20260517_151356`.
- Backend reconstruido com imagem `petshop-backend:prod`.
- Frontend gerado em `runtime/frontend/dist`.
- Alembic executado com sucesso.
- Containers finais saudaveis: `backend`, `nginx`, `postgres`, `worker-bling`.
- Health publico validado: `https://mlprohub.com.br/api/health`.
- Watchdog interno e health publico validados pelo script de deploy.

Validacao apos deploy:

- `petshop-status-producao`: commit `56c59119`, branch `main`, containers
  `backend`, `nginx`, `postgres` e `worker-bling` saudaveis.
- `https://mlprohub.com.br/api/health`: `{"status":"ok"}`.
- `https://mlprohub.com.br/api/health/watchdog`: `{"status":"healthy"}`.
- `OPS_ALERT_EMAIL_TO` configurado no `.env` seguro de producao com backup
  `backups/env/.env_20260517_151349_ops_alert_email`.
- Disparo controlado de alerta Ops por e-mail retornou `enabled=true`,
  `sent=1`, `sent_email=1`, `sent_webhook=0` e `status=sent`.
- `backend/logs/ops_alert_notifications.jsonl` registrou a deduplicacao do
  alerta controlado.
- Recebimento humano do e-mail em `prohubml@gmail.com` confirmado por Lucas em
  2026-05-17.

Restore smoke validado:

- Backup real: `/opt/petshop/backups/db/restore_smoke_20260517_135920.dump.gz`.
- Tamanho: `14699879` bytes.
- SHA-256: `5589dd14897a7f5f954fb623cb3a678ba895fdbc528a836eaa89fd87f6be6686`.
- Resultado: `restore_smoke_status=ok`, `public_tables=217`, `alembic_rows=1`.
- Container temporario removido e health/watchdog saudaveis apos o teste.

Deploy sem rebuild validado:

- Commit em producao: `7c390ed8`.
- Backup operacional do teste sem rebuild: `/opt/petshop/backups/deploy_20260517_141303`.
- Resultado: repositorio ja atualizado, health publico `ok`, sem build frontend/backend e sem restart/recreate de containers.
- Health publico e watchdog publico saudaveis apos o teste.

## Checks que devem proteger a `main`

| Check | Motivo |
|---|---|
| `MCP tests` | Garante maturidade e funcionamento dos MCPs locais |
| `Fluxo unico safety` | Garante trilho basico DEV -> PROD antes do merge |
| `Quality Gate` | Garante suite backend multitenant, import smoke e Migration Smoke |
| `Smoke test` | Garante smoke de backend/auth e build de frontend |

## Suites longas separadas

O workflow `E2E Long` fica fora dos checks obrigatorios de PR. Ele roda por
`workflow_dispatch` ou agenda semanal, usando somente variaveis `E2E_*` vindas
de GitHub Secrets ou ambiente local seguro. Quando as variaveis obrigatorias nao
existem, a suite pula com mensagem clara. Contra `mlprohub.com.br`, tambem exige
`E2E_ALLOW_PRODUCTION=true`.

Matriz de risco e cobertura: `docs/auditorias/testes-ci-cobertura-critica.md`.

## Migration Smoke CI

O job `Migration Smoke` cria dois bancos Postgres descartaveis:

- `petshop_migration_smoke_clean`: roda `alembic upgrade head` a partir de banco vazio.
- `petshop_migration_smoke_history`: roda `alembic upgrade oj20260515a1` e depois `alembic upgrade head`.

O script confirma que `alembic_version` chega ao head unico esperado e que o
schema possui volume minimo de tabelas. Ao final, os bancos temporarios sao
removidos automaticamente, exceto quando `MIGRATION_SMOKE_KEEP_DATABASES=true`
for usado para diagnostico local.

Evidencia local em 2026-05-17:

```text
migration_smoke_expected_head=ot20260516a2
migration_smoke_status label=clean status=ok
migration_smoke_status label=history status=ok
migration_smoke_status=ok
```

## O que falta para manter 10/10

| Prioridade | Status | Item | Motivo |
|---|---|---|---|
| Media | Feito em 2026-05-16; manter continuo | Revisar este guia apos deploy real | Ajusta o procedimento com evidencia operacional |
| Media | Continuo | Manter checks obrigatorios verdes em todo PR | Evita regressao do trilho seguro |
| Baixa | Continuo | Registrar incidentes e rollbacks quando ocorrerem | Mantem historico auditavel |

## Proximo passo recomendado

1. Em todo proximo deploy real autorizado, repetir `release-check`, usar `petdeploy` com `/usr/local/sbin/petshop-deploy-producao` e validar health/watchdog.
2. Conferir no painel Ops ou no arquivo `backend/logs/deploy_events.jsonl` os eventos `running`, `success` ou `failed` do deploy.
3. Seguir para Testes/CI avancado ou para o canal real de notificacao Ops, que depende de webhook seguro configurado em producao.
