export const FORM_PROTOCOLO_INICIAL = {
  nome: "",
  especie: "",
  dose_inicial_semanas: "",
  numero_doses_serie: "1",
  intervalo_doses_dias: "",
  reforco_anual: true,
  observacoes: "",
};

export function mapProtocoloParaForm(item) {
  return {
    nome: item?.nome || "",
    especie: item?.especie || "",
    dose_inicial_semanas: item?.dose_inicial_semanas ?? "",
    numero_doses_serie: item?.numero_doses_serie ?? "1",
    intervalo_doses_dias: item?.intervalo_doses_dias ?? "",
    reforco_anual: item?.reforco_anual !== false,
    observacoes: item?.observacoes || "",
  };
}

export function buildProtocoloPayload(form) {
  return {
    nome: form.nome.trim(),
    especie: form.especie.trim() || undefined,
    dose_inicial_semanas: form.dose_inicial_semanas ? parseInt(form.dose_inicial_semanas, 10) : undefined,
    numero_doses_serie: form.numero_doses_serie ? parseInt(form.numero_doses_serie, 10) : undefined,
    intervalo_doses_dias: form.intervalo_doses_dias ? parseInt(form.intervalo_doses_dias, 10) : undefined,
    reforco_anual: Boolean(form.reforco_anual),
    observacoes: form.observacoes.trim() || undefined,
  };
}
