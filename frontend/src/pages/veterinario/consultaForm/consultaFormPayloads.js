export function buildConsultaPayload({
  form,
  petSelecionadoAtual,
  tipoQuery,
  agendamentoIdQuery,
}) {
  return {
    pet_id: form.pet_id || undefined,
    cliente_id: petSelecionadoAtual.cliente_id,
    veterinario_id: form.veterinario_id || undefined,
    tipo: tipoQuery || "consulta",
    agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
    queixa_principal: form.motivo_consulta || undefined,
    peso_consulta: form.peso_kg ? Number.parseFloat(form.peso_kg) : undefined,
    temperatura: form.temperatura ? Number.parseFloat(form.temperatura) : undefined,
    frequencia_cardiaca: form.freq_cardiaca ? parseInt(form.freq_cardiaca) : undefined,
    frequencia_respiratoria: form.freq_respiratoria ? parseInt(form.freq_respiratoria) : undefined,
    tpc: form.tpc || undefined,
    mucosas: form.mucosa || undefined,
    hidratacao: form.estado_hidratacao || undefined,
    nivel_consciencia: form.nivel_consciencia || undefined,
    nivel_dor: form.nivel_dor ? parseInt(form.nivel_dor) : undefined,
    exame_fisico: form.exame_fisico || undefined,
    historia_clinica: form.historico_clinico || undefined,
    diagnostico: form.diagnostico || undefined,
    hipotese_diagnostica: form.prognostico || undefined,
    conduta: form.tratamento || undefined,
    observacoes_tutor: form.observacoes || undefined,
    retorno_em_dias: form.retorno_em_dias ? parseInt(form.retorno_em_dias) : undefined,
  };
}

export function buildFinalizacaoPayload(form) {
  return {
    diagnostico: form.diagnostico || undefined,
    hipotese_diagnostica: form.prognostico || undefined,
    conduta: form.tratamento || undefined,
    observacoes_tutor: form.observacoes || undefined,
    retorno_em_dias: form.retorno_em_dias ? parseInt(form.retorno_em_dias) : undefined,
  };
}

export function buildItensPrescricao(itens) {
  return itens
    .map((item) => {
      const nome = (item.nome || "").trim();
      const frequencia = (item.frequencia || "").trim();
      const instrucoes = (item.instrucoes || "").trim();
      const dose = (item.dose_mg || "").toString().trim();
      const unidade = (item.unidade || "mg").trim();
      const posologia = [dose ? `${dose} ${unidade}` : "", frequencia, instrucoes]
        .filter(Boolean)
        .join(" - ");

      if (!nome || !posologia) return null;

      return {
        nome_medicamento: nome,
        concentracao: item.principio_ativo || undefined,
        quantidade: dose || undefined,
        posologia,
        via_administracao: item.via || undefined,
        duracao_dias: item.duracao_dias ? Number.parseInt(item.duracao_dias) : undefined,
      };
    })
    .filter(Boolean);
}

export function buildNovoExamePayload({
  form,
  novoExameForm,
  consultaIdAtual,
  agendamentoIdQuery,
}) {
  return {
    pet_id: Number(form.pet_id),
    consulta_id: consultaIdAtual ? Number(consultaIdAtual) : undefined,
    agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
    tipo: novoExameForm.tipo,
    nome: novoExameForm.nome.trim(),
    data_solicitacao: novoExameForm.data_solicitacao || undefined,
    laboratorio: novoExameForm.laboratorio?.trim() || undefined,
    observacoes: novoExameForm.observacoes?.trim() || undefined,
  };
}

export function buildInsumoProcedimentoPayload({
  consultaIdAtual,
  insumoRapidoSelecionado,
  insumoRapidoForm,
  quantidadeUtilizada,
  quantidadeDesperdicio,
  quantidadeConsumida,
}) {
  const unidade = insumoRapidoSelecionado.unidade || "un";
  const resumoConsumo = `Utilizado: ${quantidadeUtilizada} ${unidade}${
    quantidadeDesperdicio ? ` | Desperdício: ${quantidadeDesperdicio} ${unidade}` : ""
  }`;
  const observacoes = insumoRapidoForm.observacoes?.trim()
    ? `${insumoRapidoForm.observacoes.trim()} | ${resumoConsumo}`
    : resumoConsumo;

  return {
    consulta_id: Number(consultaIdAtual),
    nome: `Insumo: ${insumoRapidoSelecionado.nome}`,
    descricao: "Lançamento rápido de insumo durante a consulta",
    valor: 0,
    observacoes,
    realizado: true,
    baixar_estoque: true,
    insumos: [
      {
        produto_id: insumoRapidoSelecionado.id,
        nome: insumoRapidoSelecionado.nome,
        unidade,
        quantidade: quantidadeConsumida,
        baixar_estoque: true,
      },
    ],
  };
}
