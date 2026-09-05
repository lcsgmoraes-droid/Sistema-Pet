export function dataRecebimentoBR(data) {
  return String(data || "")
    .slice(0, 10)
    .split("-")
    .reverse()
    .join("/");
}

export function planilhasRecebimentos(relatorio, canalLabel) {
  const { resumo, movimentos, data_inicio, data_fim } = relatorio;
  return [
    {
      sheet: "Resumo",
      linhas: [
        ["Recebimentos de vendas — pela data do recebimento"],
        ["Início", dataRecebimentoBR(data_inicio)],
        ["Fim", dataRecebimentoBR(data_fim)],
        ["Canal", canalLabel],
        ["Recebimentos", resumo.recebimentos],
        ["Devoluções em dinheiro", resumo.devolucoes],
        ["Total no período", resumo.total],
      ],
    },
    {
      sheet: "Recebimentos",
      linhas: [
        ["Recebimento", "Venda", "Data da venda", "Cliente", "Forma", "Movimento", "Valor"],
        ...movimentos.map((m) => [
          dataRecebimentoBR(m.data_recebimento),
          m.numero_venda,
          dataRecebimentoBR(m.data_venda),
          m.cliente_nome,
          m.forma_pagamento,
          m.tipo === "devolucao" ? "Devolução" : "Recebimento",
          m.valor,
        ]),
      ],
    },
  ];
}
