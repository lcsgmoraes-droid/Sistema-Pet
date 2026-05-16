# Producao - acesso e deploy por SSH

Fonte oficial para deploy real do MLProHub em producao.

## Servidor atual

- Host SSH: `root@192.241.150.121`
- Caminho do projeto no servidor: `/opt/petshop`
- Dominio publico: `https://mlprohub.com.br`
- Health publico: `https://mlprohub.com.br/api/health`
- Watchdog publico: `https://mlprohub.com.br/api/health/watchdog`

Use o IP para SSH. O dominio pode estar atras de Cloudflare e nao deve ser usado como referencia para conexao SSH operacional.

Se algum MCP/conector listar outro IP, valide antes de usar. No ultimo deploy validado, o IP funcional foi `192.241.150.121`.

## Deploy padrao

Rodar a partir da maquina local:

```bash
ssh -o BatchMode=yes root@192.241.150.121 "cd /opt/petshop && bash scripts/deploy_producao_seguro.sh"
```

Antes de rodar o deploy, preencher o checklist e revisar o plano de rollback em `docs/PRODUCAO_ROLLBACK_CHECKLIST.md`.

O script `scripts/deploy_producao_seguro.sh` e o caminho oficial. Ele faz pull de `origin/main`, gera frontend, reconstrui a imagem `petshop-backend:prod`, sobe `postgres`, `backend`, `worker-bling` e `nginx`, aplica Alembic e valida health.

O deploy tambem instala o guardiao preventivo de disco (`scripts/ops_disk_guard.sh`) em `/etc/cron.d/petshop-ops-disk-guard`. Ele roda a cada 30 minutos e tambem ao fim do deploy, registra eventos em `backend/logs/disk_guard_events.jsonl` e, quando o uso do disco chega ao limite de risco, limpa apenas cache/imagens Docker nao usados. Ele nao remove volumes, banco, uploads nem dados operacionais.

O deploy tambem instala o watchdog externo do host (`scripts/ops_host_watchdog.sh`) em `/etc/cron.d/petshop-ops-host-watchdog`. Ele roda a cada minuto fora dos containers, valida o watchdog publico, o watchdog interno, health dos containers e excesso recente de 50x no nginx. Depois de falhas consecutivas, ele reinicia primeiro `backend`, depois `nginx` se o health publico continuar falhando, e `worker-bling` se estiver unhealthy. Ele nao reinicia Postgres automaticamente; nesse caso registra evento e aguarda acao humana. Eventos ficam em `backend/logs/host_watchdog_events.jsonl`.

## Validacao apos deploy

```bash
ssh -o BatchMode=yes root@192.241.150.121 "cd /opt/petshop && git rev-parse --short HEAD && docker compose -f docker-compose.prod.yml ps && docker compose -f docker-compose.prod.yml exec -T backend alembic current"
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
