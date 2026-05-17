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
3. Sobe um container Postgres temporario, sem porta publicada.
4. Restaura o dump nesse container descartavel.
5. Valida que tabelas publicas e `alembic_version` existem.
6. Remove o container temporario ao final.

O teste nao baixa dados para o computador local, nao imprime linhas de tabelas e
nao altera o banco de producao.

## Comando padrao

Rodar em producao pelo usuario operacional:

```bash
ssh -i ~/.ssh/mlprohub_codex_deploy -o IdentitiesOnly=yes -o BatchMode=yes petdeploy@192.241.150.121 "cd /opt/petshop && bash scripts/prod_db_restore_smoke.sh"
```

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
```

## Restaurar backup ja existente no smoke

Para testar um dump especifico:

```bash
ssh -i ~/.ssh/mlprohub_codex_deploy -o IdentitiesOnly=yes -o BatchMode=yes petdeploy@192.241.150.121 "cd /opt/petshop && bash scripts/prod_db_restore_smoke.sh /opt/petshop/backups/db/ARQUIVO.dump.gz"
```

## Politica de retencao

Por padrao, `scripts/prod_db_backup.sh` remove dumps `.dump.gz` com mais de 14
dias dentro de `/opt/petshop/backups/db`.

Para alterar temporariamente:

```bash
BACKUP_RETENTION_DAYS=30 bash scripts/prod_db_restore_smoke.sh
```

## Criterio para marcar como validado

So marcar o item do guia mestre como feito quando houver evidencia de:

- `backup_status=ok`.
- `restore_smoke_status=ok`.
- `alembic_rows` maior ou igual a 1.
- Container temporario removido.
- Health publico e watchdog saudaveis depois do teste.

Registrar apenas caminho do backup, tamanho, checksum e resultado. Nunca
registrar conteudo do banco.
