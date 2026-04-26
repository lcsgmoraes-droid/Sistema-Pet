import { useMemo } from "react";

import { buildReturnTo } from "../../../utils/petReturnFlow";
import {
  MOTIVO_PLACEHOLDER_POR_TIPO,
  diagnosticarConflitoAgendamento,
  formatTituloAgenda,
  montarDiasMes,
  montarDiasVisiveis,
  montarHorariosAgendaModal,
  montarMensagemGerenciamento,
  obterDicaTipoAgendamento,
} from "./agendaFormUtils";
import { TIPO_ACAO, addDias, normalizarTipoAgendamento } from "./agendaUtils";

export function useAgendaDerivados({
  agendaDiaModal,
  agendamentoEditandoId,
  agendamentoSelecionado,
  consultorios,
  dataRef,
  formNovo,
  location,
  modo,
  petsDoTutor,
  veterinarios,
}) {
  const { inicioSemana, fimSemana } = useMemo(() => {
    const inicio =
      modo === "semana" || modo === "mes" ? addDias(dataRef, -dataRef.getDay()) : dataRef;
    const fim = modo === "semana" || modo === "mes" ? addDias(inicio, 6) : dataRef;
    return { inicioSemana: inicio, fimSemana: fim };
  }, [dataRef, modo]);

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search, { abrir_novo: "1" }),
    [location.pathname, location.search]
  );

  const tituloAgenda = useMemo(
    () => formatTituloAgenda(modo, dataRef, inicioSemana, fimSemana),
    [dataRef, fimSemana, inicioSemana, modo]
  );

  const diasVisiveis = useMemo(
    () => montarDiasVisiveis(modo, dataRef, inicioSemana),
    [dataRef, inicioSemana, modo]
  );

  const diasMes = useMemo(() => montarDiasMes(modo, dataRef), [dataRef, modo]);

  const horariosAgendaModal = useMemo(() => montarHorariosAgendaModal(agendaDiaModal), [agendaDiaModal]);

  const petSelecionadoModal = useMemo(
    () => petsDoTutor.find((pet) => String(pet.id) === String(formNovo.pet_id)) || null,
    [petsDoTutor, formNovo.pet_id]
  );

  const veterinarioSelecionadoModal = useMemo(
    () => veterinarios.find((vet) => String(vet.id) === String(formNovo.veterinario_id)) || null,
    [veterinarios, formNovo.veterinario_id]
  );

  const consultorioSelecionadoModal = useMemo(
    () => consultorios.find((item) => String(item.id) === String(formNovo.consultorio_id)) || null,
    [consultorios, formNovo.consultorio_id]
  );

  const diagnosticoConflitoSelecionado = useMemo(
    () =>
      diagnosticarConflitoAgendamento({
        agendaDiaModal,
        agendamentoEditandoId,
        hora: formNovo.hora,
        veterinarioId: formNovo.veterinario_id,
        consultorioId: formNovo.consultorio_id,
      }),
    [agendaDiaModal, agendamentoEditandoId, formNovo.hora, formNovo.veterinario_id, formNovo.consultorio_id]
  );

  const conflitoHorarioSelecionado =
    diagnosticoConflitoSelecionado.conflitosVeterinario.length > 0 ||
    diagnosticoConflitoSelecionado.conflitosConsultorio.length > 0;

  const tipoSelecionado = normalizarTipoAgendamento(formNovo.tipo);
  const dicaTipoSelecionado = obterDicaTipoAgendamento(tipoSelecionado);
  const motivoPlaceholderPorTipo = MOTIVO_PLACEHOLDER_POR_TIPO;

  const tipoAgendamentoSelecionado = agendamentoSelecionado
    ? normalizarTipoAgendamento(agendamentoSelecionado.tipo)
    : "consulta";

  const podeExcluirAgendamento =
    agendamentoSelecionado &&
    !agendamentoSelecionado.consulta_id &&
    agendamentoSelecionado.status !== "finalizado";

  const podeVoltarStatus =
    agendamentoSelecionado &&
    (agendamentoSelecionado.status === "em_atendimento" || Boolean(agendamentoSelecionado.consulta_id));

  const labelVoltarStatus = agendamentoSelecionado?.consulta_id
    ? "Desfazer inicio do atendimento"
    : "Voltar para agendado";

  const labelAbrirAgendamentoSelecionado = agendamentoSelecionado?.consulta_id
    ? "Continuar atendimento"
    : TIPO_ACAO[tipoAgendamentoSelecionado] ?? "Abrir atendimento";

  const mensagemAgendamentoSelecionado = montarMensagemGerenciamento(
    agendamentoSelecionado,
    tipoAgendamentoSelecionado
  );

  const bloqueioCamposAgendamento = useMemo(
    () => ({
      veterinario: veterinarios.length > 0 && !formNovo.veterinario_id,
      consultorio: consultorios.length > 0 && !formNovo.consultorio_id,
    }),
    [consultorios.length, formNovo.consultorio_id, formNovo.veterinario_id, veterinarios.length]
  );

  return {
    bloqueioCamposAgendamento,
    conflitoHorarioSelecionado,
    consultorioSelecionadoModal,
    diagnosticoConflitoSelecionado,
    diasMes,
    diasVisiveis,
    dicaTipoSelecionado,
    fimSemana,
    horariosAgendaModal,
    inicioSemana,
    labelAbrirAgendamentoSelecionado,
    labelVoltarStatus,
    mensagemAgendamentoSelecionado,
    motivoPlaceholderPorTipo,
    petSelecionadoModal,
    podeExcluirAgendamento,
    podeVoltarStatus,
    retornoNovoPet,
    tipoAgendamentoSelecionado,
    tipoSelecionado,
    tituloAgenda,
    veterinarioSelecionadoModal,
  };
}
