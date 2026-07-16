# Recorrencia Inteligente de Produtos

Atualizado em: 2026-07-16

## Regra de negocio

- Produtos com protocolo e numero de doses usam o intervalo fixo cadastrado e
  permanecem vinculados ao pet.
- Produtos de reposicao, como racao, usam o intervalo cadastrado como ponto de
  partida e passam a usar o comportamento real do cliente quando ha historico
  consistente.
- Mesmo sem configuracao manual, o sistema pode descobrir uma recorrencia apos
  pelo menos tres compras em intervalos consistentes.
- Compras sem pet, comuns no app e no ecommerce, tambem participam do
  aprendizado.
- Historico instavel nao gera previsao automatica sem um intervalo configurado.

## Notificacao

- O canal desta rotina e exclusivamente o app.
- A antecedencia varia conforme o ciclo e fica limitada a sete dias.
- Cada lembrete possui uma chave unica, impedindo o mesmo aviso de entrar duas
  vezes na fila.
- Ao tocar na notificacao, o cliente abre diretamente o produto no app.
- Preferencias de privacidade para marketing push continuam respeitadas.

## Auditoria

Cada lembrete registra se o intervalo foi `configurado` ou `aprendido`, o
intervalo estimado, a confianca e a quantidade de compras analisadas. Assim, a
loja consegue diferenciar um protocolo fixo de uma previsao de consumo.

## Evidencia de producao usada na validacao

Em consulta somente leitura, a venda `202607010031` foi confirmada como canal
`app` e status `finalizada`. O item era uma racao de 3 kg, sem pet e sem
recorrencia manual configurada — um caso que o fluxo antigo ignorava e que passa
a alimentar o aprendizado com esta melhoria.
