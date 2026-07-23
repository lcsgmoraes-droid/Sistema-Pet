import { formatMoneyBRL } from "../../utils/formatters";

export function exportarRelatorioCsv(relatorio, dataInicio, dataFim) {
  const linhas = [
    ["Relatório Banho & Tosa", `${dataInicio} a ${dataFim}`],
    [],
    ["Resumo", "Valor"],
    ["Atendimentos", relatorio?.resumo?.atendimentos || 0],
    ["Agendamentos", relatorio?.resumo?.agendamentos || 0],
    ["Receita", numeroCsv(relatorio?.resumo?.receita)],
    ["Custo total", numeroCsv(relatorio?.resumo?.custo_total)],
    ["Margem", numeroCsv(relatorio?.resumo?.margem_valor)],
    ["Margem percentual", numeroCsv(relatorio?.resumo?.margem_percentual)],
    ["Ticket médio", numeroCsv(relatorio?.resumo?.ticket_medio)],
    [],
    ["Margem por serviço"],
    ["Serviço", "Atendimentos", "Receita", "Custo", "Margem", "Margem %"],
    ...(relatorio?.margem_por_servico || []).map((item) => [
      item.nome,
      item.atendimentos,
      numeroCsv(item.receita),
      numeroCsv(item.custo_total),
      numeroCsv(item.margem_valor),
      numeroCsv(item.margem_percentual),
    ]),
    [],
    ["Produtividade"],
    ["Responsável", "Atendimentos", "Etapas", "Minutos"],
    ...(relatorio?.produtividade || []).map((item) => [
      item.responsavel_nome,
      item.atendimentos,
      item.etapas,
      item.minutos_trabalhados,
    ]),
    [],
    ["Desperdício"],
    ["Produto", "Quantidade", "Custo"],
    ...(relatorio?.desperdicios || []).map((item) => [
      item.produto_nome,
      numeroCsv(item.quantidade_desperdicio),
      numeroCsv(item.custo_desperdicio),
    ]),
  ];
  const csv = linhas.map((linha) => linha.map(escaparCsv).join(";")).join("\r\n");
  baixarBlob(
    new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" }),
    nomeArquivo("csv", dataInicio, dataFim),
  );
}

export async function exportarRelatorioPdf(relatorio, dataInicio, dataFim) {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ format: "a4", unit: "mm" });
  const margem = 14;
  const largura = 182;
  let y = 16;

  function garantirEspaco(altura = 12) {
    if (y + altura <= 282) return;
    doc.addPage();
    y = 16;
  }

  function titulo(texto) {
    garantirEspaco(14);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text(texto, margem, y);
    y += 7;
  }

  function linha(texto, valor = "") {
    const textoLinhas = doc.splitTextToSize(String(texto), valor !== "" ? 132 : largura);
    garantirEspaco(Math.max(textoLinhas.length, 1) * 5.5);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.text(textoLinhas, margem, y);
    if (valor !== "") {
      doc.text(String(valor), margem + largura, y, { align: "right" });
    }
    y += Math.max(textoLinhas.length, 1) * 5.5;
  }

  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("CorePet - Relatório Banho & Tosa", margem, y);
  y += 8;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(`Período: ${dataInicio} a ${dataFim}`, margem, y);
  y += 10;

  const resumo = relatorio?.resumo || {};
  titulo("Resumo");
  linha("Atendimentos", resumo.atendimentos || 0);
  linha("Receita", formatMoneyBRL(resumo.receita));
  linha("Custo total", formatMoneyBRL(resumo.custo_total));
  linha(
    "Margem",
    `${formatMoneyBRL(resumo.margem_valor)} (${formatarNumero(resumo.margem_percentual)}%)`,
  );
  linha("Ticket médio", formatMoneyBRL(resumo.ticket_medio));
  linha("Ocupação média", `${formatarNumero(resumo.ocupacao_media_percentual)}%`);
  linha("NPS", formatarNumero(resumo.nps, 0));
  y += 4;

  titulo("Margem por serviço");
  const servicos = (relatorio?.margem_por_servico || []).slice(0, 12);
  if (!servicos.length) linha("Sem dados no período");
  servicos.forEach((item) =>
    linha(
      `${item.nome} - ${item.atendimentos} atend.`,
      `${formatMoneyBRL(item.margem_valor)} - ${formatarNumero(item.margem_percentual)}%`,
    ),
  );
  y += 4;

  titulo("Produtividade");
  const produtividade = (relatorio?.produtividade || []).slice(0, 12);
  if (!produtividade.length) linha("Sem dados no período");
  produtividade.forEach((item) =>
    linha(`${item.responsavel_nome} - ${item.etapas} etapas`, `${item.minutos_trabalhados} min`),
  );
  y += 4;

  titulo("Desperdício de insumos");
  const desperdicios = (relatorio?.desperdicios || []).slice(0, 12);
  if (!desperdicios.length) linha("Sem desperdício registrado");
  desperdicios.forEach((item) =>
    linha(
      `${item.produto_nome} - ${formatarNumero(item.quantidade_desperdicio, 3)} ${item.unidade || ""}`,
      formatMoneyBRL(item.custo_desperdicio),
    ),
  );

  if (relatorio?.alertas?.length) {
    y += 5;
    titulo("Alertas");
    relatorio.alertas.forEach((alerta) => {
      const linhasAlerta = doc.splitTextToSize(`- ${alerta}`, largura);
      garantirEspaco(linhasAlerta.length * 5);
      doc.text(linhasAlerta, margem, y);
      y += linhasAlerta.length * 5;
    });
  }

  doc.save(nomeArquivo("pdf", dataInicio, dataFim));
}

function nomeArquivo(extensao, dataInicio, dataFim) {
  return `corepet-banho-tosa-${dataInicio}-a-${dataFim}.${extensao}`;
}

function numeroCsv(valor) {
  return Number(valor || 0)
    .toFixed(4)
    .replace(".", ",");
}

function formatarNumero(valor, casas = 1) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function escaparCsv(valor) {
  const texto = String(valor ?? "");
  return `"${texto.replaceAll('"', '""')}"`;
}

function baixarBlob(blob, nome) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
