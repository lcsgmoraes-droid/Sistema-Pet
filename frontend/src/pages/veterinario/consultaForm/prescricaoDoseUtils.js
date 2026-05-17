import { parseNumero } from "./consultaFormUtils.js";

export function obterPesoParaCalculoDose(form = {}, petSelecionado = {}) {
  const candidatos = [
    form.peso_kg,
    form.peso_consulta,
    petSelecionado?.peso,
    petSelecionado?.peso_kg,
    petSelecionado?.peso_atual,
    petSelecionado?.ultimo_peso,
  ];

  for (const candidato of candidatos) {
    const peso = parseNumero(candidato);
    if (Number.isFinite(peso) && peso > 0) {
      return peso;
    }
  }
  return NaN;
}

export function obterDoseMgKgReferencia(item = {}) {
  const doseMin = parseNumero(item.dose_minima_mg_kg ?? item.dose_min_mgkg);
  const doseMax = parseNumero(item.dose_maxima_mg_kg ?? item.dose_max_mgkg);

  if (Number.isFinite(doseMin) && Number.isFinite(doseMax)) {
    return (doseMin + doseMax) / 2;
  }
  if (Number.isFinite(doseMin)) {
    return doseMin;
  }
  if (Number.isFinite(doseMax)) {
    return doseMax;
  }
  return NaN;
}

export function calcularDosePrescricaoPorPeso(item = {}, pesoKg) {
  const peso = parseNumero(pesoKg);
  const doseMgKg = obterDoseMgKgReferencia(item);

  if (!Number.isFinite(peso) || peso <= 0 || !Number.isFinite(doseMgKg) || doseMgKg <= 0) {
    return null;
  }

  return {
    dose_mg: (doseMgKg * peso).toFixed(2),
    unidade: "mg",
  };
}
