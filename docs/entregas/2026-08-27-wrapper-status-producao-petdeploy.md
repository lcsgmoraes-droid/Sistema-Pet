# Wrapper seguro de status da producao

## Problema encontrado

O guia operacional orientava o uso de
`/usr/local/sbin/petshop-status-producao`, mas o repositorio nao possuia o
instalador nem o script desse wrapper. O `sudo` solicitava senha porque o comando
nao estava autorizado, embora o wrapper de deploy continuasse correto.

## Correcao

- criado status de producao somente leitura;
- criado wrapper root-owned sem argumentos e com ambiente limpo;
- limitada a permissao do usuario `petdeploy` ao caminho exato do wrapper;
- registrado cada uso no log de comandos operacionais;
- feita a reinstalacao automatica dos wrappers de deploy, status e restore smoke
  em todo deploy;
- adicionados testes de contrato para a seguranca e a autocorrecao.

## Validacoes do status

- servidor corresponde ao DNS de `corepet.com.br`;
- repositorio esta limpo, na `main` e no mesmo commit servido publicamente;
- PostgreSQL, backend, worker Bling e nginx estao saudaveis;
- banco esta na migration Alembic `head`;
- health e watchdog publicos respondem corretamente.

## Rollback

A remocao de `/etc/sudoers.d/petshop-status` e
`/usr/local/sbin/petshop-status-producao` desfaz apenas o novo acesso de status.
O deploy, os containers e o banco nao dependem desse wrapper para funcionar.
