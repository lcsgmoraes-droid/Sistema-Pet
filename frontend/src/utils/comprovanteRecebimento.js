import { formatMoneyBRL } from "./formatters.js";

const LARGURA = 42;

function ascii(texto) {
  return String(texto || "")
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "")
    .replaceAll(/[^\x20-\x7E]/g, " ")
    .replaceAll(/\s+/g, " ")
    .trim();
}

function centralizar(texto) {
  const valor = ascii(texto).slice(0, LARGURA);
  const espacos = Math.max(0, LARGURA - valor.length);
  return `${" ".repeat(Math.floor(espacos / 2))}${valor}`;
}

function quebrar(texto) {
  const palavras = ascii(texto).split(" ");
  const linhas = [];
  let atual = "";
  for (const palavra of palavras) {
    const proxima = atual ? `${atual} ${palavra}` : palavra;
    if (proxima.length <= LARGURA) atual = proxima;
    else {
      if (atual) linhas.push(atual);
      atual = palavra;
    }
  }
  if (atual) linhas.push(atual);
  return linhas;
}

export function formatarDataComprovante(data) {
  if (!data) return "Nao informada";
  const parteData = String(data).split("T")[0];
  const [ano, mes, dia] = parteData.split("-").map(Number);
  if (!ano || !mes || !dia) return ascii(data);
  return `${String(dia).padStart(2, "0")}/${String(mes).padStart(2, "0")}/${ano}`;
}

export function montarDadosComprovanteRecebimento({
  conta,
  detalhes,
  formasPagamento = [],
  recebimento,
  saldoRestante,
}) {
  const formaPagamentoId = recebimento?.forma_pagamento_id;
  const formaPagamento =
    recebimento?.forma_pagamento_nome ||
    formasPagamento.find((forma) => Number(forma.id) === Number(formaPagamentoId))?.nome ||
    "Nao informada";

  return {
    id: recebimento?.id,
    contaId: conta?.id || detalhes?.id,
    descricao: conta?.descricao || detalhes?.descricao || "Conta a receber",
    clienteNome: detalhes?.cliente?.nome || conta?.cliente_nome || "Nao informado",
    documento: detalhes?.documento || conta?.documento || null,
    numeroVenda: detalhes?.venda?.numero_venda || conta?.numero_venda || null,
    valor: Number(recebimento?.valor ?? recebimento?.valor_recebido ?? 0),
    data: recebimento?.data || recebimento?.data_recebimento,
    formaPagamento,
    contaBancaria: recebimento?.conta_bancaria_nome || null,
    observacoes: recebimento?.observacoes || null,
    saldoRestante:
      saldoRestante == null
        ? Number(detalhes?.valores?.saldo ?? 0)
        : Math.max(0, Number(saldoRestante)),
  };
}

export function montarTextoComprovanteRecebimento(comprovante) {
  const separador = "-".repeat(LARGURA);
  const numero = comprovante?.id
    ? `CR-${comprovante.contaId || "0"}-R-${comprovante.id}`
    : `CR-${comprovante?.contaId || "-"}`;
  const linhas = [
    centralizar("PET SHOP PRO"),
    centralizar("COMPROVANTE DE RECEBIMENTO"),
    separador,
    `Comprovante: ${ascii(numero)}`,
    `Data: ${formatarDataComprovante(comprovante?.data)}`,
    ...quebrar(`Cliente: ${comprovante?.clienteNome || "Nao informado"}`),
    ...quebrar(`Conta: ${comprovante?.descricao || "Conta a receber"}`),
  ];

  if (comprovante?.numeroVenda) linhas.push(`Venda: ${ascii(comprovante.numeroVenda)}`);
  if (comprovante?.documento) linhas.push(`Documento: ${ascii(comprovante.documento)}`);
  linhas.push(separador, `Forma: ${ascii(comprovante?.formaPagamento || "Nao informada")}`);
  if (comprovante?.contaBancaria) {
    linhas.push(...quebrar(`Conta bancaria: ${comprovante.contaBancaria}`));
  }
  linhas.push(
    centralizar("VALOR RECEBIDO"),
    centralizar(formatMoneyBRL(comprovante?.valor || 0)),
    `Saldo atual da conta: ${formatMoneyBRL(comprovante?.saldoRestante || 0)}`,
    separador,
  );
  if (comprovante?.observacoes) {
    linhas.push(...quebrar(`Observacoes: ${comprovante.observacoes}`), separador);
  }
  linhas.push(centralizar("Recebimento registrado no sistema"));
  return linhas.join("\n");
}
