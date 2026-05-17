export function normalizarEtapaConsultaQuery(value) {
  const texto = String(value || "").trim().toLowerCase();
  if (!texto) return null;
  if (texto === "diagnostico" || texto === "diagnóstico" || texto === "prescricao" || texto === "prescrição") {
    return 2;
  }
  if (!/^\d+$/.test(texto)) return null;

  const etapa = Number(texto);
  return etapa >= 0 && etapa <= 2 ? etapa : null;
}
