// Prévia informativa; a reserva efetiva e a concorrência são validadas pelo backend ao salvar.
export function resumirCreditosAgendamento(creditos, { petId, servicoId, data }) {
  if (!petId || !servicoId || !data) return { saldo: 0, pagamentoPendente: false };
  return creditos.reduce(
    (resumo, credito) => {
      if (
        credito.status !== "ativo" ||
        String(credito.pet_id || "") !== String(petId) ||
        credito.data_inicio > data ||
        credito.data_validade < data
      )
        return resumo;
      const itens = credito.servicos?.length
        ? credito.servicos
        : [
            {
              servico_id: credito.servico_id,
              saldo_creditos: credito.saldo_creditos,
            },
          ];
      const saldo = itens.reduce(
        (total, item) =>
          total +
          (item.servico_id && String(item.servico_id) === String(servicoId)
            ? Math.max(0, Number(item.saldo_creditos || 0))
            : 0),
        0,
      );
      return {
        saldo: resumo.saldo + saldo,
        pagamentoPendente:
          resumo.pagamentoPendente || (saldo > 0 && credito.status_pagamento !== "pago"),
      };
    },
    { saldo: 0, pagamentoPendente: false },
  );
}

export function formatarCreditos(value) {
  return Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
}
