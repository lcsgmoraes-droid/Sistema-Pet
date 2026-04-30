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
  };
}
