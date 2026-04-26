import { useCallback, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  criarConsultaFormInicial,
  criarInsumoRapidoFormInicial,
  criarNovoExameFormInicial,
} from "./consultaFormState";
import useCalculadoraDoseConsulta from "./useCalculadoraDoseConsulta";
import useConsultaAssinatura from "./useConsultaAssinatura";
import useConsultaCatalogos from "./useConsultaCatalogos";
import useConsultaEdicaoLoader from "./useConsultaEdicaoLoader";
import useConsultaFormActions from "./useConsultaFormActions";
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

  const [etapa, setEtapa] = useState(0);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);
  const [consultaIdAtual, setConsultaIdAtual] = useState(consultaId ?? null);
  const [modalCalculadoraAberto, setModalCalculadoraAberto] = useState(false);
  const [modalNovoExameAberto, setModalNovoExameAberto] = useState(false);
  const [salvandoNovoExame, setSalvandoNovoExame] = useState(false);
  const [modalNovoPetAberto, setModalNovoPetAberto] = useState(false);
  const [refreshExamesToken, setRefreshExamesToken] = useState(0);
  const [novoExameForm, setNovoExameForm] = useState(criarNovoExameFormInicial);
  const [novoExameArquivo, setNovoExameArquivo] = useState(null);
  const [modalInsumoAberto, setModalInsumoAberto] = useState(false);
  const [salvandoInsumoRapido, setSalvandoInsumoRapido] = useState(false);
  const [insumoRapidoSelecionado, setInsumoRapidoSelecionado] = useState(null);
  const [insumoRapidoForm, setInsumoRapidoForm] = useState(criarInsumoRapidoFormInicial);
  const [form, setForm] = useState(criarConsultaFormInicial);

  const setCampo = useCallback((campo, valor) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }, []);

  const { pets, setPets, veterinarios, medicamentosCatalogo, procedimentosCatalogo } = useConsultaCatalogos();
  const { carregando, finalizado, setFinalizado } = useConsultaEdicaoLoader({
    isEdicao,
    consultaId,
    setForm,
    setErro,
  });

  const modoSomenteLeitura = isEdicao && finalizado;
  const tituloConsulta = modoSomenteLeitura
    ? "Consulta finalizada (somente visualização)"
    : isEdicao
      ? "Continuar consulta"
      : "Nova consulta";

  const selecaoTutorPet = useTutorPetSelection({
    pets,
    setPets,
    formPetId: form.pet_id,
    setCampo,
    isEdicao,
    petIdQuery,
    novoPetIdQuery,
    tutorIdQuery,
    tutorNomeQuery,
  });

  const calculadora = useCalculadoraDoseConsulta({
    formPesoKg: form.peso_kg,
    petSelecionado: selecaoTutorPet.petSelecionado,
    medicamentosCatalogo,
  });

  const timeline = useConsultaTimeline(consultaIdAtual);
  const assinatura = useConsultaAssinatura({
    modoSomenteLeitura,
    consultaIdAtual,
  });
  const pdfDownloads = useConsultaPdfDownloads({
    consultaIdAtual,
    setErro,
  });
  const prescricoesProcedimentos = usePrescricaoProcedimentosConsulta({
    form,
    setForm,
    medicamentosCatalogo,
    procedimentosCatalogo,
    setErro,
  });

  const contextoConsultaParams = useMemo(() => {
    if (!form.pet_id) return "";
    const params = new URLSearchParams();
    params.set("pet_id", String(form.pet_id));
    if (consultaIdAtual) params.set("consulta_id", String(consultaIdAtual));
    if (agendamentoIdQuery) params.set("agendamento_id", String(agendamentoIdQuery));
    if (selecaoTutorPet.tutorSelecionado?.id) {
      params.set("tutor_id", String(selecaoTutorPet.tutorSelecionado.id));
    }
    if (selecaoTutorPet.tutorSelecionado?.nome) {
      params.set("tutor_nome", selecaoTutorPet.tutorSelecionado.nome);
    }
    return params.toString();
  }, [form.pet_id, consultaIdAtual, agendamentoIdQuery, selecaoTutorPet.tutorSelecionado]);

  const acoes = useConsultaFormActions({
    agendamentoIdQuery,
    carregarTimelineConsulta: timeline.carregarTimelineConsulta,
    consultaIdAtual,
    contextoConsultaParams,
    etapa,
    form,
    insumoRapidoForm,
    insumoRapidoSelecionado,
    navigate,
    novoExameArquivo,
    novoExameForm,
    pets,
    selecionarPetCriado: selecaoTutorPet.selecionarPetCriado,
    setConsultaIdAtual,
    setErro,
    setEtapa,
    setFinalizado,
    setInsumoRapidoForm,
    setInsumoRapidoSelecionado,
    setModalInsumoAberto,
    setModalNovoExameAberto,
    setModalNovoPetAberto,
    setNovoExameArquivo,
    setNovoExameForm,
    setRefreshExamesToken,
    setSalvando,
    setSalvandoInsumoRapido,
    setSalvandoNovoExame,
    setSucesso,
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
    abrirModalCalculadora: () => setModalCalculadoraAberto(true),
    abrirModalNovoExame: () => setModalNovoExameAberto(true),
    abrirTimelineLink: (link) => navigate(link),
    assinatura,
    carregando,
    consultaIdAtual,
    etapa,
    erro,
    finalizado,
    form,
    handleClearErro: () => setErro(null),
    handleClearSucesso: () => setSucesso(null),
    isEdicao,
    medicamentosCatalogo,
    modalCalculadoraAberto,
    modalInsumoAberto,
    modalNovoExameAberto,
    modalNovoPetAberto,
    modoSomenteLeitura,
    navigate,
    novoExameForm,
    procedimentosCatalogo,
    refreshExamesToken,
    salvando,
    salvandoInsumoRapido,
    salvandoNovoExame,
    setCalculadoraForm: calculadora.setCalculadoraForm,
    setEtapa,
    setInsumoRapidoForm,
    setInsumoRapidoSelecionado,
    setModalCalculadoraAberto,
    setModalInsumoAberto,
    setModalNovoExameAberto,
    setModalNovoPetAberto,
    setNovoExameArquivo,
    setNovoExameForm,
    setCampo,
    sucesso,
    tituloConsulta,
    veterinarios,
  };
}
