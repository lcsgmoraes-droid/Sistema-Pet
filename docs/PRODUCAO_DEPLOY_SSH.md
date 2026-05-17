# Producao - acesso e deploy por SSH

Fonte oficial para deploy real do MLProHub em producao.

## Servidor atual

- Host SSH preferencial: `petdeploy@192.241.150.121`
- Host SSH de fallback: `root@192.241.150.121`
- Caminho do projeto no servidor: `/opt/petshop`
- Dominio publico: `https://mlprohub.com.br`
- Health publico: `https://mlprohub.com.br/api/health`
- Watchdog publico: `https://mlprohub.com.br/api/health/watchdog`

Use o IP para SSH. O dominio pode estar atras de Cloudflare e nao deve ser usado como referencia para conexao SSH operacional.

Se algum MCP/conector listar outro IP, valide antes de usar. No ultimo deploy validado, o IP funcional foi `192.241.150.121`.

## Deploy padrao

Rodar a partir da maquina local:

```bash
ssh -i ~/.ssh/mlprohub_codex_deploy -o IdentitiesOnly=yes -o BatchMode=yes petdeploy@192.241.150.121 "sudo -n /usr/local/sbin/petshop-deploy-producao"
```

Antes de rodar o deploy, preencher o checklist e revisar o plano de rollback em `docs/PRODUCAO_ROLLBACK_CHECKLIST.md`.

O usuario `petdeploy` foi criado em producao em 2026-05-17 com chave SSH deste
PC, pertence ao grupo `docker` e tem sudo sem senha apenas para wrappers
root-owned:

- `/usr/local/sbin/petshop-deploy-producao`
- `/usr/local/sbin/petshop-status-producao`

Usar `root@192.241.150.121` somente como fallback operacional autorizado.

O script `scripts/deploy_producao_seguro.sh` e o caminho oficial. Ele faz pull de `origin/main`, gera frontend, reconstrui a imagem `petshop-backend:prod`, sobe `postgres`, `backend`, `worker-bling` e `nginx`, aplica Alembic e valida health.

O deploy tambem instala o guardiao preventivo de disco (`scripts/ops_disk_guard.sh`) em `/etc/cron.d/petshop-ops-disk-guard`. Ele roda a cada 30 minutos e tambem ao fim do deploy, registra eventos em `backend/logs/disk_guard_events.jsonl` e, quando o uso do disco chega ao limite de risco, limpa apenas cache/imagens Docker nao usados. Ele nao remove volumes, banco, uploads nem dados operacionais.

O deploy tambem instala o watchdog externo do host (`scripts/ops_host_watchdog.sh`) em `/etc/cron.d/petshop-ops-host-watchdog`. Ele roda a cada minuto fora dos containers, valida o watchdog publico, o watchdog interno, health dos containers e excesso recente de 50x no nginx. Depois de falhas consecutivas, ele reinicia primeiro `backend`, depois `nginx` se o health publico continuar falhando, e `worker-bling` se estiver unhealthy. Ele nao reinicia Postgres automaticamente; nesse caso registra evento e aguarda acao humana. Eventos ficam em `backend/logs/host_watchdog_events.jsonl`.

## Comandos manuais auditaveis

Para qualquer comando sensivel em producao fora do script oficial de deploy,
envolver a execucao com `scripts/auditar_comando_producao.sh`.

Exemplo dentro do servidor:

```bash
cd /opt/petshop
bash scripts/auditar_comando_producao.sh \
  --action docker.ps \
  --reason "validacao operacional autorizada" \
  --label "docker compose ps" \
  -- docker compose -f docker-compose.prod.yml ps
```

O wrapper exige `--action`, `--reason` e o comando apos `--`. Ele registra
`started`, `success` ou `failed` em `backend/logs/ops_command_events.jsonl`,
incluindo usuario, host, commit atual, exit code e comando com redaction basica
de argumentos sensiveis como `token=...` e `password=...`.

Nao colocar secrets no `--reason`, no `--label` ou em argumentos quando houver
alternativa operacional.

## Notificacao de alertas Ops

O painel Ops pode enviar alertas criticos para um webhook externo quando
`OPS_ALERT_WEBHOOK_URL` estiver configurado no ambiente seguro do backend.

Variaveis relevantes:

- `OPS_ALERT_WEBHOOK_URL`: URL secreta do webhook. Nao versionar e nao colar no chat.
- `OPS_ALERT_WEBHOOK_MIN_SEVERITY`: severidade minima; padrao `critical`.
- `OPS_ALERT_WEBHOOK_TIMEOUT_SECONDS`: timeout HTTP; padrao `5`.
- `OPS_ALERT_NOTIFICATION_LOG_PATH`: log local de deduplicacao; padrao `logs/ops_alert_notifications.jsonl`.

O payload enviado e minimo: tipo/severidade do alerta, titulo, detalhe, acao,
tenant/rota/request quando existirem. O notifier nao envia o payload bruto do
alerta e nao registra a URL do webhook no resultado.

Depois de configurar a variavel secreta no servidor, validar com um alerta
controlado:

```bash
cd /opt/petshop
docker compose -f docker-compose.prod.yml exec -T backend python -m app.services.ops_alert_webhook_smoke --label "validacao-producao"
```

O comando deve retornar JSON com `enabled: true` e `sent: 1`, e o canal
operacional deve receber "Teste controlado de alerta Ops". O output nao deve
exibir a URL do webhook.

## Validacao apos deploy

```bash
ssh -i ~/.ssh/mlprohub_codex_deploy -o IdentitiesOnly=yes -o BatchMode=yes petdeploy@192.241.150.121 "sudo -n /usr/local/sbin/petshop-status-producao"
```

```bash
curl -fsS https://mlprohub.com.br/api/health
curl -fsS https://mlprohub.com.br/api/health/watchdog
```

Para rollback e registro operacional, usar `docs/PRODUCAO_ROLLBACK_CHECKLIST.md`.

## Regras importantes

- Nunca considerar `git pull` sozinho como deploy de backend.
- O backend Python roda dentro da imagem Docker; mudanca Python exige rebuild do backend.
- Os jobs do Bling rodam no container `petshop-prod-worker-bling`; a API deve ficar com `BLING_SYNC_SCHEDULER_ENABLED=false` em producao.
- Nao usar `docker restart` como deploy de codigo.
- Nao subir producao se houver multiplas heads Alembic ou repositorio sujo no servidor.
- Quando a mudanca envolve Ops/observabilidade, validar `/ops` e `/ops/incidentes` depois do health.
