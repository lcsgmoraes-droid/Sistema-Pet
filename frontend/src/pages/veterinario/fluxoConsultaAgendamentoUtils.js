import { normalizarTipoAgendamento } from "./agenda/agendaUtils.js";

const STATUS_AGENDAMENTO_FECHADO = new Set(["cancelado", "finalizado"]);
const TIPOS_CLINICOS = new Set(["consulta", "retorno"]);

export function buildConsultaPayloadFromAgendamento(agendamento) {
  const tipo = normalizarTipoAgendamento(agendamento?.tipo);
  const payload = {
    pet_id: agendamento?.pet_id,
    cliente_id: agendamento?.cliente_id,
    tipo: TIPOS_CLINICOS.has(tipo) ? tipo : "consulta",
    agendamento_id: agendamento?.id,
  };

  if (agendamento?.veterinario_id) {
    payload.veterinario_id = agendamento.veterinario_id;
  }

  const motivo = String(agendamento?.motivo || "").trim();
  if (motivo) {
    payload.queixa_principal = motivo;
  }

  return payload;
}

export function filtrarAgendamentosClinicosAbertos(agendamentos) {
  return [...(agendamentos || [])]
    .filter((agendamento) => {
      const tipo = normalizarTipoAgendamento(agendamento?.tipo);
      return TIPOS_CLINICOS.has(tipo) && !STATUS_AGENDAMENTO_FECHADO.has(agendamento?.status);
    })
    .sort((a, b) => String(a.data_hora || "").localeCompare(String(b.data_hora || "")));
}

export function getAgendamentoConsultaActionLabel(agendamento) {
  if (agendamento?.consulta_id) {
    return normalizarTipoAgendamento(agendamento?.tipo) === "retorno"
      ? "Continuar retorno"
      : "Continuar consulta";
  }

  return normalizarTipoAgendamento(agendamento?.tipo) === "retorno"
    ? "Iniciar retorno"
    : "Iniciar consulta";
}
