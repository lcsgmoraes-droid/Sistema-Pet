# Producao - backup e teste controlado de restore

Este documento define o caminho seguro para provar que o backup real do banco
consegue ser restaurado sem tocar o banco de producao.

Ele nao autoriza deploy nem comando em producao. Qualquer execucao no servidor
continua exigindo autorizacao explicita do Lucas.

## O que o teste faz

O script `scripts/prod_db_restore_smoke.sh`:

1. Cria um dump real do Postgres de producao com `scripts/prod_db_backup.sh`,
   quando nenhum arquivo de backup e informado.
2. Salva o dump em `/opt/petshop/backups/db`.
3. Cria um volume identificado e sobe um container Postgres temporario, sem
   porta publicada.
4. Restaura o dump nesse container descartavel.
5. Valida que tabelas publicas e `alembic_version` existem.
6. Remove o container e o volume temporarios ao final, inclusive quando o teste
   falha.

O teste nao baixa dados para o computador local, nao imprime linhas de tabelas e
nao altera o banco de producao.

## Comando padrao

Rodar em producao pelo usuario operacional:

```bash
ssh -i ~/.ssh/mlprohub_codex_deploy -o IdentitiesOnly=yes -o BatchMode=yes petdeploy@192.241.150.121 "sudo -n /usr/local/sbin/petshop-restore-smoke-producao"
```

O wrapper e root-owned, nao aceita argumentos e registra a operacao no log de
auditoria antes de criar um backup novo e restaura-lo em container descartavel.

Saida esperada, sem dados sensiveis:

```text
backup_status=ok
backup_file=/opt/petshop/backups/db/restore_smoke_YYYYMMDD_HHMMSS.dump.gz
backup_bytes=...
backup_sha256=...
restore_smoke_status=ok
public_tables=...
alembic_rows=1
restore_container_removed=true
restore_volume_removed=true
```

## Restaurar backup ja existente no smoke

O wrapper operacional nao aceita caminhos de arquivo. Testar um dump especifico
exige acesso root de fallback, autorizacao explicita e o wrapper de auditoria:

```bash
cd /opt/petshop
bash scripts/auditar_comando_producao.sh \
  --action database.restore_smoke_existing \
  --reason "validar dump especifico autorizado" \
  --label "restore smoke de dump existente" \
  -- bash scripts/prod_db_restore_smoke.sh /opt/petshop/backups/db/ARQUIVO.dump.gz
```

## Politica de retencao

Por padrao, `scripts/prod_db_backup.sh` remove dumps `.dump.gz` com mais de 14
dias dentro de `/opt/petshop/backups/db`.

Para alterar temporariamente:

```bash
BACKUP_RETENTION_DAYS=30 bash scripts/prod_db_restore_smoke.sh
```

## Copia externa (R2, B2 ou outro S3 compativel)

O script `scripts/prod_db_external_copy.sh` envia o backup local mais recente e
seu checksum para um bucket privado. Depois do envio, ele consulta o objeto no
provedor e so registra `external_copy:ok` no `/ops` quando tamanho e SHA-256
conferem.

As credenciais nao ficam no Git. Elas devem existir apenas em producao, no
arquivo root-owned `/etc/petshop/backup-external.env`, com permissao `0600`:

```bash
OPS_BACKUP_S3_BUCKET=nome-do-bucket-privado
OPS_BACKUP_S3_ENDPOINT_URL=https://ID_DA_CONTA.r2.cloudflarestorage.com
OPS_BACKUP_S3_REGION=auto
OPS_BACKUP_S3_PREFIX=corepet/database
AWS_ACCESS_KEY_ID=preencher-direto-no-servidor
AWS_SECRET_ACCESS_KEY=preencher-direto-no-servidor
```

O token deve permitir somente leitura e gravacao nesse bucket. O bucket deve
permanecer privado e ter uma regra de ciclo de vida para remover copias antigas
no prazo escolhido. Quando o arquivo seguro nao existe, o instalador mantem a
copia externa em standby e nao cria o agendamento. Quando existe, o envio roda
diariamente as 03:45, depois do backup local das 03:15.

Nunca enviar as chaves por chat, salvar em `.env` do repositorio ou imprimir no
log. A ativacao no servidor exige autorizacao explicita de producao.

## Ultima copia externa validada

Data: 2026-07-13.

- Commit em producao: `e2134e939`.
- Provedor: Cloudflare R2, bucket privado `corepet-backups-prod`.
- Objeto: `corepet/database/petshop_prod_20260713_234008.dump.gz`.
- Tamanho: `28973026` bytes.
- SHA-256: `910aea7b1c554dc35f76d30fa0194c47f44b9b20971db4ceb4634c0eb33be617`.
- Checksum complementar enviado e visivel no bucket.
- Retencao remota: 90 dias.
- Resultado: `external_copy_status=ok` e health publico saudavel.

## Criterio para marcar como validado

So marcar o item do guia mestre como feito quando houver evidencia de:

- `backup_status=ok`.
- `restore_smoke_status=ok`.
- `alembic_rows` maior ou igual a 1.
- Container temporario removido.
- Volume temporario removido.
- Health publico e watchdog saudaveis depois do teste.

Registrar apenas caminho do backup, tamanho, checksum e resultado. Nunca
registrar conteudo do banco.

## Ultimo teste validado

Data: 2026-05-17.

- Commit em producao: `e950ec9a`.
- Backup real testado: `/opt/petshop/backups/db/restore_smoke_20260517_135920.dump.gz`.
- Tamanho: `14699879` bytes.
- SHA-256: `5589dd14897a7f5f954fb623cb3a678ba895fdbc528a836eaa89fd87f6be6686`.
- Resultado: `restore_smoke_status=ok`.
- Validacao: `public_tables=217`, `alembic_rows=1`.
- Container temporario removido: `true`.
- Health publico e watchdog saudaveis depois do teste.
