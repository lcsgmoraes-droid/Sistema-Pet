import { useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import useCalculadoraDoseConsulta from "./useCalculadoraDoseConsulta";
import useConsultaAssinatura from "./useConsultaAssinatura";
import useConsultaCatalogos from "./useConsultaCatalogos";
import useConsultaEdicaoLoader from "./useConsultaEdicaoLoader";
import useConsultaFormActions from "./useConsultaFormActions";
import useConsultaFormState from "./useConsultaFormState";
import useConsultaPdfDownloads from "./useConsultaPdfDownloads";
import useConsultaTimeline from "./useConsultaTimeline";
import usePrescricaoProcedimentosConsulta from "./usePrescricaoProcedimentosConsulta";
import useTutorPetSelection from "./useTutorPetSelection";

export default function useVetConsultaFormController() {
  const navigate = useNavigate();
  const { consultaId } = useParams();
  const [searchParams] = useSearchParams();
  const isEdicao = Boolean(consultaId);
  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const agendamentoIdQuery = searchParams.get("agendamento_id") || "";
  const tipoQuery = searchParams.get("tipo") || "consulta";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";
  const state = useConsultaFormState(consultaId);

  const { pets, setPets, veterinarios, medicamentosCatalogo, procedimentosCatalogo } = useConsultaCatalogos();
  const { carregando, finalizado, setFinalizado } = useConsultaEdicaoLoader({
    isEdicao,
    consultaId,
    setForm: state.setForm,
    setErro: state.setErro,
  });

  const modoSomenteLeitura = isEdicao && finalizado;
  const tituloConsulta = modoSomenteLeitura
    ? "Consulta finalizada (somente visualizacao)"
    : isEdicao
      ? "Continuar consulta"
      : "Nova consulta";

  const selecaoTutorPet = useTutorPetSelection({
    pets,
    setPets,
    formPetId: state.form.pet_id,
    setCampo: state.setCampo,
    isEdicao,
    petIdQuery,
    novoPetIdQuery,
    tutorIdQuery,
    tutorNomeQuery,
  });

  const calculadora = useCalculadoraDoseConsulta({
    formPesoKg: state.form.peso_kg,
    petSelecionado: selecaoTutorPet.petSelecionado,
    medicamentosCatalogo,
  });
  const timeline = useConsultaTimeline(state.consultaIdAtual);
  const assinatura = useConsultaAssinatura({
    modoSomenteLeitura,
    consultaIdAtual: state.consultaIdAtual,
  });
  const pdfDownloads = useConsultaPdfDownloads({
    consultaIdAtual: state.consultaIdAtual,
    setErro: state.setErro,
  });
  const prescricoesProcedimentos = usePrescricaoProcedimentosConsulta({
    form: state.form,
    setForm: state.setForm,
    medicamentosCatalogo,
    procedimentosCatalogo,
    setErro: state.setErro,
  });

  const contextoConsultaParams = useMemo(() => {
    if (!state.form.pet_id) return "";
    const params = new URLSearchParams();
    params.set("pet_id", String(state.form.pet_id));
    if (state.consultaIdAtual) params.set("consulta_id", String(state.consultaIdAtual));
    if (agendamentoIdQuery) params.set("agendamento_id", String(agendamentoIdQuery));
    if (selecaoTutorPet.tutorSelecionado?.id) {
      params.set("tutor_id", String(selecaoTutorPet.tutorSelecionado.id));
    }
    if (selecaoTutorPet.tutorSelecionado?.nome) {
      params.set("tutor_nome", selecaoTutorPet.tutorSelecionado.nome);
    }
    return params.toString();
  }, [state.form.pet_id, state.consultaIdAtual, agendamentoIdQuery, selecaoTutorPet.tutorSelecionado]);

  const acoes = useConsultaFormActions({
    agendamentoIdQuery,
    carregarTimelineConsulta: timeline.carregarTimelineConsulta,
    consultaIdAtual: state.consultaIdAtual,
    contextoConsultaParams,
    etapa: state.etapa,
    form: state.form,
    insumoRapidoForm: state.insumoRapidoForm,
    insumoRapidoSelecionado: state.insumoRapidoSelecionado,
    navigate,
    novoExameArquivo: state.novoExameArquivo,
    novoExameForm: state.novoExameForm,
    pets,
    selecionarPetCriado: selecaoTutorPet.selecionarPetCriado,
    setConsultaIdAtual: state.setConsultaIdAtual,
    setErro: state.setErro,
    setEtapa: state.setEtapa,
    setFinalizado,
    setInsumoRapidoForm: state.setInsumoRapidoForm,
    setInsumoRapidoSelecionado: state.setInsumoRapidoSelecionado,
    setModalInsumoAberto: state.setModalInsumoAberto,
    setModalNovoExameAberto: state.setModalNovoExameAberto,
    setModalNovoPetAberto: state.setModalNovoPetAberto,
    setNovoExameArquivo: state.setNovoExameArquivo,
    setNovoExameForm: state.setNovoExameForm,
    setRefreshExamesToken: state.setRefreshExamesToken,
    setSalvando: state.setSalvando,
    setSalvandoInsumoRapido: state.setSalvandoInsumoRapido,
    setSalvandoNovoExame: state.setSalvandoNovoExame,
    setSucesso: state.setSucesso,
    tipoQuery,
    tutorSelecionado: selecaoTutorPet.tutorSelecionado,
  });

  return {
    ...acoes,
    ...calculadora,
    ...pdfDownloads,
    ...prescricoesProcedimentos,
    ...selecaoTutorPet,
    ...timeline,
    ...state,
    abrirModalCalculadora: () => state.setModalCalculadoraAberto(true),
    abrirModalNovoExame: () => state.setModalNovoExameAberto(true),
    abrirTimelineLink: (link) => navigate(link),
    assinatura,
    carregando,
    finalizado,
    handleClearErro: () => state.setErro(null),
    handleClearSucesso: () => state.setSucesso(null),
    isEdicao,
    medicamentosCatalogo,
    modoSomenteLeitura,
    navigate,
    procedimentosCatalogo,
    setCalculadoraForm: calculadora.setCalculadoraForm,
    tituloConsulta,
    veterinarios,
  };
}
