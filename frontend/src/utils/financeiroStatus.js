const STATUS_CANCELADOS = new Set(["cancelado", "cancelada"]);
const TIPOS_REPASSE_CARTAO = new Set(["cartao_credito", "cartao_debito"]);

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
