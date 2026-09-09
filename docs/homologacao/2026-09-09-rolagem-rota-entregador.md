# Rolagem da rota no app do entregador

## Relato e diagnostico

Douglas relatou que nao consegue descer a tela da rota pelo celular. A imagem
enviada por Lucas mostra 67 paradas: 24 entregues e 43 pendentes.

O codigo usava `DraggableFlatList` com `scrollEnabled={false}` dentro de
`KeyboardSafeScrollView`. O detector de arrasto pode capturar o gesto enquanto
a lista esta impedida de rolar. Esta e a causa provavel encontrada por inspecao;
o travamento ainda nao foi reproduzido em aparelho nesta tarefa.

## Correcao preparada

- Uma unica lista controla a rolagem da tela, incluindo resumo e avisos no
  `ListHeaderComponent`.
- Rotas abertas usam a lista arrastavel; encerradas usam `FlatList`.
- Os modais ficam fora da lista e a ordenacao manual permanece disponivel.
- O icone de arrastar exige pressionar por 300 ms (antes: 70 ms), para reduzir
  ativacoes acidentais ao deslizar. O numero azul continua abrindo a ordem manual.
- Nenhuma dependencia, permissao, versao ou runtime foi alterado.

Referencia da biblioteca: [react-native-draggable-flatlist](https://github.com/computerjazz/react-native-draggable-flatlist).

## Validacao local

Executar dentro de `app-mobile`:

```powershell
npm run check
node --test scripts/test-detalhe-entrega-scroll.mjs
node scripts/test-large-files-700-batch-43-refactor.mjs
```

Os quatro testes de regressao usam componentes de tela e callbacks reais,
substituindo os componentes nativos por representacoes em memoria. Conferem
67 paradas, contagem 67/43/24, encaminhamento da reordenacao, listas encerradas,
acionamento por pressionar o icone e abertura da ordem manual. Nao executam
gestos Android/iOS nem comprovam fluidez ou alcance visual da ultima parada.

## Cenario de aceite no demo

Preparar na conta demo `corepeterp@gmail.com` um entregador exclusivo para este
teste e uma rota identificada como `TESTE ROLAGEM 67`, com clientes ficticios
numerados de 01 a 67. Usar 24 entregas concluidas e 43 pendentes para comparar
com a imagem. Nao reutilizar entregas de operacao real.

1. No app atualmente instalado, conferir versao/canal e registrar se a rolagem
   trava. Deslizar sobre nome, endereco, espaco do cartao e proximo ao icone.
2. Registrar a versao da correcao instalada antes de testar novamente.
3. Na versao corrigida, alcancar a parada 67 e retornar ao resumo.
4. Arrastar uma parada, inclusive perto da borda para exercitar a rolagem
   automatica; conferir persistencia ao sair e reabrir a rota.
5. Pelo numero azul, mover a parada 67 para a posicao 1 e conferir persistencia.
6. Abrir e fechar os modais de ordem e detalhes; continuar rolando.
7. Em uma rota ficticia encerrada, verificar rolagem e ausencia de arrasto.

## Estado em 09/09/2026

- Checagem TypeScript e testes locais passaram.
- ADB instalado; nenhum aparelho detectado nas consultas desta tarefa.
- A aba do Chrome no perfil CorePet estava autenticada como `victorteste`.
  Lucas foi solicitado a abrir a conta demo correta. Nenhum usuario, venda ou
  rota foi criado no demo ate esse acesso ser confirmado.
- Docker local estava desligado; nenhuma base local foi alterada.
- Historicos `eas build:list` e `eas update:list` consultados: existem runtimes
  `1.0.3` e `1.0.4`. A atualizacao mais recente listada em `production` para
  `1.0.3` e o grupo `97877384-0232-4de2-b600-a18f7911ebe0`.
- A mudanca desta tarefa e somente TypeScript, candidata a OTA compativel.
  O runtime/canal instalado precisa ser identificado antes de publicar/testar
  uma atualizacao. Nenhum build, OTA ou deploy foi executado.

Pendente: criar o cenario e o login no demo autenticado, reproduzir no aparelho,
aplicar a correcao em ambiente de teste e completar o aceite acima.
