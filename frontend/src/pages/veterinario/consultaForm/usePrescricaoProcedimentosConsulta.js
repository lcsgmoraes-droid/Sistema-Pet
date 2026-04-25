import {
  criarPrescricaoItemInicial,
  criarProcedimentoRealizadoInicial,
} from "./consultaFormState";
import { parseNumero } from "./consultaFormUtils";

export default function usePrescricaoProcedimentosConsulta({
  form,
  setForm,
  medicamentosCatalogo,
  procedimentosCatalogo,
  setErro,
}) {
  function adicionarItem() {
    setForm((prev) => ({
      ...prev,
      prescricao_itens: [
        ...prev.prescricao_itens,
        criarPrescricaoItemInicial(),
      ],
    }));
  }

  function removerItem(idx) {
    setForm((prev) => ({
      ...prev,
      prescricao_itens: prev.prescricao_itens.filter((_, i) => i !== idx),
    }));
  }

  function setItem(idx, chave, valor) {
    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      itens[idx] = { ...itens[idx], [chave]: valor };
      return { ...prev, prescricao_itens: itens };
    });
  }

  function adicionarProcedimento() {
    setForm((prev) => ({
      ...prev,
      procedimentos_realizados: [
        ...prev.procedimentos_realizados,
        criarProcedimentoRealizadoInicial(),
      ],
    }));
  }

  function removerProcedimento(idx) {
    setForm((prev) => ({
      ...prev,
      procedimentos_realizados: prev.procedimentos_realizados.filter((_, i) => i !== idx),
    }));
  }

  function setProcedimentoItem(idx, campo, valor) {
    setForm((prev) => {
      const itens = [...prev.procedimentos_realizados];
      itens[idx] = { ...itens[idx], [campo]: valor };
      return { ...prev, procedimentos_realizados: itens };
    });
  }

  function selecionarProcedimentoCatalogo(idx, catalogoId) {
    const procedimento = procedimentosCatalogo.find((item) => String(item.id) === String(catalogoId));
    setForm((prev) => {
      const itens = [...prev.procedimentos_realizados];
      itens[idx] = {
        ...itens[idx],
        catalogo_id: catalogoId,
        nome: procedimento?.nome || itens[idx].nome,
        descricao: procedimento?.descricao || "",
        valor: procedimento?.valor_padrao != null ? String(procedimento.valor_padrao) : itens[idx].valor,
      };
      return { ...prev, procedimentos_realizados: itens };
    });
  }

  function calcularDosePorPeso(item) {
    const peso = parseNumero(form.peso_kg);
    if (!Number.isFinite(peso) || peso <= 0) {
      setErro("Informe o peso do pet para calcular a dose automaticamente.");
      return null;
    }

    const doseMin = parseNumero(item.dose_minima_mg_kg);
    const doseMax = parseNumero(item.dose_maxima_mg_kg);
    let doseMgKg = Number.isFinite(doseMin) ? doseMin : NaN;

    if (Number.isFinite(doseMin) && Number.isFinite(doseMax)) {
      doseMgKg = (doseMin + doseMax) / 2;
    } else if (!Number.isFinite(doseMgKg) && Number.isFinite(doseMax)) {
      doseMgKg = doseMax;
    }

    if (!Number.isFinite(doseMgKg) || doseMgKg <= 0) {
      setErro("Esse medicamento não tem dose mg/kg cadastrada no catálogo.");
      return null;
    }

    return {
      dose_mg: (doseMgKg * peso).toFixed(2),
      unidade: "mg",
    };
  }

  function selecionarMedicamentoNoItem(idx, medicamentoId) {
    const medicamento = medicamentosCatalogo.find((m) => String(m.id) === String(medicamentoId));
    if (!medicamento) return;

    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      const itemAtual = itens[idx] ?? {};
      const itemAtualizado = {
        ...itemAtual,
        medicamento_id: medicamento.id,
        nome: medicamento.nome ?? itemAtual.nome ?? "",
        principio_ativo: medicamento.principio_ativo ?? itemAtual.principio_ativo ?? "",
        via: medicamento.via_administracao ?? itemAtual.via ?? "oral",
        dose_minima_mg_kg: medicamento.dose_minima_mg_kg,
        dose_maxima_mg_kg: medicamento.dose_maxima_mg_kg,
      };

      const doseCalculada = calcularDosePorPeso(itemAtualizado);
      if (doseCalculada) {
        itemAtualizado.dose_mg = doseCalculada.dose_mg;
        itemAtualizado.unidade = doseCalculada.unidade;
      }

      itens[idx] = itemAtualizado;
      return { ...prev, prescricao_itens: itens };
    });
  }

  function recalcularDoseItem(idx) {
    const item = form.prescricao_itens[idx];
    if (!item) return;

    const doseCalculada = calcularDosePorPeso(item);
    if (!doseCalculada) return;

    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      itens[idx] = {
        ...itens[idx],
        dose_mg: doseCalculada.dose_mg,
        unidade: doseCalculada.unidade,
      };
      return { ...prev, prescricao_itens: itens };
    });
  }

  return {
    adicionarItem,
    removerItem,
    setItem,
    selecionarMedicamentoNoItem,
    recalcularDoseItem,
    adicionarProcedimento,
    removerProcedimento,
    setProcedimentoItem,
    selecionarProcedimentoCatalogo,
  };
}
