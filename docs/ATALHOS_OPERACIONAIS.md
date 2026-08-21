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
| Parar o ambiente DEV | `FLUXO_UNICO.bat dev-down` |
| Fluxo interno do ambiente local | `scripts/fluxo_unico.ps1` |
| Iniciar somente o frontend DEV | `scripts/iniciar_frontend_dev.ps1` |
| Iniciar o app mobile no Expo | `scripts/iniciar_app_mobile.ps1` |
| Diagnosticar autenticacao no DEV | `scripts/diagnosticar_autenticacao_dev.ps1` |
| Rodar o E2E longo com protecao de producao | `scripts/executar_testes_e2e.ps1` |
| Fazer manutencao controlada no banco DEV | `scripts/manutencao_banco_dev.ps1` |
| Operar o piloto WhatsApp local | `scripts/whatsapp_pilot.ps1` |
| Iniciar deploy remoto pelo Windows | `scripts/deploy_producao_remoto.ps1` |
| Executar deploy dentro do servidor | `scripts/deploy_producao_seguro.sh` |
| Diagnosticar producao sem alterar nada | `python scripts/diagnosticar_producao_publica.py` |
| Entender o deploy real | `docs/PRODUCAO_DEPLOY_SSH.md` |

## Atalhos de compatibilidade

Os arquivos abaixo nao possuem mais logica propria. Todos encaminham para uma
fonte oficial desta pagina:

- `deploy.sh`;
- `deploy-producao.sh`;
- `deploy_completo_producao.sh`;
- `CORRIGIR_PRODUCAO.sh`;
- `EXECUTAR_NO_SERVIDOR.sh`;
- `deploy-prod-auto.ps1`.

Essa compatibilidade impede quebra imediata de atalhos locais e, ao mesmo tempo,
remove comportamentos antigos como push direto na `main`, reset forcado do Git,
alteracao manual de migrations e reinicio sem rebuild.

Os quatro nomes antigos relacionados a erro 404 tambem foram preservados, mas
agora executam somente o diagnostico publico e nao conseguem fazer deploy:

- `CORRIGIR_LEMBRETES_404_SIMPLES.ps1`;
- `CORRIGIR_LEMBRETES_404.ps1`;
- `DIAGNOSTICAR_404.ps1`;
- `DIAGNOSTICAR_E_CORRIGIR_404.sh`.

O diagnostico central verifica API, watchdog, commit publicado e uma rota da
aplicacao web. Ele nao acessa SSH, containers, banco ou arquivos de ambiente.

Os atalhos locais historicos tambem foram preservados sem manter implementacoes
duplicadas:

- `INICIAR_APP.bat` inicia o script oficial do app mobile e nao possui IP fixo;
- `INICIAR_BACKEND_LOCAL.bat`, `INICIAR_DEV.bat` e `INICIAR_TUDO.bat`
  encaminham para `FLUXO_UNICO.bat dev-up`;
- `INICIAR_FRONTEND.bat` inicia o script oficial do frontend DEV;
- `PARAR_TUDO.bat` encaminha para `FLUXO_UNICO.bat dev-down`.
- `FRONTEND_DEV.bat` encaminha para o mesmo inicializador oficial do frontend;
- `EXECUTAR_TESTES_E2E.bat` valida as variaveis e bloqueia producao sem liberacao;
- `TESTAR_AUTENTICACAO.bat` executa um diagnostico somente no DEV local;
- `PILOTO_WHATSAPP.bat` encaminha para a automacao oficial do piloto;
- `CORRIGIR_PERMISSOES_ADMIN.bat` e `RESETAR_SEQUENCES.bat` usam uma unica
  manutencao controlada, fixada no container e no banco DEV e com confirmacao.

Para testar o app em um celular fisico, a URL da API pode ser informada como
primeiro argumento, por exemplo:

```powershell
.\INICIAR_APP.bat http://192.168.1.20:8000/api
```

O endereco depende da rede atual e por isso nao fica gravado no codigo.

## Entradas antigas bloqueadas

`setup-server.sh` pertence a uma infraestrutura antiga. O arquivo agora apenas
explica o bloqueio e termina sem alterar o computador ou o servidor. Preparacao
de infraestrutura deve seguir o guia atual e exigir autorizacao operacional.

Os atalhos abaixo usavam definicoes de containers que nao existem mais e podiam
confundir dados locais com producao real. Eles agora apenas explicam o caminho
correto e terminam sem alterar banco, arquivos ou containers:

- `INICIAR_BANCO_PRODUCAO.bat`;
- `INICIAR_PRODUCAO_LOCAL.bat`;
- `INICIAR_PRODUCAO.bat`.

Outros atalhos antigos tambem ficaram bloqueados:

- `ASSISTENTE_RELEASE.bat` e `ASSISTENTE_RELEASE_EXECUTAR.bat` preparavam
  blocos historicos de commit que nao representam mais a estrutura atual;
- `FRONTEND_PILOTO.bat` dependia de uma configuracao removida e podia misturar
  o ambiente DEV com dados reais;
- `IMPORTAR_SIMPLESVET_TESTE.bat` usava um caminho fixo de computador e nao
  exigia a escolha explicita da empresa de destino. O codigo do importador foi
  preservado para receber uma camada multitenant segura em uma tarefa propria.

O guia historico `GUIA_COMPLETO_AMBIENTES.md` virou um redirecionamento curto
porque descrevia ambientes, dominios e credenciais que foram descontinuados.

## Protecao automatica

`scripts/validate_repository_structure.py` e os testes do repositorio verificam
que:

- todos os atalhos continuam apontando para o fluxo seguro;
- os atalhos de diagnostico continuam somente leitura;
- nenhuma operacao destrutiva conhecida volta para esses arquivos da raiz;
- o instalador antigo permanece bloqueado;
- nenhum novo `.bat`, `.ps1` ou `.sh` pode aparecer na raiz sem ser
  classificado como oficial, compatibilidade ou bloqueado.

Qualquer mudanca nessa regra deve ser pequena, revisada em Pull Request e
validada pelos checks do GitHub.
