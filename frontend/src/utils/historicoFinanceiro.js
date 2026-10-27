import { formatMoneyBRL } from "./formatters.js";

const normalizar = (valor) =>
  String(valor || "")
    .trim()
    .toLowerCase()
    .replace(/[ -]+/g, "_");
const estado = (codigo, label, tom) => ({ codigo, label, tom });
const estadosVenda = {
  pago: estado("pago", "Pago", "sucesso"),
  parcial: estado("parcial", "Parcial", "atencao"),
  em_aberto: estado("em_aberto", "Em aberto", "atencao"),
  cancelado: estado("cancelado", "Cancelada", "perigo"),
  desconhecido: estado("desconhecido", "Pagamento não informado", "neutro"),
};
const codigoPagamento = (valor) => {
  const chave = normalizar(valor);
  if (["pago", "paga", "quitado", "quitada", "recebido"].includes(chave)) return "pago";
  if (["parcial", "baixa_parcial", "parcialmente_pago"].includes(chave)) return "parcial";
  if (["em_aberto", "aberto", "aberta", "pendente", "nao_pago"].includes(chave)) return "em_aberto";
  if (["cancelado", "cancelada", "devolvida"].includes(chave)) return "cancelado";
  return "desconhecido";
};

function estadoFinanceiroVenda(venda = {}) {
  if (!venda) return estadosVenda.desconhecido;
  if (codigoPagamento(venda.status_operacional || venda.status) === "cancelado") {
    return estadosVenda.cancelado;
  }
  const pagamento = venda.status_pagamento || venda.detalhes?.status_pagamento;
  // Finalização operacional sozinha não comprova recebimento do dinheiro.
  return estadosVenda[codigoPagamento(pagamento || venda.status)];
}

export function statusFinanceiroVenda(venda) {
  return estadoFinanceiroVenda(venda).label;
}

export function formatarFormaPagamentoHistorico(valor) {
  const texto = typeof valor === "string" ? valor.trim() : "";
  if (!texto) return "Não informado";
  const chave = normalizar(texto.normalize("NFD").replace(/[\u0300-\u036f]/g, ""));
  const aliases = {
    dinheiro: "Dinheiro",
    cash: "Dinheiro",
    pix: "Pix",
    credito: "Cartão de crédito",
    cartao_credito: "Cartão de crédito",
    cartao_de_credito: "Cartão de crédito",
    credit_card: "Cartão de crédito",
    debito: "Cartão de débito",
    cartao_debito: "Cartão de débito",
    cartao_de_debito: "Cartão de débito",
    debit_card: "Cartão de débito",
    boleto: "Boleto",
    crediario: "Crediário",
    a_prazo: "A prazo",
    transferencia: "Transferência bancária",
    transferencia_bancaria: "Transferência bancária",
    credito_loja: "Crédito em loja",
    link: "Link de pagamento",
    link_pagamento: "Link de pagamento",
    nao_informado: "Não informado",
  };
  return aliases[chave] || texto;
}

export function obterStatusHistorico(transacao = {}) {
  if (["venda", "devolucao"].includes(transacao.tipo)) return estadoFinanceiroVenda(transacao);
  const status = normalizar(transacao.detalhes?.status_recebimento || transacao.status);
  if (transacao.tipo === "recebimento") {
    return status === "estornado" || Number(transacao.valor) < 0
      ? estado("estornado", "Estornado", "perigo")
      : estado("recebido", "Recebido", "sucesso");
  }
  if (transacao.tipo === "credito") return estado("registrado", "Registrado", "neutro");
  if (["recebido", "pago", "paga", "quitado"].includes(status))
    return estado("recebido", "Recebido", "sucesso");
  if (status === "vencido") return estado("vencido", "Vencido", "perigo");
  const financeiro = codigoPagamento(status);
  if (financeiro !== "desconhecido") return estadosVenda[financeiro];
  return estado("desconhecido", "Não informado", "neutro");
}

function dataValida(ano, mes, dia) {
  const data = new Date(Date.UTC(Number(ano), Number(mes) - 1, Number(dia)));
  return (
    data.getUTCFullYear() === Number(ano) &&
    data.getUTCMonth() === Number(mes) - 1 &&
    data.getUTCDate() === Number(dia)
  );
}

