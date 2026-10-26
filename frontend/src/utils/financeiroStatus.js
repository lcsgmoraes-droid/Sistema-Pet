const STATUS_CANCELADOS = new Set(["cancelado", "cancelada"]);
const TIPOS_REPASSE_CARTAO = new Set(["cartao_credito", "cartao_debito", "link_pagamento"]);

export function obterStatusContaReceber(conta) {
  if (ehLancamentoFinanceiroCancelado(conta)) return "cancelado";
  const status = String(conta?.status || "pendente")
    .trim()
    .toLowerCase();
  if (["pago", "recebido"].includes(status)) return "recebido";
  const final = Number(conta?.valor_final);
  const recebido = Number(conta?.valor_recebido);
  if (Number.isFinite(final) && Number.isFinite(recebido) && final - recebido <= 0)
    return "recebido";
  return status === "baixa_parcial" ? "parcial" : status;
}

export function ehLancamentoFinanceiroCancelado(contaOuStatus) {
  const status = typeof contaOuStatus === "string" ? contaOuStatus : contaOuStatus?.status;
  return STATUS_CANCELADOS.has(
    String(status || "")
      .trim()
      .toLowerCase(),
  );
}

export function ehContaDeRepasseCartao(conta) {
  return TIPOS_REPASSE_CARTAO.has(
    String(conta?.forma_pagamento_tipo || "")
      .trim()
      .toLowerCase(),
  );
}

export function calcularSaldoFinanceiro(conta, campoPago) {
  if (ehLancamentoFinanceiroCancelado(conta)) return 0;

  const valorFinal = Number(conta?.valor_final ?? conta?.valor_original ?? 0);
  const valorPago = Number(conta?.[campoPago] ?? 0);
  return valorFinal - valorPago;
}

export function calcularSaldoAtualizadoFinanceiro(conta, campoPago) {
  if (ehLancamentoFinanceiroCancelado(conta)) return 0;

  const saldoAtualizado = Number(conta?.saldo_atualizado);
  if (Number.isFinite(saldoAtualizado)) return saldoAtualizado;

  return calcularSaldoFinanceiro(conta, campoPago);
}
