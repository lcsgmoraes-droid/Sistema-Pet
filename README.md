# Sistema Pet

ERP multi-tenant para pet shops, com PDV, estoque, clientes, produtos,
financeiro, campanhas, integracoes e operacao segura em producao.

## Comece por aqui

O indice oficial de documentacao fica em:

- `docs/INDICE_OPERACIONAL.md`

O guia vivo de maturidade 10/10 fica em:

- `docs/MATURIDADE_GERAL_10_10_GUIA.md`

Esses dois arquivos mandam mais do que documentos antigos, backups historicos ou
anotacoes soltas.

## Fluxo de trabalho

Antes de alterar codigo, confira onde voce esta:

```powershell
git status --short --branch
```

Se estiver em `main` ou `master`, comece uma branch nova:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_start_task.ps1 -Tipo feat -Nome "nome da tarefa"
```

Se ja estiver em uma branch de tarefa, continue nela. A `main` deve ser conferida
no inicio da tarefa e antes de fechar/enviar a branch, nao a cada passo pequeno.

Ao terminar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "mensagem clara" -Push
```

Nunca faca commit ou push direto em `main`.

## Validacao local

Validacao geral:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validar_fluxo.ps1
```

Check seguro de ambiente DEV:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_dev_environment.ps1
```

Bootstrap de PC novo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_dev_environment.ps1
```

## Ambientes

| Ambiente | Uso | Referencia |
|---|---|---|
| DEV local | Desenvolvimento, testes e validacao antes de PR | `docs/DEV_ENVIRONMENT_CHECK.md` |
| MCP local | Ferramentas locais para Codex/VS Code | `mcp/README.md` |
| CI/GitHub | Checks obrigatorios e suites longas | `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md` |
| Producao | Dados reais, deploy via `petdeploy` | `docs/PRODUCAO_DEPLOY_SSH.md` |

## Producao

Deploy real so pelo caminho seguro documentado:

```powershell
ssh -i ~/.ssh/mlprohub_codex_deploy -o IdentitiesOnly=yes -o BatchMode=yes petdeploy@192.241.150.121 "sudo -n /usr/local/sbin/petshop-deploy-producao"
```

Antes de qualquer deploy real, confirmar escopo, rollback e autorizacao.

## Documentacao

Novas evidencias de trabalho devem seguir:

- `docs/PADRAO_EVIDENCIA.md`

Quando um PR fecha uma frente de maturidade, atualizar no mesmo PR:

- `docs/MATURIDADE_GERAL_10_10_GUIA.md`
- o guia especifico da area afetada
- o indice operacional se a rota de leitura mudar

## Status

O placar atualizado esta sempre em `docs/MATURIDADE_GERAL_10_10_GUIA.md`.
