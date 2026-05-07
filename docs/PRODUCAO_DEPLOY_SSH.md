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

O script `scripts/deploy_producao_seguro.sh` e o caminho oficial. Ele faz pull de `origin/main`, gera frontend, reconstrui a imagem `petshop-backend:prod`, sobe `postgres`, `backend`, `worker-bling` e `nginx`, aplica Alembic e valida health.

## Validacao apos deploy

```bash
ssh -o BatchMode=yes root@192.241.150.121 "cd /opt/petshop && git rev-parse --short HEAD && docker compose -f docker-compose.prod.yml ps && docker compose -f docker-compose.prod.yml exec -T backend alembic current"
```

```bash
curl -fsS https://mlprohub.com.br/api/health
curl -fsS https://mlprohub.com.br/api/health/watchdog
```

## Regras importantes

- Nunca considerar `git pull` sozinho como deploy de backend.
- O backend Python roda dentro da imagem Docker; mudanca Python exige rebuild do backend.
- Os jobs do Bling rodam no container `petshop-prod-worker-bling`; a API deve ficar com `BLING_SYNC_SCHEDULER_ENABLED=false` em producao.
- Nao usar `docker restart` como deploy de codigo.
- Nao subir producao se houver multiplas heads Alembic ou repositorio sujo no servidor.
- Quando a mudanca envolve Ops/observabilidade, validar `/ops` e `/ops/incidentes` depois do health.
