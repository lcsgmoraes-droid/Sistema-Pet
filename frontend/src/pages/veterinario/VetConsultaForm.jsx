import { useState, useMemo, useCallback } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import ConsultaActionsFooter from "./consultaForm/ConsultaActionsFooter";
import ConsultaFeedbackAlerts from "./consultaForm/ConsultaFeedbackAlerts";
import ConsultaFinalizadaScreen from "./consultaForm/ConsultaFinalizadaScreen";
import ConsultaFormModals from "./consultaForm/ConsultaFormModals";
import ConsultaHeader from "./consultaForm/ConsultaHeader";
import ConsultaReadonlyNotice from "./consultaForm/ConsultaReadonlyNotice";
import ConsultaSteps from "./consultaForm/ConsultaSteps";
import DiagnosticoTratamentoSection from "./consultaForm/DiagnosticoTratamentoSection";
import ExameClinicoSection from "./consultaForm/ExameClinicoSection";
import TriagemInicialSection from "./consultaForm/TriagemInicialSection";
import {
  criarConsultaFormInicial,
  criarInsumoRapidoFormInicial,
  criarNovoExameFormInicial,
} from "./consultaForm/consultaFormState";
import {
  ETAPAS,
  css,
} from "./consultaForm/consultaFormUtils";
import useConsultaFormActions from "./consultaForm/useConsultaFormActions";
import useCalculadoraDoseConsulta from "./consultaForm/useCalculadoraDoseConsulta";
import useConsultaAssinatura from "./consultaForm/useConsultaAssinatura";
import useConsultaCatalogos from "./consultaForm/useConsultaCatalogos";
import useConsultaEdicaoLoader from "./consultaForm/useConsultaEdicaoLoader";
import useConsultaPdfDownloads from "./consultaForm/useConsultaPdfDownloads";
import useConsultaTimeline from "./consultaForm/useConsultaTimeline";
import usePrescricaoProcedimentosConsulta from "./consultaForm/usePrescricaoProcedimentosConsulta";
import useTutorPetSelection from "./consultaForm/useTutorPetSelection";

// ---------- helpers ----------
function campo(label, obrigatorio = false) {
  return function renderCampo(children) {
    return (
      <div className="space-y-1">
        <label className="block text-xs font-medium text-gray-600">
          {label} {obrigatorio && <span className="text-red-400">*</span>}
        </label>
        {children}
      </div>
    );
  };
}