export function formatarDataHistorico(valor, { comHora = false } = {}) {
  if (valor === null || valor === undefined || valor === "") return "—";
  const texto = String(valor).trim();
  const iso =
    /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$/.exec(
      texto,
    );
  if (
    iso &&
    (!dataValida(iso[1], iso[2], iso[3]) || Number(iso[4] || 0) > 23 || Number(iso[5] || 0) > 59)
  )
    return "—";
  if (valor instanceof Date || (iso && /(?:Z|[+-]\d{2}:?\d{2})$/.test(texto))) {
    const data = valor instanceof Date ? valor : new Date(texto.replace(" ", "T"));
    if (Number.isNaN(data.getTime())) return "—";
    const partes = Object.fromEntries(
      new Intl.DateTimeFormat("pt-BR", {
        timeZone: "America/Sao_Paulo",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        ...(comHora ? { hour: "2-digit", minute: "2-digit", hourCycle: "h23" } : {}),
      })
        .formatToParts(data)
        .map(({ type, value }) => [type, value]),
    );
    return `${partes.day}-${partes.month}-${partes.year}${comHora ? ` ${partes.hour}:${partes.minute}` : ""}`;
  }
  if (iso && dataValida(iso[1], iso[2], iso[3])) {
    return `${iso[3]}-${iso[2]}-${iso[1]}${comHora && iso[4] ? ` ${iso[4]}:${iso[5]}` : ""}`;
  }
  const local = /^(\d{2})[-/](\d{2})[-/](\d{4})$/.exec(texto);
  return local && dataValida(local[3], local[2], local[1])
    ? `${local[1]}-${local[2]}-${local[3]}`
    : "—";
}

const campos = {
  recebimento_id: ["Recebimento", "referencia"],
  conta_receber_id: ["Conta a receber", "referencia"],
  numero_venda: ["Venda", "referencia"],
  data_baixa: ["Data da baixa", "data"],
  data_vencimento: ["Vencimento", "data"],
  subtotal: ["Subtotal", "moeda"],
  desconto: ["Desconto", "moeda"],
  cupom_discount_applied: ["Desconto de cupom", "moeda"],
  total: ["Total", "moeda"],
  valor_recebido: ["Valor recebido", "moeda"],
  saldo: ["Saldo", "moeda"],
  saldo_anterior: ["Saldo anterior", "moeda"],
  saldo_atual: ["Saldo atual", "moeda"],
  forma_pagamento: ["Forma de pagamento", "texto"],
  canal: ["Canal", "texto"],
  usuario: ["Usuário", "texto"],
  tipo: ["Movimento", "texto"],
  caixa_nome: ["Caixa", "texto"],
  conta_bancaria_nome: ["Conta bancária", "texto"],
  observacoes: ["Observação", "observacao"],
};
const camposPorTipo = {
  recebimento: [
    "recebimento_id",
    "conta_receber_id",
    "numero_venda",
    "data_baixa",
    "forma_pagamento",
    "caixa_nome",
    "conta_bancaria_nome",
    "observacoes",
  ],
  conta_receber: [
    "conta_receber_id",
    "numero_venda",
    "data_vencimento",
    "valor_recebido",
    "saldo",
    "observacoes",
  ],
  credito: ["tipo", "saldo_anterior", "saldo_atual", "usuario", "observacoes"],
  venda: [
    "numero_venda",
    "subtotal",
    "desconto",
    "cupom_discount_applied",
    "total",
    "canal",
    "forma_pagamento",
    "observacoes",
  ],
};

export function camposDetalhesHistorico(transacao = {}) {
  const detalhes = { ...transacao.detalhes };
  if (transacao.tipo === "recebimento") detalhes.data_baixa ||= transacao.data;
  const chaves = camposPorTipo[transacao.tipo === "devolucao" ? "venda" : transacao.tipo] || [];
  return chaves.flatMap((chave) => {
    const valor = detalhes[chave];
    if (valor === null || valor === undefined || valor === "") return [];
    const [label, tipo] = campos[chave];
    const texto =
      tipo === "moeda"
        ? formatMoneyBRL(valor)
        : chave === "forma_pagamento"
          ? formatarFormaPagamentoHistorico(valor)
          : tipo === "data"
            ? formatarDataHistorico(valor)
            : tipo === "referencia"
              ? `#${String(valor).replace(/^#/, "")}`
              : String(valor);
    return [{ chave, label, tipo, valor: texto }];
  });
}
