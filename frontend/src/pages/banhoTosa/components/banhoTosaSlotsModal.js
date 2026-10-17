const STATUS_FINAIS = new Set(["cancelado", "entregue", "no_show"]);
const INTERVALO_GRADE = 30;

export function montarSlotsModal({
  agendamentos = [],
  capacidade,
  dataRef,
  duracaoMinutos = 60,
  form = {},
  recursos = [],
  sugestoes = [],
}) {
  const inicio = minutos(capacidade?.janela_inicio || "08:00");
  const fim = minutos(capacidade?.janela_fim || "18:00");
  const duracao =
    Number.isFinite(Number(duracaoMinutos)) && Number(duracaoMinutos) > 0
      ? Number(duracaoMinutos)
      : 60;
  const recursosAtivos = recursos.filter((recurso) => recurso.ativo !== false);
  const recursoSelecionadoId = form.recurso_id ? String(form.recurso_id) : "";
  const recursosDoSlot = recursoSelecionadoId
    ? recursosAtivos.filter((recurso) => String(recurso.id) === recursoSelecionadoId)
    : recursosAtivos;
  const ativos = agendamentos.filter(
    (item) =>
      !STATUS_FINAIS.has(
        String(item.status || "")
          .trim()
          .toLowerCase(),
      ),
  );
  const slots = [];

  for (let cursor = inicio; cursor < fim; cursor += INTERVALO_GRADE) {
    const horario = labelHora(cursor);
    const fimSlot = cursor + duracao;
    const foraExpediente = fimSlot > fim;
    const ocupados = ativos.filter(
      (item) =>
        (!recursoSelecionadoId || String(item.recurso_id || "") === recursoSelecionadoId) &&
        sobrepoeSlot(item, cursor, fimSlot, dataRef),
    );
    const conflitoPet =
      form.pet_id &&
      ativos.some(
        (item) =>
          String(item.pet_id) === String(form.pet_id) &&
          sobrepoeSlot(item, cursor, fimSlot, dataRef),
      );
    const disponiveis = recursosDoSlot
      .map((recurso) => ({
        recurso,
        pico: picoOcupacao(
          ocupacoesRecurso(capacidade, recurso.id, ativos, dataRef),
          cursor,
          fimSlot,
          dataRef,
        ),
      }))
      .filter(({ recurso, pico }) => pico < capacidadeRecurso(recurso))
      .sort((a, b) => a.pico - b.pico);
    const livre = Boolean(
      !foraExpediente &&
      !conflitoPet &&
      (disponiveis.length || (!recursos.length && !recursoSelecionadoId && !ocupados.length)),
    );
    const sugestaoApi = sugestoes.find(
      (item) =>
        String(item.horario_inicio || "").slice(0, 10) === dataRef &&
        hora(item.horario_inicio) === horario &&
        minutoData(item.horario_fim, dataRef) === fimSlot &&
        disponiveis.some(({ recurso }) => String(recurso.id) === String(item.recurso_id)),
    );
    // A API limita a lista de sugestoes. Ausencia nela nao prova falta de vaga:
    // o fallback usa a duracao inteira e o mesmo pico simultaneo do backend.
    const sugestao = livre
      ? sugestaoApi || sugestaoLocal(disponiveis[0], dataRef, cursor, fimSlot)
      : null;
    slots.push({
      descricao: descreverSlot({ livre, ocupados, sugestao, foraExpediente, conflitoPet }),
      foraExpediente,
      horario,
      livre,
      ocupados,
      sugestao,
    });
  }
  return slots;
}

function capacidadeRecurso(recurso) {
  return Math.max(Number(recurso.capacidade_simultanea || recurso.capacidade || 1), 1);
}

function ocupacoesRecurso(capacidade, recursoId, agendamentos, dataRef) {
  const resumo = capacidade?.recursos?.find(
    (item) => String(item.recurso_id) === String(recursoId),
  );
  // Inclui reservas iniciadas na vespera sem depender da listagem por inicio do dia.
  // Nao soma novamente os mesmos intervalos presentes na lista de compromissos.
  if (capacidade?.data === dataRef && Array.isArray(resumo?.intervalos_ocupados)) {
    return resumo.intervalos_ocupados;
  }
  return agendamentos.filter((item) => String(item.recurso_id || "") === String(recursoId));
}

function picoOcupacao(agendamentos, inicioSlot, fimSlot, dataRef) {
  const eventos = [];
  for (const item of agendamentos) {
    const [inicio, fim] = intervalo(item, dataRef);
    const entrada = Math.max(inicio, inicioSlot);
    const saida = Math.min(fim, fimSlot);
    if (entrada < saida) eventos.push([entrada, 1], [saida, -1]);
  }
  eventos.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  let atual = 0;
  let pico = 0;
  for (const [, delta] of eventos) {
    atual += delta;
    pico = Math.max(pico, atual);
  }
  return pico;
}

function sugestaoLocal(disponivel, dataRef, inicio, fim) {
  if (!disponivel || !dataRef) return null;
  const { recurso, pico } = disponivel;
  return {
    horario_inicio: `${dataRef}T${labelHora(inicio)}:00`,
    horario_fim: `${dataRef}T${labelHora(fim)}:00`,
    recurso_id: recurso.id,
    recurso_nome: recurso.nome,
    recurso_tipo: recurso.tipo,
    capacidade_simultanea: capacidadeRecurso(recurso),
    ocupacao_no_slot: pico,
    vagas_disponiveis: capacidadeRecurso(recurso) - pico,
    motivo: pico ? "Encaixe com capacidade disponivel" : "Horario livre",
  };
}

function descreverSlot({ livre, ocupados, sugestao, foraExpediente, conflitoPet }) {
  if (foraExpediente) return "O servico termina depois do expediente";
  if (conflitoPet) return "O pet ja possui agendamento neste intervalo";
  if (livre && sugestao?.recurso_nome) return `Livre em ${sugestao.recurso_nome}`;
  if (livre) return "Horario livre";
  if (ocupados.length)
    return ocupados.map((item) => item.pet_nome || `Pet #${item.pet_id}`).join(", ");
  return "Sem vaga sugerida para este horario";
}

function sobrepoeSlot(item, inicioSlot, fimSlot, dataRef) {
  const [inicio, fim] = intervalo(item, dataRef);
  return inicio < fimSlot && fim > inicioSlot;
}

function intervalo(item, dataRef) {
  const inicio = minutoData(item.data_hora_inicio, dataRef);
  const fim = item.data_hora_fim_prevista
    ? minutoData(item.data_hora_fim_prevista, dataRef)
    : inicio;
  return [inicio, fim];
}

function minutoData(valor, dataRef) {
  const dia = String(valor || "").slice(0, 10);
  const deslocamento = dataRef && dia ? (Date.parse(dia) - Date.parse(dataRef)) / 60000 : 0;
  return minutos(hora(valor)) + deslocamento;
}

function hora(valor) {
  return String(valor || "").slice(11, 16);
}

function minutos(valor) {
  const [h, m] = String(valor || "00:00").split(":");
  return Number(h || 0) * 60 + Number(m || 0);
}

function labelHora(total) {
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}