// ---------- componente principal ----------
export default function VetConsultaForm() {
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

  const {
    pets,
    setPets,
    veterinarios,
    medicamentosCatalogo,
    procedimentosCatalogo,
  } = useConsultaCatalogos();
  const [novoExameForm, setNovoExameForm] = useState(criarNovoExameFormInicial);
  const [novoExameArquivo, setNovoExameArquivo] = useState(null);
  const [modalInsumoAberto, setModalInsumoAberto] = useState(false);
  const [salvandoInsumoRapido, setSalvandoInsumoRapido] = useState(false);
  const [insumoRapidoSelecionado, setInsumoRapidoSelecionado] = useState(null);
  const [insumoRapidoForm, setInsumoRapidoForm] = useState(criarInsumoRapidoFormInicial);

  // ---------- Form state ----------
  const [form, setForm] = useState(criarConsultaFormInicial);
  const set = useCallback((campo, valor) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }, []);
  const {
    carregando,
    finalizado,
    setFinalizado,
  } = useConsultaEdicaoLoader({
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

  const {
    buscaTutor,
    setBuscaTutor,
    tutorSelecionado,
    setTutorSelecionado,
    tutoresSugeridos,
    listaPetsExpandida,
    setListaPetsExpandida,
    petsDoTutor,
    petSelecionado,
    petSelecionadoLabel,
    sugestoesEspecies,
    selecionarTutor,
    limparTutor,
    selecionarPetCriado,
  } = useTutorPetSelection({
    pets,
    setPets,
    formPetId: form.pet_id,
    setCampo: set,
    isEdicao,
    petIdQuery,
    novoPetIdQuery,
    tutorIdQuery,
    tutorNomeQuery,
  });
  const {
    calculadoraForm,
    setCalculadoraForm,
    medicamentoCalculadoraSelecionado,
    calculadoraResultado,
  } = useCalculadoraDoseConsulta({
    formPesoKg: form.peso_kg,
    petSelecionado,
    medicamentosCatalogo,
  });
  const {
    timelineConsulta,
    carregandoTimeline,
    carregarTimelineConsulta,
  } = useConsultaTimeline(consultaIdAtual);
  const assinatura = useConsultaAssinatura({
    modoSomenteLeitura,
    consultaIdAtual,
  });
  const {
    baixandoPdf,
    baixarProntuarioPdf,
    baixarUltimaReceitaPdf,
  } = useConsultaPdfDownloads({
    consultaIdAtual,
    setErro,
  });
  const {
    adicionarItem,
    removerItem,
    setItem,
    selecionarMedicamentoNoItem,
    recalcularDoseItem,
    adicionarProcedimento,
    removerProcedimento,
    setProcedimentoItem,
    selecionarProcedimentoCatalogo,
  } = usePrescricaoProcedimentosConsulta({
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
    if (tutorSelecionado?.id) params.set("tutor_id", String(tutorSelecionado.id));
    if (tutorSelecionado?.nome) params.set("tutor_nome", tutorSelecionado.nome);
    return params.toString();
  }, [form.pet_id, consultaIdAtual, agendamentoIdQuery, tutorSelecionado]);

  const {
    abrirFluxoConsulta,
    abrirModalInsumoRapido,
    abrirModalNovoPet,
    finalizar,
    handleNovoPetCriado,
    salvarInsumoRapidoConsulta,
    salvarNovoExameRapido,
    salvarRascunho,
  } = useConsultaFormActions({
    agendamentoIdQuery,
    carregarTimelineConsulta,
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
    selecionarPetCriado,
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
    tutorSelecionado,
  });

  // ---------- Render ----------
  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (finalizado && !isEdicao) {
    return (
      <ConsultaFinalizadaScreen
        onVerConsultas={() => navigate("/veterinario/consultas")}
        onNovaConsulta={() => navigate("/veterinario/consultas/nova")}
      />
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <ConsultaHeader
        tituloConsulta={tituloConsulta}
        consultaIdAtual={consultaIdAtual}
        onAbrirAssistente={() => abrirFluxoConsulta("/veterinario/ia")}
        onAbrirCalculadora={() => setModalCalculadoraAberto(true)}
      />

      {modoSomenteLeitura && (
        <ConsultaReadonlyNotice
          assinatura={assinatura}
          baixandoPdf={baixandoPdf}
          onBaixarProntuario={baixarProntuarioPdf}
          onBaixarReceita={baixarUltimaReceitaPdf}
        />
      )}

      <ConsultaSteps
        etapas={ETAPAS}
        etapaAtual={etapa}
        modoSomenteLeitura={modoSomenteLeitura}
        onChangeEtapa={setEtapa}
      />

      <ConsultaFeedbackAlerts
        erro={erro}
        sucesso={sucesso}
        onClearErro={() => setErro(null)}
        onClearSucesso={() => setSucesso(null)}
      />

      {/* =========== ETAPA 1: TRIAGEM =========== */}
      {etapa === 0 && (
        <TriagemInicialSection
          modoSomenteLeitura={modoSomenteLeitura}
          isEdicao={isEdicao}
          form={form}
          setCampo={set}
          css={css}
          renderCampo={campo}
          buscaTutor={buscaTutor}
          setBuscaTutor={setBuscaTutor}
          tutorSelecionado={tutorSelecionado}
          setTutorSelecionado={setTutorSelecionado}
          tutoresSugeridos={tutoresSugeridos}
          selecionarTutor={selecionarTutor}
          limparTutor={limparTutor}
          veterinarios={veterinarios}
          listaPetsExpandida={listaPetsExpandida}
          setListaPetsExpandida={setListaPetsExpandida}
          petSelecionadoLabel={petSelecionadoLabel}
          petsDoTutor={petsDoTutor}
          abrirModalNovoPet={abrirModalNovoPet}
        />
      )}

      {/* =========== ETAPA 2: EXAME CLÍNICO =========== */}
      {etapa === 1 && (
        <ExameClinicoSection
          modoSomenteLeitura={modoSomenteLeitura}
          form={form}
          setCampo={set}
          css={css}
          renderCampo={campo}
          consultaIdAtual={consultaIdAtual}
          refreshExamesToken={refreshExamesToken}
          onNovoExame={() => setModalNovoExameAberto(true)}
          abrirFluxoConsulta={abrirFluxoConsulta}
        />
      )}

      {/* =========== ETAPA 3: DIAGNÓSTICO =========== */}
      {etapa === 2 && (
        <DiagnosticoTratamentoSection
          modoSomenteLeitura={modoSomenteLeitura}
          form={form}
          setCampo={set}
          medicamentosCatalogo={medicamentosCatalogo}
          procedimentosCatalogo={procedimentosCatalogo}
          consultaIdAtual={consultaIdAtual}
          timelineConsulta={timelineConsulta}
          carregandoTimeline={carregandoTimeline}
          adicionarItem={adicionarItem}
          removerItem={removerItem}
          setItem={setItem}
          selecionarMedicamentoNoItem={selecionarMedicamentoNoItem}
          recalcularDoseItem={recalcularDoseItem}
          adicionarProcedimento={adicionarProcedimento}
          removerProcedimento={removerProcedimento}
          setProcedimentoItem={setProcedimentoItem}
          selecionarProcedimentoCatalogo={selecionarProcedimentoCatalogo}
          abrirModalInsumoRapido={abrirModalInsumoRapido}
          abrirFluxoConsulta={abrirFluxoConsulta}
          carregarTimelineConsulta={carregarTimelineConsulta}
          onOpenTimelineLink={(link) => navigate(link)}
        />
      )}

      <ConsultaActionsFooter
        modoSomenteLeitura={modoSomenteLeitura}
        etapa={etapa}
        totalEtapas={ETAPAS.length}
        salvando={salvando}
        diagnosticoPreenchido={Boolean(form.diagnostico)}
        onCancel={() => navigate(-1)}
        onVoltarConsultas={() => navigate("/veterinario/consultas")}
        onVoltarEtapa={() => setEtapa((e) => e - 1)}
        onSalvarRascunho={salvarRascunho}
        onFinalizar={finalizar}
      />

      <ConsultaFormModals
        css={css}
        modalInsumoAberto={modalInsumoAberto}
        setModalInsumoAberto={setModalInsumoAberto}
        consultaIdAtual={consultaIdAtual}
        petSelecionadoLabel={petSelecionadoLabel}
        insumoRapidoSelecionado={insumoRapidoSelecionado}
        setInsumoRapidoSelecionado={setInsumoRapidoSelecionado}
        insumoRapidoForm={insumoRapidoForm}
        setInsumoRapidoForm={setInsumoRapidoForm}
        salvarInsumoRapidoConsulta={salvarInsumoRapidoConsulta}
        salvandoInsumoRapido={salvandoInsumoRapido}
        modalNovoPetAberto={modalNovoPetAberto}
        setModalNovoPetAberto={setModalNovoPetAberto}
        tutorSelecionado={tutorSelecionado}
        sugestoesEspecies={sugestoesEspecies}
        handleNovoPetCriado={handleNovoPetCriado}
        modalCalculadoraAberto={modalCalculadoraAberto}
        setModalCalculadoraAberto={setModalCalculadoraAberto}
        calculadoraForm={calculadoraForm}
        setCalculadoraForm={setCalculadoraForm}
        medicamentosCatalogo={medicamentosCatalogo}
        medicamentoCalculadoraSelecionado={medicamentoCalculadoraSelecionado}
        calculadoraResultado={calculadoraResultado}
        modalNovoExameAberto={modalNovoExameAberto}
        setModalNovoExameAberto={setModalNovoExameAberto}
        petId={form.pet_id}
        novoExameForm={novoExameForm}
        setNovoExameForm={setNovoExameForm}
        setNovoExameArquivo={setNovoExameArquivo}
        salvarNovoExameRapido={salvarNovoExameRapido}
        salvandoNovoExame={salvandoNovoExame}
      />
    </div>
  );
}
