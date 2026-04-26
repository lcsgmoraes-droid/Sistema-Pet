import { useInternacoesAgendaProcedimentosAcoes } from "./useInternacoesAgendaProcedimentosAcoes";
import { useInternacoesInsumoRapidoAcoes } from "./useInternacoesInsumoRapidoAcoes";
import { useInternacoesProcedimentoFeitoAcoes } from "./useInternacoesProcedimentoFeitoAcoes";

export function useInternacoesProcedimentosAcoes({
  agendaForm,
  carregarAgendaProcedimentos,
  carregarDetalheInternacao,
  expandida,
  formFeito,
  formInsumoRapido,
  insumoRapidoSelecionado,
  modalFeito,
  setAgendaForm,
  setAgendaProcedimentos,
  setErro,
  setFormFeito,
  setFormInsumoRapido,
  setInsumoRapidoSelecionado,
  setModalFeito,
  setModalInsumoRapido,
  setSalvando,
  sugestaoHorario,
}) {
  const agendaAcoes = useInternacoesAgendaProcedimentosAcoes({
    agendaForm,
    carregarAgendaProcedimentos,
    carregarDetalheInternacao,
    expandida,
    setAgendaForm,
    setAgendaProcedimentos,
    setErro,
    setSalvando,
    sugestaoHorario,
  });

  const feitoAcoes = useInternacoesProcedimentoFeitoAcoes({
    carregarDetalheInternacao,
    expandida,
    formFeito,
    modalFeito,
    setAgendaProcedimentos,
    setErro,
    setFormFeito,
    setModalFeito,
    setSalvando,
  });

  const insumoRapidoAcoes = useInternacoesInsumoRapidoAcoes({
    carregarDetalheInternacao,
    expandida,
    formInsumoRapido,
    insumoRapidoSelecionado,
    setErro,
    setFormInsumoRapido,
    setInsumoRapidoSelecionado,
    setModalInsumoRapido,
    setSalvando,
    sugestaoHorario,
  });

  return {
    ...agendaAcoes,
    ...feitoAcoes,
    ...insumoRapidoAcoes,
  };
}
