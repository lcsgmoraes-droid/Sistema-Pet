export function validarAcertoEntregador(dados) {
  if (!dados.is_entregador || !dados.tipo_acerto_entrega) return null;
  if (!["semanal", "quinzenal", "mensal"].includes(dados.tipo_acerto_entrega)) {
    return "Selecione uma periodicidade válida ou Sem acerto.";
  }
  if (dados.tipo_acerto_entrega === "semanal") {
    const dia = Number(dados.dia_semana_acerto);
    if (!Number.isInteger(dia) || dia < 1 || dia > 7) {
      return "Informe o dia da semana para o acerto semanal.";
    }
  }
  if (dados.tipo_acerto_entrega === "mensal") {
    const dia = Number(dados.dia_mes_acerto);
    if (!Number.isInteger(dia) || dia < 1 || dia > 28) {
      return "O dia do mês deve estar entre 1 e 28.";
    }
  }
  return null;
}

export function normalizarAcertoEntregador(dados) {
  return {
    ...dados,
    tipo_acerto_entrega: dados.tipo_acerto_entrega || null,
    dia_semana_acerto:
      dados.tipo_acerto_entrega === "semanal" ? Number(dados.dia_semana_acerto) : null,
    dia_mes_acerto: dados.tipo_acerto_entrega === "mensal" ? Number(dados.dia_mes_acerto) : null,
  };
}
