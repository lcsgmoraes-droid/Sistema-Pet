# Homologacao - integridade e tempo de restauracao do backup

Data: 2026-08-27

Ambiente: homologacao local isolada em Docker

## Objetivo

Comprovar que um backup com checksum valido pode ser restaurado em outro
PostgreSQL, medir a duracao da recuperacao e remover todos os recursos
temporarios sem tocar producao.

## Execucao

1. A homologacao local foi construida com os Dockerfiles de producao.
2. O PostgreSQL de homologacao foi lido com `pg_dump` em formato customizado.
3. O arquivo comprimido e seu SHA-256 foram mantidos em volume Docker
   temporario.
4. `scripts/prod_db_restore_smoke.sh` restaurou o dump em outro PostgreSQL sem
   porta publicada.
5. O script validou tabelas, migration, checksum, duracao e limpeza final.

## Resultado

- Status: aprovado.
- Checksum: verificado.
- Duracao total: 8 segundos.
- Tabelas publicas: 255.
- Registros em `alembic_version`: 1.
- Container temporario removido: sim.
- Volume temporario removido: sim.
- Frontend e backend da homologacao: saudaveis antes do teste.

## Limites da evidencia

O teste usa somente dados ficticios de homologacao. Ele comprova a automacao e
o formato da telemetria, mas nao mede o tempo do banco real nem substitui a
rotina recorrente instalada no servidor de producao. Nenhum comando remoto foi
executado.
