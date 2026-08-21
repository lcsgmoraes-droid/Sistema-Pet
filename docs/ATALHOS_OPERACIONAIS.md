# Atalhos operacionais e fontes oficiais

Atualizado em: 2026-08-20

Este documento evita que nomes antigos de scripts sejam confundidos com novas
formas de operar o sistema. Existe uma unica implementacao real para cada
operacao critica; os nomes antigos, quando preservados, apenas encaminham para
ela.

## Fontes oficiais

| Necessidade | Caminho oficial |
|---|---|
| Checar, iniciar DEV e consultar status | `FLUXO_UNICO.bat` |
| Fluxo interno do ambiente local | `scripts/fluxo_unico.ps1` |
| Iniciar deploy remoto pelo Windows | `scripts/deploy_producao_remoto.ps1` |
| Executar deploy dentro do servidor | `scripts/deploy_producao_seguro.sh` |
| Entender o deploy real | `docs/PRODUCAO_DEPLOY_SSH.md` |

## Atalhos de compatibilidade

Os arquivos abaixo nao possuem mais logica propria. Todos encaminham para um dos
dois scripts oficiais:

- `deploy.sh`;
- `deploy-producao.sh`;
- `deploy_completo_producao.sh`;
- `CORRIGIR_PRODUCAO.sh`;
- `EXECUTAR_NO_SERVIDOR.sh`;
- `deploy-prod-auto.ps1`.

Essa compatibilidade impede quebra imediata de atalhos locais e, ao mesmo tempo,
remove comportamentos antigos como push direto na `main`, reset forcado do Git,
alteracao manual de migrations e reinicio sem rebuild.

## Entrada antiga bloqueada

`setup-server.sh` pertence a uma infraestrutura antiga. O arquivo agora apenas
explica o bloqueio e termina sem alterar o computador ou o servidor. Preparacao
de infraestrutura deve seguir o guia atual e exigir autorizacao operacional.

## Protecao automatica

`scripts/validate_repository_structure.py` e os testes do repositorio verificam
que:

- todos os atalhos continuam apontando para o fluxo seguro;
- nenhuma operacao destrutiva conhecida volta para esses arquivos da raiz;
- o instalador antigo permanece bloqueado.

Qualquer mudanca nessa regra deve ser pequena, revisada em Pull Request e
validada pelos checks do GitHub.
