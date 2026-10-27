import { obterCodigoPessoaPublico } from "../../utils/codigosPublicos.js";
import { formatMoneyBRL } from "../../utils/formatters.js";
import {
  camposDetalhesHistorico,
  formatarDataHistorico,
  obterStatusHistorico,
} from "../../utils/historicoFinanceiro.js";

const statusLabels = {
  aberta: "Em aberto",
  em_aberto: "Em aberto",
  baixa_parcial: "Parcial",
  parcial: "Parcial",
  pago: "Pago",
  recebido: "Pago / recebido",
  finalizada: "Pagamento não informado",
  cancelado: "Cancelada",
  cancelada: "Cancelada",
  devolvida: "Devolvida",
  efetivado: "Recebido",
  estornado: "Estornado",
};

const tipoLabels = {
  venda: "Vendas",
  devolucao: "Devoluções",
  conta_receber: "Contas a receber",
  recebimento: "Recebimentos",
  credito: "Créditos",
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

export async function gerarPdfComprasCliente(dados) {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF({ unit: "mm", format: "a4" });
  return preencherPdfComprasCliente(pdf, dados);
}

export function preencherPdfComprasCliente(
  pdf,
  { cliente, filtros, transacoes, geradoEm = new Date() },
) {
  const margem = 16;
  const largura = 178;
  const limite = 278;
  let y = 18;

  const escrever = (texto, tamanho = 9, negrito = false, espaco = 5) => {
    pdf.setFont("helvetica", negrito ? "bold" : "normal");
    pdf.setFontSize(tamanho);
    const linhas = pdf.splitTextToSize(String(texto), largura);
    for (const linha of linhas) {
      if (y + espaco > limite) {
        pdf.addPage();
        y = 18;
      }
      pdf.text(linha, margem, y);
      y += espaco;
    }
  };

  pdf.setTextColor(26, 45, 73);
  escrever("CorePet | Histórico financeiro", 16, true, 8);
  pdf.setTextColor(40, 50, 65);
  escrever(
    `Cliente: ${cliente?.nome || "Cliente"}${cliente?.codigo ? ` (${cliente.codigo})` : ""}`,
  );
  escrever(
    `Período: ${filtros.data_inicio ? formatarDataHistorico(filtros.data_inicio) : "sem data inicial"} a ${
      filtros.data_fim ? formatarDataHistorico(filtros.data_fim) : "sem data final"
    }`,
  );
  escrever(
    `Tipo: ${tipoLabels[filtros.tipo] || "Todas as transações"} | Status: ${statusLabels[filtros.status] || "Todos"}`,
  );
  escrever(`Gerado em: ${formatarDataHistorico(geradoEm, { comHora: true })}`, 8);
  y += 5;

  escrever(`${transacoes.length} transação(ões) no período`, 11, true, 7);
  for (const [tipo, label] of Object.entries(tipoLabels)) {
    const movimentos = transacoes.filter((transacao) => transacao.tipo === tipo);
    if (!movimentos.length) continue;
    const total = movimentos.reduce((soma, transacao) => soma + Number(transacao.valor || 0), 0);
    escrever(`${label}: ${formatMoneyBRL(total)}`, 9);
  }
  if (["aberta", "em_aberto", "parcial"].includes(filtros.status)) {
    escrever("Valores das vendas; o saldo devedor atualizado pode ser diferente.", 8);
  }
  y += 2;

  for (const transacao of transacoes) {
    const numero = transacao.detalhes?.numero_venda;
    const referencia = ["venda", "devolucao"].includes(transacao.tipo)
      ? `${transacao.tipo === "devolucao" ? "Devolução" : "Venda"}${numero ? ` #${numero}` : ""}`
      : transacao.descricao || tipoLabels[transacao.tipo] || "Movimento";
    const titulo = `${formatarDataHistorico(transacao.data)}  |  ${referencia}`;
    const valor = formatMoneyBRL(transacao.valor);
    const status = obterStatusHistorico(transacao).label;
    const tituloLinhas = pdf.splitTextToSize(titulo, largura);
    if (y + tituloLinhas.length * 5 + 10 > limite) {
      pdf.addPage();
      y = 18;
    }
    pdf.setDrawColor(220, 226, 234);
    pdf.line(margem, y - 4, margem + largura, y - 4);
    escrever(titulo, 10, true);
    escrever(`Valor: ${valor}    Status: ${status}`);
    for (const campo of camposDetalhesHistorico(transacao)) {
      escrever(`${campo.label}: ${campo.valor}`, 8);
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

  const codigo = String(obterCodigoPessoaPublico(cliente) || "cliente").replace(
    /[^a-zA-Z0-9-]/g,
    "",
  );
  pdf.save(`corepet-compras-${codigo}-${formatarDataHistorico(geradoEm)}.pdf`);
  return pdf;
}
