# Recorrência de produtos

## Objetivo

Lembrar o cliente de recomprar produtos, adquirir as próximas doses de um
protocolo e, quando configurado, iniciar um novo protocolo depois do término.

## Regras

- Um produto físico pode ter vários protocolos. Não é necessário duplicar o
  SKU ou o estoque para separar, por exemplo, vacina de filhote e de adulto.
- Composição de produto continua reservada a kits; ela não representa um
  protocolo de aplicação.
- A Dose 1 ocorre no dia 0, usando a data da venda como início.
- As demais doses guardam dias desde o início. Uma compra antecipada não move
  as próximas datas do protocolo.
- Depois da última dose, a configuração pode encerrar sem lembrete ou oferecer
  um novo protocolo após uma quantidade livre de dias.
- O protocolo é vinculado ao pet. Espécie e fase de vida ajudam o PDV a sugerir
  a opção, mas o operador pode confirmar ou alterar a escolha.
- O operador também pode escolher não iniciar a recorrência naquela venda; essa
  decisão fica gravada no item e não afeta vendas futuras.
- Recompras contínuas podem manter o intervalo configurado ou aprender o ciclo
  real do cliente quando houver histórico suficiente.

## Canais de notificação

O canal ativo nesta etapa é o aplicativo. A integração com WhatsApp permanece
em espera até o módulo estar operacional. Quando for ativada, os eventos
`recompra`, `proxima_dose` e `reinicio_protocolo` também deverão ser enviados
por WhatsApp, com consentimento do cliente, histórico do contato e chave de
idempotência para impedir mensagens duplicadas.
