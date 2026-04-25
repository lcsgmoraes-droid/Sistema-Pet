import { useEffect, useMemo, useState } from "react";

import { criarCalculadoraFormInicial } from "./consultaFormState";
import { parseNumero } from "./consultaFormUtils";

export default function useCalculadoraDoseConsulta({
  formPesoKg,
  petSelecionado,
  medicamentosCatalogo,
}) {
  const [calculadoraForm, setCalculadoraForm] = useState(criarCalculadoraFormInicial);

  const medicamentoCalculadoraSelecionado = useMemo(
    () =>
      medicamentosCatalogo.find(
        (item) => String(item.id) === String(calculadoraForm.medicamento_id)
      ) ?? null,
    [medicamentosCatalogo, calculadoraForm.medicamento_id]
  );

  const calculadoraResultado = useMemo(() => {
    const peso = parseNumero(calculadoraForm.peso_kg);
    const dose = parseNumero(calculadoraForm.dose_mg_kg);
    const frequencia = parseNumero(calculadoraForm.frequencia_horas);
    const dias = parseNumero(calculadoraForm.dias);
    if (!Number.isFinite(peso) || peso <= 0 || !Number.isFinite(dose) || dose <= 0) {
      return null;
    }

    const mgPorDose = peso * dose;
    const dosesPorDia = Number.isFinite(frequencia) && frequencia > 0 ? 24 / frequencia : null;
    const mgDia = dosesPorDia ? mgPorDose * dosesPorDia : null;
    const mgTratamento = mgDia && Number.isFinite(dias) && dias > 0 ? mgDia * dias : null;

    return {
      mgPorDose,
      dosesPorDia,
      mgDia,
      mgTratamento,
    };
  }, [calculadoraForm]);

  useEffect(() => {
    setCalculadoraForm((prev) => ({
      ...prev,
      peso_kg: prev.peso_kg || formPesoKg || String(petSelecionado?.peso || ""),
    }));
  }, [formPesoKg, petSelecionado]);

  useEffect(() => {
    if (!medicamentoCalculadoraSelecionado) return;
    const doseMin = parseNumero(medicamentoCalculadoraSelecionado.dose_minima_mg_kg);
    const doseMax = parseNumero(medicamentoCalculadoraSelecionado.dose_maxima_mg_kg);
    const doseMedia = Number.isFinite(doseMin) && Number.isFinite(doseMax)
      ? ((doseMin + doseMax) / 2).toFixed(2)
      : doseMin || doseMax || "";
    setCalculadoraForm((prev) => ({
      ...prev,
      dose_mg_kg: prev.dose_mg_kg || String(doseMedia || ""),
    }));
  }, [medicamentoCalculadoraSelecionado]);

  return {
    calculadoraForm,
    setCalculadoraForm,
    medicamentoCalculadoraSelecionado,
    calculadoraResultado,
  };
}
