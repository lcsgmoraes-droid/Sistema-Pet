export const FORM_CONSULTORIO_AGENDA_INICIAL = {
  nome: "",
  descricao: "",
  ordem: "",
};

function textoLimpo(valor) {
  return String(valor || "").trim();
}

export function montarPayloadConsultorioAgenda(form) {
  const nome = textoLimpo(form?.nome);
  const descricao = textoLimpo(form?.descricao);
  const ordemTexto = textoLimpo(form?.ordem);
  const payload = { nome };

  if (descricao) {
    payload.descricao = descricao;
  }

  if (ordemTexto) {
    payload.ordem = Number.parseInt(ordemTexto, 10);
  }

  return payload;
}

export function inserirConsultorioAgenda(consultorios, consultorioCriado) {
  const lista = Array.isArray(consultorios) ? consultorios : [];
  if (!consultorioCriado?.id) return lista;

  return [
    ...lista.filter((item) => String(item.id) !== String(consultorioCriado.id)),
    consultorioCriado,
  ].sort((a, b) => {
    const ordemA = Number.isFinite(Number(a.ordem)) ? Number(a.ordem) : 999;
    const ordemB = Number.isFinite(Number(b.ordem)) ? Number(b.ordem) : 999;
    if (ordemA !== ordemB) return ordemA - ordemB;
    return String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR");
  });
}
