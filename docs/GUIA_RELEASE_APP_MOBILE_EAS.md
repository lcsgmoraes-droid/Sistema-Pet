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
eas update --channel preview --platform all --message "mensagem curta"
```

Para build de loja/producao:

```bash
cd app-mobile
eas update --channel production --platform all --message "mensagem curta"
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

## Build de loja

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

## Submissao para as lojas

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
