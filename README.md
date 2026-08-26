# Sistema Pet

ERP multi-tenant para pet shops, com PDV, estoque, clientes, produtos,
financeiro, campanhas, integracoes e operacao segura em producao.

## Comece por aqui

Mapa oficial do codigo-fonte:

- `docs/MAPA_CODIGO_FONTE.md`

Arquitetura atual:

- `docs/ARQUITETURA.md`

O indice oficial de documentacao fica em:

- `docs/INDICE_OPERACIONAL.md`

O guia vivo de maturidade 10/10 fica em:

- `docs/MATURIDADE_GERAL_10_10_GUIA.md`

A matriz das 14 areas de governanca enterprise fica em:

- `docs/GOVERNANCA_ENTERPRISE.md`

O indice e esses guias mandam mais do que documentos antigos, backups historicos
ou anotacoes soltas.

## Codigo-fonte oficial

| Produto | Fonte |
|---|---|
| Backend e regras de negocio | `backend/app/` |
| Sistema web | `frontend/src/` |
| Aplicativo mobile | `app-mobile/src/` |
| Evolucao do banco | `backend/alembic/versions/` |

Pastas de build, containers, dependencias, uploads e arquivos `.env` nao sao
codigo-fonte. Veja a explicacao completa em `docs/MAPA_CODIGO_FONTE.md`.

Para contribuir, siga `CONTRIBUTING.md` e `AGENTS.md`.

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
| HOMOLOG dedicado | Aceite com dados ficticios antes de producao | Planejado em `docs/GOVERNANCA_ENTERPRISE.md`; ainda nao disponivel |
| Producao | Dados reais, deploy via `petdeploy` | `docs/PRODUCAO_DEPLOY_SSH.md` |

## Producao

Deploy real so pelo caminho seguro documentado:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_producao_remoto.ps1
```

Antes de qualquer deploy real, confirmar escopo, rollback e autorizacao.

## Documentacao

Novas evidencias de trabalho devem seguir:

- `docs/PADRAO_EVIDENCIA.md`

Entregas relevantes e homologacoes devem usar:

- `docs/templates/FICHA_ENTREGA.md`
- `docs/templates/REGISTRO_HOMOLOGACAO.md`

Quando um PR fecha uma frente de maturidade, atualizar no mesmo PR:

- `docs/MATURIDADE_GERAL_10_10_GUIA.md`
- o guia especifico da area afetada
- o indice operacional se a rota de leitura mudar

## Status

O placar atualizado esta sempre em `docs/MATURIDADE_GERAL_10_10_GUIA.md`.
