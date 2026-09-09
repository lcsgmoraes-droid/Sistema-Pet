# Rolagem e fluxo da rota no app do entregador

## Relato e diagnostico

Douglas relatou que nao consegue descer a tela da rota pelo celular. A imagem
enviada por Lucas mostra 67 paradas: 24 entregues e 43 pendentes.

O travamento foi reproduzido no Samsung SM-S938B de Lucas, com CorePet 1.0.4,
versionCode 15, instalado pela Play Store, canal production. Na rota ficticia
de 67 paradas, deslizar sobre nome, endereco, area livre do cartao e icone
manteve as mesmas posicoes das paradas 1, 2 e 3. Deslizar sobre o aviso acima
dos cartoes moveu a pagina. O codigo usava `DraggableFlatList` com
`scrollEnabled={false}` dentro de `KeyboardSafeScrollView`, disputando o gesto.

## Correcao preparada

- Uma unica lista controla a rolagem da tela, incluindo resumo e avisos no
  `ListHeaderComponent`.
- Rotas abertas usam a lista arrastavel; encerradas usam `FlatList`.
- Os modais ficam fora da lista e a ordenacao manual permanece disponivel.
- O icone de arrastar exige pressionar por 300 ms (antes: 70 ms), para reduzir
  ativacoes acidentais ao deslizar. O numero azul continua abrindo a ordem manual.
- Formularios de ordem e nao entrega permitem rolagem com teclado aberto;
  detalhes usam a formatacao monetaria brasileira existente.
- App e ERP usam a mesma operacao de nao entrega: motivo preservado na venda,
  paradas restantes renumeradas, rotas encerradas protegidas. Se a ultima
  parada for devolvida, a rota vazia e removida e o app encerra o rastreamento
  antes de voltar para a lista.
- js-yaml foi ajustado de 4.3.1 para 4.3.2 por apontamento do Trivy; o teste
  de componentes usa imports do Node em vez de VM dinamica.
- Nenhuma dependencia nativa, permissao, versao ou runtime foi alterado.

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

O cenario ja foi criado na conta demo `corepeterp@gmail.com`, tenant online
`8f556b9e-3eb2-4e72-89db-10c512d53093`, com entregador exclusivo. A rota 600
tem 67 paradas ficticias, 24 concluidas e 43 pendentes. O roteiro abaixo deve
ser repetido na versao corrigida antes de liberar a atualizacao.

1. No app atualmente instalado, conferir versao/canal e registrar se a rolagem
   trava. Deslizar sobre nome, endereco, espaco do cartao e proximo ao icone.
2. Registrar a versao da correcao instalada antes de testar novamente.
3. Na versao corrigida, alcancar a parada 67 e retornar ao resumo.
4. Arrastar uma parada, inclusive perto da borda para exercitar a rolagem
   automatica; conferir persistencia ao sair e reabrir a rota.
5. Pelo numero azul, mover a parada 67 para a posicao 1 e conferir persistencia.
6. Abrir e fechar os modais de ordem e detalhes; continuar rolando.
7. Em uma rota ficticia encerrada, verificar rolagem e ausencia de arrasto.

## Testes executados no app instalado

| Cenario | Resultado observado |
| --- | --- |
| Login e perfil | Core Pet Demo e entregador exclusivo confirmados |
| Criacao de rota | Tres pedidos selecionados no celular; rota 601 criada |
| Entregar antes de iniciar | Bloqueado com orientacao para iniciar a rota |
| Iniciar | Rota passou a em_rota; app exibiu rastreamento ativo |
| Detalhes | Cliente, endereco e item ficticio carregaram |
| Receber em credito 3x | Registro persistido, pendente de integracao; sem cobranca real |
| Marcar entregue | Pedido 1116114 confirmado; resumo 3/2/1 |
| Nao entregue | Pedido 1116115 saiu da rota e voltou a pendente |
| Preservar motivo | **Falhou**: texto digitado nao permaneceu na venda |
| Numeracao apos nao entrega | **Falhou**: paradas ficaram numeradas 1 e 3 |
| Ordem manual | Endereco 3 movido para n1 e salvo |
| Arrastar | Pressionar e arrastar inverteu as duas paradas restantes |
| Concluir entregas | Segundo pedido remanescente entregue; resumo 2/0/2 |
| Finalizar e historico | Sucesso; rota concluida com duas entregas |
| Reabrir rota encerrada | Ordem preservada, sem arrasto |

