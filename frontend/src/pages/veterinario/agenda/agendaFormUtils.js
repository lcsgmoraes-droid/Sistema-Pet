import {
  HORARIOS_BASE,
  TIPO_LABEL,
  TIPO_OPTIONS,
  addDias,
  inicioDaGradeMensal,
  isoDate,
} from "./agendaUtils";

export const MOTIVO_PLACEHOLDER_POR_TIPO = {
  consulta: "Ex: Consulta dermatológica, retorno clínico...",
  retorno: "Ex: Retorno pós-cirúrgico, reavaliação...",
  vacina: "Ex: V10 anual, antirrábica...",
  exame: "Ex: Hemograma, ultrassom, bioquímico...",
};

export function formatTituloAgenda(modo, dataRef, inicioSemana, fimSemana) {
  if (modo === "dia") {
    return dataRef.toLocaleDateString("pt-BR", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  }

  if (modo === "mes") {
    return dataRef.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
  }

  return `${inicioSemana.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
  })} - ${fimSemana.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })}`;
}

export function montarDiasVisiveis(modo, dataRef, inicioSemana) {
  return modo === "semana"
    ? Array.from({ length: 7 }, (_, index) => addDias(inicioSemana, index))
    : [dataRef];
}

export function montarDiasMes(modo, dataRef) {
  return modo === "mes"
    ? Array.from({ length: 42 }, (_, index) => addDias(inicioDaGradeMensal(dataRef), index))
    : [];
}

export function listarAgendamentosDia(agendamentos, data) {
  const key = isoDate(data);
  return agendamentos
    .filter((agendamento) => (agendamento.data_hora ?? "").startsWith(key))
    .sort((a, b) => (a.data_hora ?? "").localeCompare(b.data_hora ?? ""));
}

export function sugerirHoraLivreAgenda(agendamentosDia) {
  const ocupados = new Set(
    agendamentosDia
      .filter((agendamento) => agendamento.status !== "cancelado")
      .map((agendamento) => String(agendamento.data_hora || "").slice(11, 16))
      .filter(Boolean)
  );

  return HORARIOS_BASE.find((horario) => !ocupados.has(horario)) || "09:00";
}

export function montarHorariosAgendaModal(agendaDiaModal) {
  const ocupados = new Map();

  for (const agendamento of agendaDiaModal) {
    if (agendamento.status === "cancelado") continue;
    const hora = String(agendamento.data_hora || "").slice(11, 16);
    if (!hora) continue;
    const atual = ocupados.get(hora) || [];
    atual.push(agendamento);
    ocupados.set(hora, atual);
  }

  return HORARIOS_BASE.map((horario) => ({
    horario,
    ocupados: ocupados.get(horario) || [],
    livre: !ocupados.has(horario),
  }));
}

export function diagnosticarConflitoAgendamento({
  agendaDiaModal,
  agendamentoEditandoId,
  hora,
  veterinarioId,
  consultorioId,
}) {
  if (!hora) {
    return {
      conflitosVeterinario: [],
      conflitosConsultorio: [],
      outrosNoHorario: [],
    };
  }

  const ocupadosMesmoHorario = agendaDiaModal.filter((agendamento) => {
    if (agendamento.status === "cancelado") return false;
    if (agendamentoEditandoId && Number(agendamento.id) === Number(agendamentoEditandoId)) return false;
    return String(agendamento.data_hora || "").slice(11, 16) === hora;
  });

  const conflitosVeterinario = veterinarioId
    ? ocupadosMesmoHorario.filter(
        (agendamento) => String(agendamento.veterinario_id || "") === String(veterinarioId)
      )
    : [];

  const conflitosConsultorio = consultorioId
    ? ocupadosMesmoHorario.filter(
        (agendamento) => String(agendamento.consultorio_id || "") === String(consultorioId)
      )
    : [];

  return {
    conflitosVeterinario,
    conflitosConsultorio,
    outrosNoHorario: ocupadosMesmoHorario,
  };
}

export function obterDicaTipoAgendamento(tipoSelecionado) {
  return (
    TIPO_OPTIONS.find((item) => item.value === tipoSelecionado)?.hint ||
    "Escolha o fluxo para o próximo passo operacional."
  );
}

export function montarMensagemGerenciamento(agendamentoSelecionado, tipoAgendamentoSelecionado) {
  if (!agendamentoSelecionado) return "";

  if (agendamentoSelecionado.status === "em_atendimento") {
    return "Esse agendamento já está em atendimento. Você pode continuar, editar ou desfazer o início se foi aberto por engano.";
  }

  return `Deseja iniciar o fluxo de ${TIPO_LABEL[tipoAgendamentoSelecionado] ?? "Consulta"} agora?`;
}
