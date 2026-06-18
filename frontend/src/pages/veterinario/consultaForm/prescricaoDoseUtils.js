import { parseNumero } from "./consultaFormUtils.js";

function formatarNumeroCampo(valor) {
  if (!Number.isFinite(valor)) return "";
  return Number.isInteger(valor) ? String(valor) : String(Number(valor.toFixed(2)));
}

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

export function buildCalculadoraDoseFormParaPrescricao({
  calculadoraFormAtual = {},
  formConsulta = {},
  itemPrescricao = {},
  petSelecionado = {},
} = {}) {
  const peso = obterPesoParaCalculoDose(formConsulta, petSelecionado);
  const doseMgKg = obterDoseMgKgReferencia(itemPrescricao);

  return {
    ...calculadoraFormAtual,
    medicamento_id: itemPrescricao.medicamento_id
      ? String(itemPrescricao.medicamento_id)
      : calculadoraFormAtual.medicamento_id || "",
    peso_kg: Number.isFinite(peso) ? formatarNumeroCampo(peso) : calculadoraFormAtual.peso_kg || "",
    dose_mg_kg: Number.isFinite(doseMgKg)
      ? formatarNumeroCampo(doseMgKg)
      : calculadoraFormAtual.dose_mg_kg || "",
    frequencia_horas: calculadoraFormAtual.frequencia_horas || "12",
    dias: itemPrescricao.duracao_dias
      ? String(itemPrescricao.duracao_dias)
      : calculadoraFormAtual.dias || "7",
  };
}
