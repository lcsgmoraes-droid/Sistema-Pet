# Acompanhamento: situação das devoluções legadas

Identificado em 27/10/2026 durante a revisão do histórico financeiro.

**Estado: pendente de revisão dedicada.** Este acompanhamento fica separado da
correção de observações, datas, recebimentos e filtros do histórico de baixas.

O fluxo de devolução grava os estados operacionais `devolvida_total` e
`finalizada_devolucao` em `backend/app/vendas/devolucoes_routes.py`. A devolução
total dos itens preserva o frete: esse estado, isoladamente, não comprova que o
valor financeiro integral da venda deva ser cancelado ou invertido.

As consultas e rótulos de histórico ainda precisam de uma análise específica da
combinação desses estados com pagamentos, restituições e frete. Antes de mudar
a classificação ou o sinal dos valores, a revisão deve definir e testar:

- Devolução parcial e devolução total dos itens, com e sem frete retido.
- Pagamentos e restituições integrais ou parciais, preservando os movimentos.
- Situação financeira exibida e filtrada, sem sugerir dívida inexistente.
- Valores e sinais apresentados, sem inverter o frete que permanece devido ou
  já foi recebido.

Nenhuma regra, tipo de movimento, saldo, valor ou registro de devolução foi
alterado nesta entrega em razão deste acompanhamento.
