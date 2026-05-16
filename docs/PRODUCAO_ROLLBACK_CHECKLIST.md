# Producao - checklist de deploy e rollback

Este documento e o roteiro operacional para deploy seguro e rollback do Sistema Pet em producao.

Ele nao autoriza deploy. Qualquer comando no servidor de producao ou push direto para `main` continua exigindo autorizacao explicita do Lucas.

## Referencias oficiais

- Deploy por SSH: `docs/PRODUCAO_DEPLOY_SSH.md`
- Fluxo unico DEV -> PROD: `docs/FLUXO_UNICO_DEV_PROD.md`
- Script oficial de deploy: `scripts/deploy_producao_seguro.sh`
- Servidor: `root@192.241.150.121`
- Projeto no servidor: `/opt/petshop`
- Health publico: `https://mlprohub.com.br/api/health`
- Watchdog publico: `https://mlprohub.com.br/api/health/watchdog`

## Checklist antes do deploy

Marcar estes itens antes de rodar qualquer comando no servidor:

| Status | Item | Como validar |
|---|---|---|
| Pendente | PR mergeado na `main` | GitHub mostra PR como mergeado |
| Pendente | Checks obrigatorios passaram | `MCP tests`, `Fluxo unico safety`, `Quality Gate`, `Smoke test` |
| Pendente | `main` local atualizada | `git status --short --branch` sem divergencia |
| Pendente | Fluxo unico local passou | `FLUXO_UNICO.bat release-check` |
| Pendente | Lucas autorizou deploy de producao | Confirmacao explicita no chat |
| Pendente | Janela de deploy combinada | Evitar horario critico |
| Pendente | Risco de migration revisado | Confirmar se Alembic e reversivel ou exige plano manual |
| Pendente | Espaco em disco suficiente | `df -h` no servidor, se houver duvida |

## Deploy padrao

Rodar somente depois da autorizacao explicita:

```bash
ssh -o BatchMode=yes root@192.241.150.121 "cd /opt/petshop && bash scripts/deploy_producao_seguro.sh"
```

Durante o deploy, guardar estes dados:

| Campo | Onde aparece |
|---|---|
| Commit antes do deploy | `backups/deploy_*/head_before.txt` |
| Commit depois do deploy | `backups/deploy_*/head_after.txt` |
| Backup operacional | Linha `Backup operacional: ...` no final do script |
| Estado dos containers antes | `backups/deploy_*/docker_ps_before.txt` |
| Estado dos containers depois | `backups/deploy_*/docker_ps_after.txt` |

## Validacao apos deploy

Rodar estes checks e guardar o resultado:

```bash
curl -fsS https://mlprohub.com.br/api/health
curl -fsS https://mlprohub.com.br/api/health/watchdog
```

```bash
ssh -o BatchMode=yes root@192.241.150.121 "cd /opt/petshop && git rev-parse --short HEAD && docker compose -f docker-compose.prod.yml ps && docker compose -f docker-compose.prod.yml exec -T backend alembic current"
```

Se a mudanca envolver Ops ou observabilidade, validar tambem:

- `https://mlprohub.com.br/ops`
- `https://mlprohub.com.br/ops/incidentes`

## Quando acionar rollback

Acionar rollback se qualquer item abaixo acontecer depois do deploy:

- Health publico falha de forma persistente.
- Watchdog publico falha de forma persistente.
- Backend inicia mas endpoints criticos retornam erro.
- Worker Bling fica unhealthy ou sem heartbeat.
- Nginx passa a servir frontend quebrado.
- Migration causa erro operacional ou suspeita de perda de dados.

Se houver suspeita de problema no banco, parar e tratar como incidente de dados. Nao improvisar rollback de banco.

## Rollback rapido de frontend

Usar quando o backend esta saudavel e o problema parece estar somente no frontend.

```bash
ssh -o BatchMode=yes root@192.241.150.121 "cd /opt/petshop && test -d runtime/frontend/dist.prev && rm -rf runtime/frontend/dist.bad && mv runtime/frontend/dist runtime/frontend/dist.bad && mv runtime/frontend/dist.prev runtime/frontend/dist && docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps nginx"
```

Validar:

```bash
curl -fsS https://mlprohub.com.br/api/health
curl -fsS https://mlprohub.com.br/api/health/watchdog
```

## Rollback de codigo backend

Usar quando o problema esta no codigo novo e nao depende de reverter dados do banco.

Substitua `backups/deploy_YYYYMMDD_HHMMSS` pelo backup operacional mostrado no deploy.
O comando abaixo usa aspas simples no comando remoto para evitar que a maquina local tente ler `head_before.txt`.

```bash
ssh -o BatchMode=yes root@192.241.150.121 'cd /opt/petshop && BACKUP_DIR=backups/deploy_YYYYMMDD_HHMMSS && TARGET_HEAD=$(cat "$BACKUP_DIR/head_before.txt") && git reset --hard "$TARGET_HEAD" && docker compose -f docker-compose.prod.yml build backend && docker compose -f docker-compose.prod.yml up -d backend worker-bling nginx'
```

Depois validar:

```bash
curl -fsS https://mlprohub.com.br/api/health
curl -fsS https://mlprohub.com.br/api/health/watchdog
```

```bash
ssh -o BatchMode=yes root@192.241.150.121 "cd /opt/petshop && docker compose -f docker-compose.prod.yml ps && docker compose -f docker-compose.prod.yml exec -T backend alembic current"
```

Atencao: se o deploy executou migration Alembic com mudanca de schema ou dados, nao fazer rollback de codigo sem revisar compatibilidade. O codigo antigo pode nao funcionar com o banco novo.

## Rollback de banco

Rollback de banco e operacao de alto risco.

Seguir esta regra:

1. Parar deploys e novas mudancas.
2. Confirmar qual migration rodou e qual erro aconteceu.
3. Validar se existe `downgrade` Alembic seguro para o caso.
4. Se nao houver downgrade seguro, planejar restore de backup com janela de manutencao.
5. So executar com autorizacao explicita do Lucas.

Nao usar `alembic downgrade` em producao sem plano validado.

## Registro do incidente ou rollback

Depois do deploy ou rollback, registrar:

| Campo | Valor |
|---|---|
| Data/hora |  |
| Responsavel |  |
| PR/commit implantado |  |
| Backup operacional |  |
| Health publico |  |
| Watchdog publico |  |
| Rollback usado |  |
| Observacoes |  |

## Estado esperado no fim

- `curl -fsS https://mlprohub.com.br/api/health` passa.
- `curl -fsS https://mlprohub.com.br/api/health/watchdog` passa.
- `docker compose -f docker-compose.prod.yml ps` mostra servicos principais saudaveis.
- `git status --porcelain` no servidor fica vazio.
- Evento de deploy ou falha fica registrado em `backend/logs/deploy_events.jsonl`.
