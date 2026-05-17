function listaOuVazia(valor) {
  return Array.isArray(valor) ? valor : [];
}

function texto(valor) {
  return valor == null ? "" : String(valor);
}

function separarPosologia(item) {
  const posologia = texto(item.posologia).trim();
  const quantidade = texto(item.quantidade).trim();
  if (!posologia) {
    return { unidade: "mg", frequencia: "", instrucoes: "" };
  }

  const partes = posologia.split(" - ").map((parte) => parte.trim()).filter(Boolean);
  const primeira = partes[0] || "";
  const doseRegex = quantidade
    ? new RegExp(`^${quantidade.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*(\\S+)?`, "i")
    : null;
  const matchDose = doseRegex ? primeira.match(doseRegex) : null;

  if (matchDose) {
    return {
      unidade: matchDose[1] || "mg",
      frequencia: partes[1] || "",
      instrucoes: partes.slice(2).join(" - "),
    };
  }

  return {
    unidade: "mg",
    frequencia: posologia,
    instrucoes: "",
  };
}

export function mapPrescricoesParaForm(prescricoes = []) {
  return listaOuVazia(prescricoes).flatMap((prescricao) =>
    listaOuVazia(prescricao.itens).map((item) => {
      const posologia = separarPosologia(item);
      return {
        medicamento_id: item.medicamento_catalogo_id ? String(item.medicamento_catalogo_id) : "",
        nome: texto(item.nome_medicamento),
        principio_ativo: texto(item.concentracao),
        dose_mg: texto(item.quantidade),
        unidade: posologia.unidade,
        dose_minima_mg_kg: "",
        dose_maxima_mg_kg: "",
        frequencia: posologia.frequencia,
        duracao_dias: item.duracao_dias != null ? String(item.duracao_dias) : "",
        via: texto(item.via_administracao) || "oral",
        instrucoes: posologia.instrucoes,
      };
    })
  );
}

export function mapProcedimentosParaForm(procedimentos = []) {
  return listaOuVazia(procedimentos).map((item) => ({
    catalogo_id: item.catalogo_id ? String(item.catalogo_id) : "",
    nome: texto(item.nome),
    descricao: texto(item.descricao),
    valor: item.valor != null ? String(item.valor) : "",
    observacoes: texto(item.observacoes),
    baixar_estoque: true,
  }));
}

export function mapConsultaParaForm(consulta) {
  return {
    pet_id: consulta.pet_id ?? "",
    veterinario_id: consulta.veterinario_id ?? "",
    motivo_consulta: consulta.queixa_principal ?? consulta.motivo_consulta ?? "",
    peso_kg: consulta.peso_consulta ?? consulta.peso_kg ?? "",
    temperatura: consulta.temperatura ?? "",
    freq_cardiaca: consulta.frequencia_cardiaca ?? consulta.freq_cardiaca ?? "",
    freq_respiratoria: consulta.frequencia_respiratoria ?? consulta.freq_respiratoria ?? "",
    tpc: consulta.tpc ?? "",
    mucosa: consulta.mucosas ?? consulta.mucosa ?? "",
    estado_hidratacao: consulta.hidratacao ?? consulta.estado_hidratacao ?? "",
    nivel_consciencia: consulta.nivel_consciencia ?? "",
    nivel_dor: consulta.nivel_dor ?? "",
    exame_fisico: consulta.exame_fisico ?? "",
    historico_clinico: consulta.historia_clinica ?? consulta.historico_clinico ?? "",
    diagnostico: consulta.diagnostico ?? "",
    prognostico: consulta.hipotese_diagnostica ?? consulta.prognostico ?? "",
    tratamento: consulta.conduta ?? consulta.tratamento ?? "",
    observacoes: consulta.observacoes_tutor ?? consulta.observacoes_internas ?? consulta.observacoes ?? "",
    retorno_em_dias: consulta.retorno_em_dias ?? "",
    prescricao_itens: listaOuVazia(consulta.prescricao_rascunho),
    procedimentos_realizados: listaOuVazia(consulta.procedimentos_rascunho),
  };
}
