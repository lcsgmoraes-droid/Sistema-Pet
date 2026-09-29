import { formatMoneyBRL } from "../../utils/formatters.js";

const statusLabels = {
  aberta: "Em aberto",
  baixa_parcial: "Pagamento parcial",
  finalizada: "Finalizada (paga)",
  cancelada: "Cancelada",
  devolvida: "Devolvida",
};

const tipoLabels = {
  venda: "Vendas",
  devolucao: "Devoluções",
};

const formatarData = (valor) => {
  const data = String(valor || "").slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(data)
    ? `${data.slice(8, 10)}/${data.slice(5, 7)}/${data.slice(0, 4)}`
    : "-";
};

export async function buscarTransacoesParaPdf(api, clienteId, filtros) {
  const params = new URLSearchParams({ page: "1", per_page: "100" });
  for (const campo of ["data_inicio", "data_fim", "tipo", "status"]) {
    if (filtros[campo]) params.set(campo, filtros[campo]);
  }

  const transacoes = [];
  let pagina = 1;
  let totalPaginas;
  do {
    params.set("page", String(pagina));
    const response = await api.get(`/financeiro/cliente/${clienteId}?${params.toString()}`);
    transacoes.push(...(response.data.historico || []));
    totalPaginas = response.data.paginacao?.total_paginas || 1;
    pagina += 1;
  } while (pagina <= totalPaginas);

  return transacoes;
}

export async function gerarPdfComprasCliente({ cliente, filtros, transacoes }) {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF({ unit: "mm", format: "a4" });
  const margem = 16;
  const largura = 178;
  const limite = 278;
  let y = 18;

  const escrever = (texto, tamanho = 9, negrito = false, espaco = 5) => {
    pdf.setFont("helvetica", negrito ? "bold" : "normal");
    pdf.setFontSize(tamanho);
    const linhas = pdf.splitTextToSize(String(texto), largura);
    const altura = linhas.length * espaco;
    if (y + altura > limite) {
      pdf.addPage();
      y = 18;
    }
    pdf.text(linhas, margem, y);
    y += altura;
  };

  pdf.setTextColor(26, 45, 73);
  escrever("CorePet | Histórico de compras", 16, true, 8);
  pdf.setTextColor(40, 50, 65);
  escrever(
    `Cliente: ${cliente?.nome || "Cliente"}${cliente?.codigo ? ` (${cliente.codigo})` : ""}`,
  );
  escrever(
    `Período: ${filtros.data_inicio ? formatarData(filtros.data_inicio) : "sem data inicial"} a ${
      filtros.data_fim ? formatarData(filtros.data_fim) : "sem data final"
    }`,
  );
  escrever(
    `Tipo: ${tipoLabels[filtros.tipo] || "Todas as transações"} | Status: ${statusLabels[filtros.status] || "Todos"}`,
  );
  escrever(`Gerado em: ${new Date().toLocaleString("pt-BR")}`, 8);
  y += 5;

  const total = transacoes.reduce((soma, transacao) => soma + Number(transacao.valor || 0), 0);
  escrever(
    `${transacoes.length} transação(ões) | Total do período: ${formatMoneyBRL(total)}`,
    11,
    true,
    7,
  );
  if (filtros.status === "aberta") {
    escrever("Valores das vendas; o saldo devedor atualizado pode ser diferente.", 8);
  }
  y += 2;

  for (const transacao of transacoes) {
    const numero = transacao.detalhes?.numero_venda || transacao.detalhes?.venda_id || "-";
    const titulo = `${formatarData(transacao.data)}  |  ${transacao.tipo === "devolucao" ? "Devolução" : "Venda"} #${numero}`;
    const valor = formatMoneyBRL(transacao.valor);
    const status = statusLabels[transacao.status] || transacao.status || "-";
    const tituloLinhas = pdf.splitTextToSize(titulo, largura);
    if (y + tituloLinhas.length * 5 + 10 > limite) {
      pdf.addPage();
      y = 18;
    }
    pdf.setDrawColor(220, 226, 234);
    pdf.line(margem, y - 4, margem + largura, y - 4);
    escrever(titulo, 10, true);
    escrever(`Valor: ${valor}    Status: ${status}`);
    if (Number(transacao.detalhes?.desconto) > 0) {
      escrever(`Desconto: ${formatMoneyBRL(transacao.detalhes.desconto)}`, 8);
    }
    y += 3;
  }

  const totalPaginas = pdf.internal.getNumberOfPages();
  for (let pagina = 1; pagina <= totalPaginas; pagina += 1) {
    pdf.setPage(pagina);
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(8);
    pdf.setTextColor(100, 110, 125);
    pdf.text(`Página ${pagina} de ${totalPaginas}`, margem + largura, 287, { align: "right" });
  }

  const codigo = String(cliente?.codigo || cliente?.id || "cliente").replace(/[^a-zA-Z0-9-]/g, "");
  pdf.save(`corepet-compras-${codigo}-${new Date().toISOString().slice(0, 10)}.pdf`);
}
