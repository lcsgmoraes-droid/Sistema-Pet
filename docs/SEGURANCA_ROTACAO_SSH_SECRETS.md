# Seguranca - rotacao de SSH e secrets

Este documento define o procedimento seguro para trocar chaves SSH e secrets do
Sistema Pet sem expor valores sensiveis no Git, no chat ou nos logs.

Ele nao autoriza deploy nem mudanca em producao. Qualquer comando no servidor
continua exigindo autorizacao explicita do Lucas.

## Quando rotacionar

Rotacionar SSH ou secrets nestes casos:

- A cada 90 dias para chaves SSH operacionais.
- Quando um computador for perdido, vendido, formatado ou compartilhado.
- Quando alguem deixar de precisar de acesso.
- Quando houver suspeita de vazamento, malware ou uso indevido.
- Depois de expor acidentalmente qualquer token, webhook, senha ou chave.
- Antes de promover uma integracao critica de teste para producao.

## Inventario minimo

Manter este inventario atualizado sem gravar o valor dos secrets:

| Item | Onde fica | Dono | Rotacao alvo |
|---|---|---|---|
| SSH `petdeploy` | `/home/petdeploy/.ssh/authorized_keys` | Lucas/Codex | 90 dias ou incidente |
| SSH root fallback | `/root/.ssh/authorized_keys` | Lucas | Somente fallback, revisar trimestralmente |
| `.env` de producao | `/opt/petshop/.env` | Lucas | 90 dias ou incidente |
| SMTP/transacional | Provedor de e-mail e `.env` | Lucas | 90 dias ou incidente |
| Webhook Ops | Provedor do canal e `.env` | Lucas | 90 dias ou incidente |
| Tokens externos | Provedores externos e `.env` | Lucas | Conforme risco do provedor |

## Rotacao planejada de SSH `petdeploy`

1. Gerar uma nova chave local com nome datado.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/mlprohub_codex_deploy_YYYYMM -C "petdeploy-mlprohub-YYYYMM"
```

2. Copiar apenas a chave publica para o servidor usando a chave atual ou o root
fallback autorizado.

3. Adicionar a nova chave em `/home/petdeploy/.ssh/authorized_keys` mantendo a
chave antiga temporariamente.

4. Validar a nova chave.

```bash
ssh -i ~/.ssh/mlprohub_codex_deploy_YYYYMM -o IdentitiesOnly=yes -o BatchMode=yes petdeploy@192.241.150.121 "sudo -n /usr/local/sbin/petshop-status-producao"
```

5. Atualizar a referencia local usada pelo fluxo operacional. Preferir manter o
nome padrao `~/.ssh/mlprohub_codex_deploy` apontando para a chave ativa ou
atualizar os documentos no mesmo PR.

6. Remover a chave antiga de `/home/petdeploy/.ssh/authorized_keys`.

7. Validar que a chave antiga nao entra mais e que a nova continua funcionando.

8. Registrar no guia mestre a data, o motivo e o responsavel. Nao registrar o
conteudo da chave privada nem da chave publica.

## Rotacao emergencial de SSH

Use quando houver suspeita de vazamento.

1. Entrar com root fallback autorizado ou acesso console do provedor.
2. Remover imediatamente a chave suspeita de `authorized_keys`.
3. Criar/adicionar uma nova chave.
4. Validar `petshop-status-producao`.
5. Rodar health publico e watchdog.
6. Registrar o incidente e revisar se outros secrets tambem precisam ser
rotacionados.

## Rotacao planejada de secrets de producao

1. Listar o secret a ser trocado e o impacto esperado.
2. Criar janela de manutencao quando o secret afetar login, pagamento, e-mail,
integracao fiscal, Bling, webhook ou banco.
3. Gerar o novo valor diretamente no provedor ou no servidor. Nao colar em chat.
4. Atualizar `/opt/petshop/.env` no servidor de producao.
5. Reiniciar somente os servicos afetados ou rodar o deploy seguro quando houver
mudanca de codigo junto.
6. Validar:
   - `https://mlprohub.com.br/api/health`
   - `https://mlprohub.com.br/api/health/watchdog`
   - login basico
   - fluxo afetado pelo secret
7. Remover/revogar o secret antigo no provedor.
8. Registrar data, item rotacionado, responsavel e validacoes feitas sem expor o
valor.

## Cuidados obrigatorios

- Nunca commitar `.env`, token, webhook, senha, chave privada ou backup com
secrets.
- Nunca imprimir webhook, token ou senha em comando de teste.
- Preferir ferramentas/provedores que permitem revogar o secret antigo depois
de validar o novo.
- Para banco de dados, planejar janela propria. Troca de senha de banco exige
coordenar Postgres, `.env`, backend e worker.
- Para SMTP, validar envio para provedores diferentes quando possivel.

## Registro de rotacao

Usar este modelo no fim de cada rotacao:

| Campo | Valor |
|---|---|
| Data/hora |  |
| Responsavel |  |
| Item rotacionado |  |
| Motivo |  |
| Servicos afetados |  |
| Validacao feita |  |
| Chave/secret antigo revogado |  |
| Observacoes sem secrets |  |
