export const TIPO_RECOMPRA_CONTINUA = "recompra_continua";
export const TIPO_PROTOCOLO_DOSES = "protocolo_doses";

export function criarRegraRecorrencia(tipo = TIPO_PROTOCOLO_DOSES) {
  const protocoloDoses = tipo === TIPO_PROTOCOLO_DOSES;
  return {
    nome: protocoloDoses ? "Novo protocolo" : "Recompra contínua",
    tipo,
    especie_compativel: "both",
    fase_vida: "all",
    intervalo_recompra_dias: protocoloDoses ? "" : "30",
    ajustar_ao_historico: !protocoloDoses,
    oferecer_novo_protocolo: false,
    reiniciar_apos_dias: "",
    observacoes: "",
    doses: protocoloDoses
      ? [
          { numero_dose: 1, dias_desde_inicio: "0" },
          { numero_dose: 2, dias_desde_inicio: "30" },
        ]
      : [],
  };
}

function normalizarRegra(regra = {}) {
  const tipo = regra.tipo || TIPO_PROTOCOLO_DOSES;
  const doses = (regra.doses || [])
    .slice()
    .sort((a, b) => Number(a.numero_dose) - Number(b.numero_dose))
    .map((dose, index) => ({
      id: dose.id,
      numero_dose: index + 1,
      dias_desde_inicio: String(index === 0 ? 0 : (dose.dias_desde_inicio ?? "")),
    }));

  return {
    id: regra.id,
    nome: regra.nome || (tipo === TIPO_PROTOCOLO_DOSES ? "Protocolo" : "Recompra contínua"),
    tipo,
    especie_compativel: regra.especie_compativel || "both",
    fase_vida: regra.fase_vida || "all",
    intervalo_recompra_dias:
      regra.intervalo_recompra_dias === null || regra.intervalo_recompra_dias === undefined
        ? ""
        : String(regra.intervalo_recompra_dias),
    ajustar_ao_historico: regra.ajustar_ao_historico !== false,
    oferecer_novo_protocolo: Boolean(regra.reiniciar_apos_dias),
    reiniciar_apos_dias:
      regra.reiniciar_apos_dias === null || regra.reiniciar_apos_dias === undefined
        ? ""
        : String(regra.reiniciar_apos_dias),
    observacoes: regra.observacoes || "",
    doses:
      tipo === TIPO_PROTOCOLO_DOSES && doses.length > 0
        ? doses
        : tipo === TIPO_PROTOCOLO_DOSES
          ? [{ numero_dose: 1, dias_desde_inicio: "0" }]
          : [],
  };
}

export function normalizarProtocolosRecorrencia(produto = {}) {
  if (Array.isArray(produto.protocolos_recorrencia) && produto.protocolos_recorrencia.length > 0) {
    return produto.protocolos_recorrencia
      .filter((regra) => regra.ativo !== false)
      .map(normalizarRegra);
  }
  if (!produto.tem_recorrencia || !produto.intervalo_dias) return [];

  const totalDoses = Number(produto.numero_doses || 0);
  const intervalo = Number(produto.intervalo_dias);
  if (totalDoses > 1) {
    return [
      normalizarRegra({
        nome: "Protocolo existente",
        tipo: TIPO_PROTOCOLO_DOSES,
        especie_compativel: produto.especie_compativel || "both",
        observacoes: produto.observacoes_recorrencia || "",
        doses: Array.from({ length: totalDoses }, (_, index) => ({
          numero_dose: index + 1,
          dias_desde_inicio: index * intervalo,
        })),
      }),
    ];
  }

  return [
    normalizarRegra({
      nome: "Recompra contínua",
      tipo: TIPO_RECOMPRA_CONTINUA,
      especie_compativel: produto.especie_compativel || "both",
      intervalo_recompra_dias: intervalo,
      observacoes: produto.observacoes_recorrencia || "",
    }),
  ];
}

export function alterarQuantidadeDoses(regra, quantidade) {
  const total = Math.min(Math.max(Number.parseInt(quantidade, 10) || 1, 1), 50);
  const atuais = regra.doses || [];
  const intervaloPadrao =
    atuais.length > 1
      ? Math.max(
          Number(atuais.at(-1)?.dias_desde_inicio || 0) -
            Number(atuais.at(-2)?.dias_desde_inicio || 0),
          1,
        )
      : 30;
  const doses = Array.from({ length: total }, (_, index) => {
    if (index === 0) return { ...(atuais[0] || {}), numero_dose: 1, dias_desde_inicio: "0" };
    if (atuais[index]) return { ...atuais[index], numero_dose: index + 1 };
    return {
      numero_dose: index + 1,
      dias_desde_inicio: String(
        Number(atuais.at(-1)?.dias_desde_inicio || 0) +
          intervaloPadrao * (index - atuais.length + 1),
      ),
    };
  });
  return { ...regra, doses };
}

export function validarProtocolosRecorrencia(protocolos = []) {
  if (protocolos.length === 0) return "Adicione ao menos uma regra de recorrência.";

  for (const regra of protocolos) {
    if (!String(regra.nome || "").trim()) return "Informe o nome de todos os protocolos.";
    if (regra.tipo === TIPO_RECOMPRA_CONTINUA) {
      const intervalo = Number(regra.intervalo_recompra_dias);
      if (!Number.isInteger(intervalo) || intervalo < 1 || intervalo > 3650) {
        return `Informe um intervalo válido para ${regra.nome}.`;
      }
      continue;
    }

    const dias = (regra.doses || []).map((dose) => Number(dose.dias_desde_inicio));
    if (dias.length === 0 || dias[0] !== 0) return `A Dose 1 de ${regra.nome} deve ser no dia 0.`;
    if (dias.some((dia) => !Number.isInteger(dia) || dia < 0 || dia > 3650)) {
      return `Revise os dias das doses de ${regra.nome}.`;
    }
    if (dias.some((dia, index) => index > 0 && dia <= dias[index - 1])) {
      return `As doses de ${regra.nome} precisam ter dias crescentes.`;
    }
    if (regra.oferecer_novo_protocolo) {
      const retorno = Number(regra.reiniciar_apos_dias);
      if (!Number.isInteger(retorno) || retorno < 1 || retorno > 3650) {
        return `Informe em quantos dias oferecer um novo protocolo de ${regra.nome}.`;
      }
    }
  }
  return null;
}

export function montarProtocolosRecorrenciaPayload(protocolos = []) {
  return protocolos.map((regra) => ({
    id: regra.id || undefined,
    nome: String(regra.nome || "").trim(),
    tipo: regra.tipo,
    especie_compativel: regra.especie_compativel || "both",
    fase_vida: regra.fase_vida || "all",
    intervalo_recompra_dias:
      regra.tipo === TIPO_RECOMPRA_CONTINUA ? Number(regra.intervalo_recompra_dias) : null,
    ajustar_ao_historico:
      regra.tipo === TIPO_RECOMPRA_CONTINUA && regra.ajustar_ao_historico !== false,
    reiniciar_apos_dias:
      regra.tipo === TIPO_PROTOCOLO_DOSES && regra.oferecer_novo_protocolo
        ? Number(regra.reiniciar_apos_dias)
        : null,
    observacoes: String(regra.observacoes || "").trim() || null,
    ativo: true,
    doses:
      regra.tipo === TIPO_PROTOCOLO_DOSES
        ? (regra.doses || []).map((dose, index) => ({
            id: dose.id || undefined,
            numero_dose: index + 1,
            dias_desde_inicio: index === 0 ? 0 : Number(dose.dias_desde_inicio),
          }))
        : [],
  }));
}
