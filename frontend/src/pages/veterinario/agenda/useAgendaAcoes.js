import { useAgendaCalendarioAcoes } from "./useAgendaCalendarioAcoes";
import { useAgendaCarregamentoAcoes } from "./useAgendaCarregamentoAcoes";
import { useAgendaFormularioAcoes } from "./useAgendaFormularioAcoes";
import { useAgendaGerenciamentoAcoes } from "./useAgendaGerenciamentoAcoes";

export function useAgendaAcoes({
  agendamentoEditandoId,
  agendamentoSelecionado,
  agendamentos,
  bloqueioCamposAgendamento,
  calendarioMeta,
  conflitoHorarioSelecionado,
  dataRef,
  fimSemana,
  formNovo,
  inicioSemana,
  modo,
  navigate,
  petSelecionadoModal,
  setAbrindoAgendamentoId,
  setAgendaDiaModal,
  setAgendamentoEditandoId,
  setAgendamentos,
  setAgendamentoSelecionado,
  setCarregando,
  setDataRef,
  setErro,
  setErroNovo,
  setFormNovo,
  setMensagemCalendario,
  setNovoAberto,
  setPetsDoTutor,
  setProcessandoAgendamentoId,
  setSalvandoNovo,
  setTutorSelecionado,
  tutorSelecionado,
}) {
  const carregamentoAcoes = useAgendaCarregamentoAcoes({
    agendamentos,
    dataRef,
    fimSemana,
    inicioSemana,
    modo,
    setAgendamentos,
    setCarregando,
    setDataRef,
    setErro,
  });

  const formularioAcoes = useAgendaFormularioAcoes({
    agendamentoEditandoId,
    bloqueioCamposAgendamento,
    carregar: carregamentoAcoes.carregar,
    conflitoHorarioSelecionado,
    dataRef,
    formNovo,
    navigate,
    petSelecionadoModal,
    setAgendaDiaModal,
    setAgendamentoEditandoId,
    setAgendamentoSelecionado,
    setErro,
    setErroNovo,
    setFormNovo,
    setNovoAberto,
    setPetsDoTutor,
    setSalvandoNovo,
    setTutorSelecionado,
    sugerirHoraLivre: carregamentoAcoes.sugerirHoraLivre,
    tutorSelecionado,
  });

  const calendarioAcoes = useAgendaCalendarioAcoes({
    calendarioMeta,
    setMensagemCalendario,
  });

  const gerenciamentoAcoes = useAgendaGerenciamentoAcoes({
    agendamentoSelecionado,
    carregar: carregamentoAcoes.carregar,
    navigate,
    setAbrindoAgendamentoId,
    setAgendamentoSelecionado,
    setErro,
    setErroNovo,
    setProcessandoAgendamentoId,
  });

  return {
    ...calendarioAcoes,
    ...carregamentoAcoes,
    ...formularioAcoes,
    ...gerenciamentoAcoes,
  };
}
