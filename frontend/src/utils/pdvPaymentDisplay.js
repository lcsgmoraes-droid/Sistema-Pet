const ROTULOS_FORMA_PAGAMENTO = {
  boleto: "Boleto",
  cartao: "Cartão",
  cartao_credito: "Cartão de crédito",
  cartao_debito: "Cartão de débito",
  cashback: "Cashback",
  crediario: "Crediário",
  credito: "Cartão de crédito",
  debito: "Cartão de débito",
  dinheiro: "Dinheiro",
  pix: "Pix",
};

function normalizarChave(valor) {
  return String(valor || "")
    .trim()
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replaceAll(/[^a-z0-9]+/g, "_")
    .replaceAll(/^_+|_+$/g, "");
}

function capitalizarTexto(valor) {
  const texto = String(valor || "")
    .trim()
    .replaceAll(/[_-]+/g, " ")
    .replaceAll(/\s+/g, " ");
  if (!texto) return "Pagamento";
  return texto.charAt(0).toLocaleUpperCase("pt-BR") + texto.slice(1);
}

export function rotuloFormaPagamento(pagamento = {}) {
  const forma =
    pagamento.forma_pagamento ||
    pagamento.nome ||
    pagamento.forma_pagamento_tipo ||
    pagamento.tipo ||
    "";
  let chave = normalizarChave(forma);

  if (chave === "cartao") {
    const modalidade = normalizarChave(pagamento.modalidade_cartao);
    if (modalidade === "credito" || modalidade === "debito") {
      chave = `cartao_${modalidade}`;
    }
  }

  return ROTULOS_FORMA_PAGAMENTO[chave] || capitalizarTexto(forma);
}

export function descricaoFormaPagamento(pagamento = {}) {
  const rotulo = rotuloFormaPagamento(pagamento);
  const parcelas = Math.trunc(Number(pagamento.numero_parcelas || pagamento.parcelas || 0));
  return parcelas > 1 ? `${rotulo} · ${parcelas}x` : rotulo;
}
