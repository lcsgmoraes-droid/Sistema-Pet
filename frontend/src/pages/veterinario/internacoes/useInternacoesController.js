import { useEffect } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { useInternacaoOperacional } from "../useInternacaoOperacional";
import { useInternacoesAcoes } from "./useInternacoesAcoes";
import { useInternacoesApoiosData } from "./useInternacoesApoiosData";
import { useInternacoesDerivados } from "./useInternacoesDerivados";
import { useInternacoesQueryEffects } from "./useInternacoesQueryEffects";
import { useInternacoesState } from "./useInternacoesState";

export default function useInternacoesController() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const abrirNovaQuery = searchParams.get("abrir_nova") === "1";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";
  const state = useInternacoesState();
  const apoios = useInternacoesApoiosData();
  const operacional = useInternacaoOperacional({ setErro: state.setErro });

  useInternacoesQueryEffects({
    abrirNovaQuery,
    novoPetIdQuery,
    setFormNova: state.setFormNova,
    setModalNova: state.setModalNova,
    setTutorNovaSelecionado: state.setTutorNovaSelecionado,
    tutorIdQuery,
    tutorNomeQuery,
  });

  const derivados = useInternacoesDerivados({
    agendaForm: state.agendaForm,
    agendaProcedimentos: operacional.agendaProcedimentos,
    evolucoes: state.evolucoes,
    filtroPessoaHistorico: state.filtroPessoaHistorico,
    formNova: state.formNova,
    internacoes: state.internacoes,
    location,
    pets: apoios.pets,
    totalBaias: operacional.totalBaias,
    tutorNovaSelecionado: state.tutorNovaSelecionado,
  });

  const acoes = useInternacoesAcoes({
    aba: state.aba,
    agendaForm: state.agendaForm,
    carregarAgendaProcedimentos: operacional.carregarAgendaProcedimentos,
    consultaIdQuery,
    expandida: state.expandida,
    filtroDataAltaFim: state.filtroDataAltaFim,
    filtroDataAltaInicio: state.filtroDataAltaInicio,
    filtroPessoaHistorico: state.filtroPessoaHistorico,
    filtroPetHistorico: state.filtroPetHistorico,
    formAlta: state.formAlta,
    formEvolucao: state.formEvolucao,
    formFeito: state.formFeito,
    formInsumoRapido: state.formInsumoRapido,
    formNova: state.formNova,
    insumoRapidoSelecionado: state.insumoRapidoSelecionado,
    modalAlta: state.modalAlta,
    modalEvolucao: state.modalEvolucao,
    modalFeito: state.modalFeito,
    setAba: state.setAba,
    setAgendaForm: state.setAgendaForm,
    setAgendaProcedimentos: operacional.setAgendaProcedimentos,
    setCarregando: state.setCarregando,
    setCarregandoHistoricoPet: state.setCarregandoHistoricoPet,
    setCentroAba: state.setCentroAba,
    setErro: state.setErro,
    setEvolucoes: state.setEvolucoes,
    setExpandida: state.setExpandida,
    setFiltroPessoaHistorico: state.setFiltroPessoaHistorico,
    setFiltroPetHistorico: state.setFiltroPetHistorico,
    setFormAlta: state.setFormAlta,
    setFormEvolucao: state.setFormEvolucao,
    setFormFeito: state.setFormFeito,
    setFormInsumoRapido: state.setFormInsumoRapido,
    setFormNova: state.setFormNova,
    setHistoricoPet: state.setHistoricoPet,
    setInsumoRapidoSelecionado: state.setInsumoRapidoSelecionado,
    setInternacoes: state.setInternacoes,
    setModalAlta: state.setModalAlta,
    setModalEvolucao: state.setModalEvolucao,
    setModalFeito: state.setModalFeito,
    setModalHistoricoPet: state.setModalHistoricoPet,
    setModalInsumoRapido: state.setModalInsumoRapido,
    setModalNova: state.setModalNova,
    setProcedimentosInternacao: state.setProcedimentosInternacao,
    setSalvando: state.setSalvando,
    setTutorNovaSelecionado: state.setTutorNovaSelecionado,
    sugestaoHorario: derivados.sugestaoHorario,
  });

  useEffect(() => {
    state.setAgendaForm((prev) => (prev.horario ? prev : { ...prev, horario: derivados.sugestaoHorario }));
  }, [derivados.sugestaoHorario, state.setAgendaForm]);

  useEffect(() => {
    state.setFormInsumoRapido((prev) =>
      prev.horario_execucao ? prev : { ...prev, horario_execucao: derivados.sugestaoHorario }
    );
  }, [derivados.sugestaoHorario, state.setFormInsumoRapido]);

  useEffect(() => {
    acoes.carregar();
  }, [acoes.carregar]);

  return {
    ...acoes,
    ...derivados,
    ...operacional,
    ...state,
    consultaIdQuery,
    onAbrirFichaPet: (petId) => navigate(`/pets/${petId}`),
    veterinarios: apoios.veterinarios,
  };
}
