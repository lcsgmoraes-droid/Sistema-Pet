import { FORM_NOVO_INICIAL, isoDate, normalizarTipoAgendamento } from "./agendaUtils.js";

function normalizarDataQuery(dataQuery) {
  const texto = String(dataQuery || "").trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(texto) ? texto : "";
}

export function aplicarDefaultsQueryAgenda({
  formAtual,
  dataBase = new Date(),
  dataQuery = "",
  tipoQuery = "",
  motivoQuery = "",
  consultaOrigemIdQuery = "",
} = {}) {
  const form = {
    ...FORM_NOVO_INICIAL,
    ...(formAtual || {}),
  };

  return {
    ...form,
    tipo: tipoQuery ? normalizarTipoAgendamento(tipoQuery) : form.tipo,
    consulta_origem_id: consultaOrigemIdQuery || form.consulta_origem_id || "",
    data: normalizarDataQuery(dataQuery) || form.data || isoDate(dataBase),
    motivo: motivoQuery || form.motivo,
  };
}
