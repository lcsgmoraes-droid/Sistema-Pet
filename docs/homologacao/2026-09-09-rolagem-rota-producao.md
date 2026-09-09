# Reteste da rolagem no binario de producao

Lucas informou que a rota continuou sem rolar depois de abrir e fechar o app
quatro vezes. O reteste por USB usou o Samsung SM-S938B, CorePet 1.0.4 (15),
conta demo e rota ficticia 600, com 67 paradas.

## Evidencia observada

- O processo Android 29405 baixou a OTA `a3b277d6-5e63-46d1-966d-894d4287a677`
  em 09/09/2026, 11:13:23, mas permaneceu aberto entre as reaberturas da tela.
  A interface ainda mostrava a instrucao antiga, sem os novos rotulos de
  acessibilidade do arrasto.
- Depois de encerrar somente o processo CorePet e reabrir, o processo 3746
  mostrou o texto novo e os rotulos `Reordenar entrega N` da correcao.
- Mesmo com a OTA aplicada, deslizar sobre o endereco e sobre o cabecalho
  manteve as mesmas coordenadas das paradas 1, 2 e 3. A correcao anterior foi
  insuficiente no binario de producao. O aceite no Expo Go nao comprova esse
  comportamento, pois usou versoes diferentes de Reanimated/Worklets.

## Ajuste adicional

A lista continua unica e a ordem manual permanece disponivel. A distancia
de ativacao do arrasto passa de 4 para 24 pontos, permitindo que a rolagem
nativa reconheca o deslize antes do gesto de arrastar. O icone ainda exige
pressionar por 300 ms. Nao ha alteracao de dependencia, runtime ou binario.

A biblioteca aplica `activationDistance` ao `activeOffsetY` do gesto Pan
externo a lista; a alteracao deve ser confirmada com gestos no app instalado,
inclusive arrastar depois de pressionar o icone.

Referencia: [implementacao da biblioteca](https://github.com/computerjazz/react-native-draggable-flatlist/blob/main/src/components/DraggableFlatList.tsx).

## Validacao

TypeScript e os quatro testes existentes de componentes/callbacks passaram.
Esses testes nao executam gestos nativos. A confirmacao fisica do ajuste de
distancia esta pendente neste registro e sera guardada com as evidencias locais
em `runtime/qa-rolagem-entregador/`.

Nao foram alterados status, pagamentos ou pedidos durante este reteste.
