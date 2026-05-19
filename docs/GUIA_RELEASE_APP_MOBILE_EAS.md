# Guia - Release do app mobile com EAS

Objetivo: evitar publicar uma atualizacao OTA no canal errado. O app so recebe
updates do mesmo canal usado no build/APK instalado.

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

## Orientacao para teste no aparelho

Depois de publicar OTA, pedir para o usuario:

1. fechar totalmente o app;
2. abrir com internet e esperar alguns segundos;
3. fechar totalmente de novo;
4. abrir novamente.

O Expo pode baixar o update em uma abertura e aplicar na proxima.
