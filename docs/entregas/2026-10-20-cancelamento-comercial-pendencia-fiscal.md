# Cancelamento comercial com pendência fiscal

Data: 2026-10-20.
Responsáveis: Lucas / Codex.
Autorização: Lucas solicitou a correção, publicação em produção e cancelamento
da venda vinculada à NFC-e 18574 da Tecno Agropet.

## Problema e comportamento esperado

A IntNFe registrou a tentativa de cancelamento da NFC-e 18574, série 2,
como recusada (`autorizado=false`, código `501`, sem protocolo), por prazo
superior a 30 minutos. A nota permanece autorizada. A interface deve exibir
a recusa e seu motivo, sem apresentar sucesso ou andamento para esse caso.

O cancelamento comercial passa a estornar estoque, recebimentos internos,
caixa e demais efeitos usando o serviço transacional existente, mesmo quando
a situação fiscal ainda não permite confirmar o cancelamento da nota.
A venda fica `cancelada`; número, XML, chave, protocolo e situação fiscal
permanecem preservados.

O pedido fiscal possui estado próprio: `pendente`, `solicitado`, `recusado`
ou `confirmado`, acompanhado de código, motivo e data de solicitação.
Uma venda cancelada com documento ainda ativo mostra **Nota a cancelar**;
um pedido aceito e ainda não confirmado mostra **Cancelamento da nota em andamento**.
A confirmação fiscal posterior encerra a pendência sem repetir os estornos
nem reativar a venda. Nenhum novo documento pode ser emitido para uma venda
cancelada.

## Limite fiscal do caso concreto

Recusa por prazo não é processamento demorado. Para a hipótese de operação
não realizada e cancelamento fora do prazo, a SEFAZ/PR orienta emitir NF-e
de estorno, finalidade de ajuste, referenciando o documento original
([SAC, pergunta 1485](https://atendimento.fazenda.pr.gov.br/sacsefa/portal/assuntosReferente/22)).
Lucas confirmou que a mercadoria não saiu e a venda não aconteceu.
Cancelar a venda no ERP não cancela o documento
perante a SEFAZ nem realiza reembolso no adquirente do cartão.

## Escopo e validação

Sem mudanças do catálogo iFood ou da tarefa de consultas sobre DRE histórica.
Nenhum dado de desenvolvimento é transferido para produção.

Passaram 264 testes focados de backend (emissão, cancelamento, concorrência,
estoque/financeiro reais em SQLite, isolamento por tenant, listagem e XML),
33 testes de lógica do frontend e 6 testes de navegador com APIs simuladas.
ESLint, formatação e build de produção do frontend passaram.

A migration `zzzzl20261020a1` adiciona quatro campos nullable sem alterar dados
de vendas/notas existentes. Upgrade e downgrade foram testados preservando
os estados comercial e fiscal.

O gate completo, PR, commit publicado, health, backup e resultado da operação
serão conferidos pelo fluxo oficial. As evidências operacionais locais ficam
em `runtime/validacoes/`, sem segredos nem artefatos de execução no Git.
