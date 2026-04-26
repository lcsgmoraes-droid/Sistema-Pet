export function numero(valor) {
  const parsed = Number.parseFloat(String(valor).replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

export function calcularDose(form) {
  const peso = numero(form.peso_kg);
  const dose = numero(form.dose_mg_kg);
  const frequencia = numero(form.frequencia_horas);
  const dias = numero(form.dias);
  if (!peso || !dose) return null;

  const mgPorDose = peso * dose;
  const dosesPorDia = frequencia ? 24 / frequencia : null;
  const mgDia = dosesPorDia ? mgPorDose * dosesPorDia : null;
  const mgTratamento = mgDia && dias ? mgDia * dias : null;

  return {
    mgPorDose,
    dosesPorDia,
    mgDia,
    mgTratamento,
  };
}

export function obterDoseMedia(medicamento) {
  const doseMin = numero(medicamento?.dose_min_mgkg);
  const doseMax = numero(medicamento?.dose_max_mgkg);
  return doseMin && doseMax ? ((doseMin + doseMax) / 2).toFixed(2) : (doseMin || doseMax || "");
}
