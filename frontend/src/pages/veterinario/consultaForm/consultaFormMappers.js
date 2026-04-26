export function mapConsultaParaForm(consulta) {
  return {
    pet_id: consulta.pet_id ?? "",
    veterinario_id: consulta.veterinario_id ?? "",
    motivo_consulta: consulta.motivo_consulta ?? "",
    peso_kg: consulta.peso_kg ?? "",
    temperatura: consulta.temperatura ?? "",
    freq_cardiaca: consulta.freq_cardiaca ?? "",
    freq_respiratoria: consulta.freq_respiratoria ?? "",
    tpc: consulta.tpc ?? "",
    mucosa: consulta.mucosa ?? "",
    estado_hidratacao: consulta.estado_hidratacao ?? "",
    nivel_consciencia: consulta.nivel_consciencia ?? "",
    nivel_dor: consulta.nivel_dor ?? "",
    exame_fisico: consulta.exame_fisico ?? "",
    historico_clinico: consulta.historico_clinico ?? "",
    diagnostico: consulta.diagnostico ?? "",
    prognostico: consulta.prognostico ?? "",
    tratamento: consulta.tratamento ?? "",
    observacoes: consulta.observacoes ?? "",
    retorno_em_dias: consulta.retorno_em_dias ?? "",
  };
}
