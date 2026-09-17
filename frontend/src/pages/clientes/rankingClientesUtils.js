export function dataParaInput(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function obterPeriodoRanking(tipo, referencia = new Date()) {
  const hoje = new Date(referencia.getFullYear(), referencia.getMonth(), referencia.getDate(), 12);
  let inicio = new Date(hoje);
  let fim = new Date(hoje);

  if (tipo === "7_dias") inicio.setDate(inicio.getDate() - 6);
  if (tipo === "30_dias") inicio.setDate(inicio.getDate() - 29);
  if (tipo === "mes_atual") inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1, 12);
  if (tipo === "mes_anterior") {
    inicio = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1, 12);
    fim = new Date(hoje.getFullYear(), hoje.getMonth(), 0, 12);
  }
  if (tipo === "ano_atual") inicio = new Date(hoje.getFullYear(), 0, 1, 12);

  return {
    data_inicio: dataParaInput(inicio),
    data_fim: dataParaInput(fim),
  };
}

export const METRICAS_RANKING = {
  total_gasto: {
    label: "Maior faturamento",
    coluna: "Total gasto",
  },
  total_compras: {
    label: "Mais compras",
    coluna: "Compras",
  },
  total_itens: {
    label: "Mais itens",
    coluna: "Itens",
  },
  ticket_medio: {
    label: "Maior ticket médio",
    coluna: "Ticket médio",
  },
  ultima_compra: {
    label: "Compra mais recente",
    coluna: "Última compra",
  },
};
