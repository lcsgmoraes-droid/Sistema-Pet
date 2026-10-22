import { formatMoneyBRL } from "../../utils/formatters.js";

const centavos = (valor) => Math.round(Number(valor || 0) * 100);

export function validarTiposPagamentoExcedente({
  valorTotal = 0,
  totalPagoExistente = 0,
  pagamentos = [],
}) {
  const restante = Math.max(0, centavos(valorTotal) - centavos(totalPagoExistente));
  let fixos = 0;
  let dinheiro = 0;
  let planos = 0;
  let novos = 0;
  for (const pagamento of pagamentos) {
    const valor = centavos(pagamento.valor);
    novos += valor;
    const beneficio =
      pagamento.is_cashback ||
      pagamento.is_credito_cliente ||
      ["cashback", "credito_cliente"].includes(pagamento.forma_pagamento_tipo);
    const plano = ["crediario", "boleto"].includes(pagamento.forma_pagamento_tipo);
    const ehDinheiro = pagamento.forma_pagamento_tipo === "dinheiro";
    if (beneficio || plano || ehDinheiro) fixos += valor;
    if (ehDinheiro) dinheiro += valor;
    if (plano) planos += valor;
  }
  if (dinheiro > restante) {
    return "Confira o dinheiro: o valor aplicado deve respeitar o saldo líquido e a diferença deve constar como troco. Remova e adicione novamente esse pagamento com o valor entregue.";
  }
  if (fixos > restante) {
    return "Créditos, cashback, crediário e boleto devem respeitar o saldo líquido da venda. Revise esses pagamentos antes de continuar; a justificativa de excedente não libera benefícios ou planos acima do saldo.";
  }
  if (planos > 0 && novos > restante) {
    return "Revise as parcelas de crediário ou boleto antes de registrar um recebimento excedente. A justificativa não libera benefícios ou planos acima do saldo.";
  }
  return "";
}

export function comporExcedentePagamento({
  valorTotal = 0,
  totalPagoExistente = 0,
  pagamentos = [],
}) {
  const total = centavos(valorTotal);
  const existente = centavos(totalPagoExistente);
  const novos = pagamentos.reduce((soma, pagamento) => soma + centavos(pagamento.valor), 0);
  return {
    valorTotal: total / 100,
    totalPagoExistente: existente / 100,
    novosPagamentos: novos / 100,
    totalPagamentos: (existente + novos) / 100,
    excedente: Math.max(0, existente + novos - total) / 100,
    contexto: null,
    chave: JSON.stringify([
      total,
      existente,
      pagamentos.map((p) => [
        String(p.forma_pagamento_id ?? p.forma_id ?? ""),
        p.forma_pagamento_tipo || "",
        centavos(p.valor),
        centavos(p.valor_recebido ?? p.valor),
        centavos(p.troco),
        p.numero_parcelas || p.parcelas || 1,
        p.operadora_id || null,
        p.bandeira || null,
      ]),
    ]),
  };
}

export function extrairExcecaoPagamento(erro) {
  const detalhe = erro?.response?.data?.detail;
  if (
    !detalhe ||
    typeof detalhe !== "object" ||
    !["PAGAMENTO_EXCEDENTE_REQUER_JUSTIFICATIVA", "PAGAMENTO_EXCEDENTE_DESATUALIZADO"].includes(
      detalhe.code,
    )
  )
    return null;
  return detalhe;
}

export function usarContextoExcedenteServidor(composicao, snapshot) {
  const contexto = snapshot?.detalhe?.contexto_pagamento_excedente || snapshot?.detalhe?.contexto;
  if (
    snapshot?.base !== composicao.chave ||
    !contexto ||
    typeof snapshot.detalhe.excedente !== "number" ||
    !Number.isFinite(snapshot.detalhe.excedente) ||
    snapshot.detalhe.excedente <= 0 ||
    ![
      contexto.total_venda,
      contexto.total_ja_pago,
      contexto.total_novos_pagamentos,
      contexto.crediario_pendente,
    ].every((n) => typeof n === "number" && Number.isFinite(n) && n >= 0)
  )
    return composicao;
  return {
    ...composicao,
    contexto,
    valorTotal: contexto.total_venda,
    totalPagoExistente: contexto.total_ja_pago,
    novosPagamentos: contexto.total_novos_pagamentos,
    totalPagamentos:
      (centavos(contexto.total_ja_pago) + centavos(contexto.total_novos_pagamentos)) / 100,
    excedente: snapshot.detalhe.excedente,
    chave: JSON.stringify([composicao.chave, contexto]),
  };
}

export function excecaoPagamentoAutorizada(composicao, autorizacao) {
  return Boolean(
    composicao.excedente > 0 &&
    autorizacao?.chave === composicao.chave &&
    typeof autorizacao.justificativa === "string" &&
    autorizacao.justificativa.trim().length >= 10 &&
    autorizacao.justificativa.trim().length <= 1000,
  );
}

export function mensagemExcedentePagamento(composicao) {
  return `Os pagamentos somam ${formatMoneyBRL(composicao.totalPagamentos)} para o total líquido de ${formatMoneyBRL(composicao.valorTotal)}. O excedente de ${formatMoneyBRL(composicao.excedente)} exige justificativa e confirmação da exceção.`;
}
