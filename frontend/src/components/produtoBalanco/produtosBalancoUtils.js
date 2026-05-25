export const parseNumeroBR = (valor) => {
  if (valor === null || valor === undefined) return Number.NaN;
  if (typeof valor === "number") return Number.isFinite(valor) ? valor : Number.NaN;

  const texto = String(valor).trim();
  if (!texto) return Number.NaN;

  const normalizado = texto.includes(",")
    ? texto.replaceAll(".", "").replace(",", ".")
    : texto;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : Number.NaN;
};

export const formatQtd = (valor) => {
  const numero = parseNumeroBR(valor ?? 0);
  const valorSeguro = Number.isFinite(numero) ? numero : 0;
  return valorSeguro.toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
};

export const montarMovimentoBalanco = (
  produto,
  saldoFinal,
  { numeroLote = "", dataValidade = "" } = {}
) => {
  const estoqueAtual = parseNumeroBR(produto?.estoque_atual ?? 0);
  if (!Number.isFinite(estoqueAtual)) {
    return { erro: "Estoque atual invalido." };
  }

  if (!Number.isFinite(saldoFinal) || saldoFinal < 0) {
    return { erro: "Informe um numero valido." };
  }

  const diferenca = saldoFinal - estoqueAtual;
  if (Math.abs(diferenca) < 0.0001) {
    return { semAlteracao: true, diferenca: 0, estoqueAtual };
  }

  const quantidade = Math.abs(diferenca);
  if (!Number.isFinite(quantidade) || quantidade <= 0) {
    return { erro: "Quantidade calculada invalida." };
  }

  const endpoint = diferenca > 0 ? "/estoque/entrada" : "/estoque/saida";
  const payload = {
    produto_id: produto.id,
    quantidade,
    motivo: "balanco",
    observacao: `Balanco rapido: estoque ajustado para ${saldoFinal}`,
  };

  if (diferenca > 0) {
    const lote = String(numeroLote || "").trim();
    const validade = String(dataValidade || "").trim();
    if (lote) payload.numero_lote = lote;
    if (validade) payload.data_validade = validade;
  }

  return { endpoint, payload, diferenca, estoqueAtual };
};
