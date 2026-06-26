function numeroSeguro(valor) {
  const numero = Number(valor || 0);
  return Number.isFinite(numero) ? numero : 0;
}

export const CANAIS_DESTAQUE = ["loja_fisica", "mercado_livre", "shopee", "amazon"];

export const LABELS_CANAIS = {
  loja_fisica: "Loja FÃ­sica",
  mercado_livre: "Mercado Livre",
  shopee: "Shopee",
  amazon: "Amazon",
  site: "Site",
  instagram: "Instagram",
  whatsapp: "WhatsApp",
};

export const ESTILOS_CANAIS = {
  loja_fisica: {
    card: "bg-emerald-50 border-emerald-200 text-emerald-700",
    bar: "bg-emerald-400",
  },
  mercado_livre: {
    card: "bg-yellow-50 border-yellow-200 text-yellow-700",
    bar: "bg-yellow-400",
  },
  shopee: {
    card: "bg-orange-50 border-orange-200 text-orange-700",
    bar: "bg-orange-400",
  },
  amazon: {
    card: "bg-sky-50 border-sky-200 text-sky-700",
    bar: "bg-sky-400",
  },
  site: {
    card: "bg-indigo-50 border-indigo-200 text-indigo-700",
    bar: "bg-indigo-400",
  },
  instagram: {
    card: "bg-pink-50 border-pink-200 text-pink-700",
    bar: "bg-pink-400",
  },
  whatsapp: {
    card: "bg-green-50 border-green-200 text-green-700",
    bar: "bg-green-400",
  },
};

export function formatarQuantidadeMovimentacao(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function parseNumeroInputMovimentacao(valor) {
  if (valor === null || valor === undefined || valor === "") return 0;
  if (typeof valor === "number") return Number.isFinite(valor) ? valor : 0;

  const texto = String(valor).trim();
  const normalizado = texto.includes(",") ? texto.replace(/\./g, "").replace(",", ".") : texto;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : 0;
}

export function dataAtualIsoLocalMovimentacao() {
  const agora = new Date();
  const local = new Date(agora.getTime() - agora.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

export function extrairMensagemErroApiMovimentacao(error, fallback) {
  const detalhe = error?.response?.data?.detail ?? error?.response?.data?.message;
  if (typeof detalhe === "string") return detalhe;
  if (detalhe && typeof detalhe === "object") {
    return detalhe.message || detalhe.mensagem || fallback;
  }
  return error?.message || fallback;
}

export function getSaldoAposLancamento(movimentacao) {
  const saldo = movimentacao?.saldo_apos_lancamento ?? movimentacao?.quantidade_nova;
  const saldoNumerico = Number(saldo);
  return Number.isFinite(saldoNumerico) ? saldoNumerico : null;
}

export function produtoUsaEstoqueVirtual(produto) {
  return (
    (produto?.tipo_produto === "KIT" || produto?.tipo_produto === "VARIACAO") &&
    produto?.tipo_kit === "VIRTUAL"
  );
}

export function resolverEstoqueAtualMovimentacoes(produto) {
  if (produtoUsaEstoqueVirtual(produto)) {
    return numeroSeguro(produto?.estoque_virtual ?? produto?.estoque_disponivel);
  }

  return numeroSeguro(produto?.estoque_atual);
}

export function resolverSaldoDisponivelMovimentacoes(produto) {
  if (produtoUsaEstoqueVirtual(produto)) {
    return numeroSeguro(produto?.estoque_disponivel ?? produto?.estoque_virtual);
  }

  const estoqueAtual = resolverEstoqueAtualMovimentacoes(produto);
  const estoqueReservado = numeroSeguro(produto?.estoque_reservado);
  return estoqueAtual - estoqueReservado;
}