Pela API autenticada como o entregador, fechar com tres pendencias e enviar
uma reordenacao incompleta retornaram HTTP 400, sem alterar a rota.

## Dados demo e evidencias

- Login `entregador.rolagem`: cliente 14577, usuario 70, sem permissoes
  administrativas do ERP. Senha somente no arquivo local ignorado pelo Git
  `runtime/qa-rolagem-entregador/acesso-demo.txt`.
- Cliente ficticio dos pedidos: 14578, sem usuario de app.
- Rota 600: `ROTA-20260909001747`, vendas 1116047 a 1116113.
- Rota 601, criada/concluida pelo celular: `R260909003332D40D1F`, vendas
  1116114 a 1116116; a venda 1116115 foi devolvida para pendente.
- Venda adicional 1116117, reservada para repetir a ocorrencia, aberta sem rota.
- Todos os 71 pedidos usam servico ficticio, total e taxa zero, sem estoque.
  Nenhum contato foi enviado pelo assistente. Rotas preexistentes preservadas.
- Capturas locais: `runtime/qa-rolagem-entregador/antes-travado.png`,
  `fluxo-motivo-sem-teclado.png`, `fluxo-historico-confirmado.png` e XMLs.

## Validacao das correcoes e limites

Passaram TypeScript, quatro testes de componentes/callbacks, checagem de tamanho
dos arquivos e 19 testes de backend sobre status, reordenacao e historico.
Os testes incluem preservar observacoes anteriores, motivo via query/body,
devolver a ultima parada e bloquear alteracoes em rotas encerradas.

```powershell
# Dentro de backend, usando banco isolado para os testes
$env:DATABASE_URL='sqlite://'
$env:ENVIRONMENT='test'
./.venv/Scripts/python.exe -m pytest tests/unit/test_entrega_status_contract.py tests/unit/test_ecommerce_entregador_rotas.py tests/unit/test_rotas_entrega_historico.py -q
```

Dois testes adicionais existentes em `test_rotas_entrega_router_contract.py`
falharam localmente ao procurar rotas diretamente em `router.routes`, com
FastAPI 0.137.2. Esses contratos nao foram tratados como aprovados.

A revisao automatica bloqueou o servidor de teste conectado ao ERP sem explicar
o motivo. A alternativa sem acesso ao ERP iniciou e gerou um bundle Android
com dados em memoria e os componentes reais corrigidos. Contudo, Expo Go 57.0.9
fechou com SIGSEGV em `libhermesvm.so` antes de exibir a tela. A causa desse
crash de teste nao foi determinada. Servidor encerrado, encaminhamento USB
removido e CorePet reaberto ao terminar.

**Pendente: validar a versao corrigida no aparelho**, incluindo atingir a parada
67, retorno ao topo, arrasto na borda e formularios com teclado; repetir o fluxo
com backend corrigido. Nao houve teste iOS nem cobranca real em operadora.

## Alinhamento das atualizacoes

Historicos EAS consultados: as ultimas atualizacoes production de 1.0.3 e 1.0.4
partem do mesmo commit `23eadc2b5dd2786671d92905836f6149b3b4c9ff`, nas duas
plataformas. Grupos:

- 1.0.3: `97877384-0232-4de2-b600-a18f7911ebe0`.
- 1.0.4: `16b66cef-4674-4eaa-8037-40f86f3d4471`.

Os numeros atendem binarios diferentes, com a mesma base de codigo nessas
atualizacoes. Isso nao comprova qual OTA cada aparelho baixou. Manter a mesma
revisao de codigo para os runtimes compativeis e registrar os grupos no release.

Mudancas do app candidatas a OTA; preservar motivo e renumerar tambem exigem
publicar o backend. Nenhum build de loja, OTA, merge ou deploy foi executado.
