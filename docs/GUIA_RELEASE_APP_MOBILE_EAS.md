# Guia - Release do app mobile com EAS

Objetivo: evitar publicar uma atualizacao OTA no canal errado. O app so recebe
updates do mesmo canal usado no build/APK instalado.

Para publicacao nas lojas, use tambem:

- `docs/APP_MOBILE_PUBLICACAO_LOJAS.md`

## Regra principal

- APK interno baixado pelo link do EAS geralmente usa o profile `preview` e o
  canal `preview`.
- Build de loja/producao usa o profile `production` e o canal `production`.
- Se o usuario esta com APK `preview`, publicar apenas em `production` nao muda
  o app instalado.

## Build de preview somente manual

O workflow `App Mobile - EAS Build Manual (Android APK)` nao e executado a cada
push na `main`. Ele deve ser iniciado manualmente no GitHub Actions apenas quando
um novo APK for realmente necessario.

Antes de confirmar o workflow:

1. informe o motivo do novo APK;
2. confirme que uma OTA nao atende a necessidade;
3. verifique se houve mudanca nativa, runtime novo ou se o APK anterior deixou
   de estar disponivel.

Mudancas somente em JavaScript/TypeScript, telas, textos, estilos, chamadas ao
backend e assets compativeis devem reutilizar o APK instalado e seguir o fluxo
OTA do canal `preview` ou `production`. Um merge na `main`, sozinho, nao e motivo
para gerar outro APK.

## Decisao obrigatoria: OTA ou novo binario

O fluxo padrao do CorePet e OTA. Nao iniciar um novo build, `eas submit`, Play
Console, App Store Connect ou configuracao de Service Account antes de provar
que a mudanca exige codigo nativo.

Use OTA quando a entrega tiver somente:

- telas e navegacao em JavaScript/TypeScript;
- chamadas para APIs/backend;
- textos, estilos e assets compativeis;
- correcoes que nao adicionam nem atualizam modulos nativos.

Nesse caso, mantenha a mesma `version` e o mesmo `runtimeVersion` dos binarios
ativos. Tambem nao altere `versionCode` nem `buildNumber`. Publique para Android
e iOS juntos:

```bash
cd app-mobile
eas update --channel production --platform all --environment production --message "mensagem curta"
```

Nao rode `expo install --fix` como parte de uma OTA. Se o Expo Doctor recomendar
novas versoes de dependencias nativas, registre a recomendacao para uma tarefa
separada; aceitar a correcao muda o contrato nativo e pode obrigar um novo
binario nas lojas.

Novo binario so deve ser preparado quando houver pelo menos uma destas causas:

- dependencia ou plugin nativo novo/atualizado;
- permissao ou configuracao nativa alterada;
- mudanca necessaria em `android/` ou no projeto iOS;
- runtime atual incapaz de executar a nova versao.

Antes de escolher o fluxo, sempre conferir:

```bash
cd app-mobile
eas build:list --platform all --limit 20 --json --non-interactive
eas update:list --branch production --limit 10 --json --non-interactive
```

Se ainda houver duvida, comparar o fingerprint local com os builds ativos. Uma
mudanca somente em numero de compilacao, script operacional ou configuracao que
nao entra no aplicativo nao basta, por si so, para trocar OTA por loja.

### Estado operacional verificado em 27/08/2026

- iOS: aplicativo publicado. A App Store Connect exibe o CorePet como `Pronto
  para distribuicao` e possui um contrato atualizado pendente de aceite pelo
  titular antes do envio de uma nova versao.
- Android: aplicativo publicado; a Google Play exibe a versao `14 (1.0.3)`
  ativa em producao e o binario usa runtime `1.0.3`.
- O canal `production` ja possui historico de OTAs para Android e iOS juntos.
- Os artefatos `1.0.4` gerados em 22/08/2026 nao devem substituir os binarios
  atuais sem uma decisao explicita de nova versao nativa.
- O fluxo atual nao depende de criar outra conta Google ou Service Account de
  Play Store. Nao iniciar esse cadastro para uma atualizacao OTA.

## Antes de publicar update

1. Confirmar qual canal o build instalado usa:

```bash
cd app-mobile
eas build:list --platform android --limit 5 --json
```

2. No resultado, conferir `channel`, `buildProfile`, `runtimeVersion` e
   `gitCommitHash` do APK que foi entregue ao usuario.

3. Rodar a validacao local:

```bash
cd app-mobile
npm run check
```

## Publicar no canal correto

Para APK interno:

```bash
cd app-mobile
eas update --channel preview --platform all --environment preview --message "mensagem curta"
```

Para build de loja/producao, somente quando a decisao acima comprovar mudanca
nativa:

```bash
cd app-mobile
eas update --channel production --platform all --environment production --message "mensagem curta"
```

Quando a mesma correcao precisa chegar aos dois tipos de app, publicar nos dois
canais e registrar os dois grupos de update.

## Verificar publicacao

```bash
cd app-mobile
eas update:list --branch preview --limit 3 --json
eas update:view <UPDATE_GROUP_ID> --json
```

Trocar `preview` por `production` quando o update for de producao.

Conferir:

- `branch` igual ao canal esperado;
- `runtimeVersion` igual ao build instalado;
- plataformas `android` e `ios`, quando aplicavel;
- `gitCommitHash` igual ao commit esperado.

## Quando precisa de novo APK

EAS Update so troca JavaScript/assets compativeis com o mesmo runtime. Gerar novo
APK quando houver:

- mudanca nativa;
- novo plugin nativo;
- permissao Android/iOS nova;
- alteracao de runtime;
- dependencia nativa que exige rebuild.

## Build de loja (excecao nativa)

Antes de gerar build de loja:

```bash
cd app-mobile
npm run check
```

Build Android para Google Play:

```bash
cd app-mobile
eas build --platform android --profile production
```

Build iOS para App Store/TestFlight:

```bash
cd app-mobile
eas build --platform ios --profile production
```

O profile `production` usa:

- canal EAS: `production`;
- API: `https://corepet.com.br/api`;
- tenant padrao configurado em `eas.json`;
- Android package: `br.com.corepet.app`;
- iOS bundle identifier: `br.com.corepet.app`.

## Submissao para as lojas (excecao nativa)

Primeira submissao Android:

- criar o app manualmente na Play Console;
- preencher cadastro, privacidade, classificacao e teste;
- subir o primeiro AAB manualmente se a API da Play ainda nao estiver liberada.

Submissoes Android seguintes podem usar EAS Submit quando houver Service Account
configurada:

```bash
cd app-mobile
eas submit --platform android --profile production
```

Submissao iOS pode usar EAS Submit quando a conta Apple Developer e App Store
Connect estiverem configuradas:

```bash
cd app-mobile
eas submit --platform ios --profile production
```

Para iOS, antes de depender de notificacoes push em producao, confirmar as
credenciais APNs/Apple Push no fluxo de credenciais do EAS.

## Orientacao para teste no aparelho

Depois de publicar OTA, pedir para o usuario:

1. fechar totalmente o app;
2. abrir com internet e esperar alguns segundos;
3. fechar totalmente de novo;
4. abrir novamente.

O Expo pode baixar o update em uma abertura e aplicar na proxima.
