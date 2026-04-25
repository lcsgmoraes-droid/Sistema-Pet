import { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { vetApi } from "./vetApi";
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
  buildConsultaPayload,
  buildFinalizacaoPayload,
  buildInsumoProcedimentoPayload,
  buildItensPrescricao,
  buildNovoExamePayload,
  criarConsultaFormInicial,
  criarInsumoRapidoFormInicial,
  criarNovoExameFormInicial,
  criarPrescricaoItemInicial,
  criarProcedimentoRealizadoInicial,
  mapConsultaParaForm,
} from "./consultaForm/consultaFormState";
import {
  ETAPAS,
  css,
  parseNumero,
} from "./consultaForm/consultaFormUtils";
import useCalculadoraDoseConsulta from "./consultaForm/useCalculadoraDoseConsulta";
import useConsultaCatalogos from "./consultaForm/useConsultaCatalogos";
import useConsultaTimeline from "./consultaForm/useConsultaTimeline";
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
  const [finalizado, setFinalizado] = useState(false);
  const [carregando, setCarregando] = useState(isEdicao);
  const [assinatura, setAssinatura] = useState(null);
  const [baixandoPdf, setBaixandoPdf] = useState(false);
  const [modalCalculadoraAberto, setModalCalculadoraAberto] = useState(false);
  const [modalNovoExameAberto, setModalNovoExameAberto] = useState(false);
  const [salvandoNovoExame, setSalvandoNovoExame] = useState(false);
  const [modalNovoPetAberto, setModalNovoPetAberto] = useState(false);
  const [refreshExamesToken, setRefreshExamesToken] = useState(0);
  const modoSomenteLeitura = isEdicao && finalizado;
  const tituloConsulta = modoSomenteLeitura
    ? "Consulta finalizada (somente visualização)"
    : isEdicao
      ? "Continuar consulta"
      : "Nova consulta";

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

  // Carrega dados ao editar
  useEffect(() => {
    if (!isEdicao) return;
    vetApi
      .obterConsulta(consultaId)
      .then((res) => {
        const c = res.data;
        setForm((prev) => ({ ...prev, ...mapConsultaParaForm(c) }));
        if (c.status === "finalizada") setFinalizado(true);
      })
      .catch(() => setErro("Não foi possível carregar a consulta."))
      .finally(() => setCarregando(false));
  }, [consultaId, isEdicao]);

  useEffect(() => {
    if (!modoSomenteLeitura || !consultaIdAtual) return;
    vetApi
      .validarAssinaturaConsulta(consultaIdAtual)
      .then((res) => setAssinatura(res.data))
      .catch(() => setAssinatura(null));
  }, [modoSomenteLeitura, consultaIdAtual]);

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

  function abrirModalInsumoRapido() {
    if (!consultaIdAtual) {
      setErro("Salve a consulta primeiro para lançar insumos rápidos.");
      return;
    }
    setInsumoRapidoSelecionado(null);
    setInsumoRapidoForm(criarInsumoRapidoFormInicial());
    setModalInsumoAberto(true);
  }

  function abrirModalNovoPet() {
    if (!tutorSelecionado) return;
    setModalNovoPetAberto(true);
  }

  function handleNovoPetCriado(petCriado) {
    if (!petCriado?.id) {
      setModalNovoPetAberto(false);
      return;
    }

    const mensagem = selecionarPetCriado(petCriado);
    setModalNovoPetAberto(false);
    setErro(null);
    setSucesso(mensagem);
  }

  // ---------- Salvar rascunho ----------
  async function salvarRascunho() {
    setSalvando(true);
    setErro(null);
    setSucesso(null);
    try {
      const petSelecionadoAtual = pets.find((p) => String(p.id) === String(form.pet_id));

      if (!petSelecionadoAtual?.cliente_id) {
        setErro("Selecione um pet válido vinculado a um tutor.");
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }

      const payload = buildConsultaPayload({
        form,
        petSelecionadoAtual,
        tipoQuery,
        agendamentoIdQuery,
      });

      if (!consultaIdAtual) {
        const res = await vetApi.criarConsulta(payload);
        setConsultaIdAtual(res.data.id);
        navigate(`/veterinario/consultas/${res.data.id}`, { replace: true });
      } else {
        await vetApi.atualizarConsulta(consultaIdAtual, payload);
      }

      setSucesso(
        etapa < ETAPAS.length - 1
          ? "Rascunho salvo com sucesso."
          : "Rascunho salvo com sucesso. Você pode finalizar quando quiser."
      );

      if (etapa < ETAPAS.length - 1) setEtapa((e) => e + 1);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao salvar. Tente novamente.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setSalvando(false);
    }
  }

  // ---------- Finalizar ----------
  async function finalizar() {
    setSucesso(null);
    if (!consultaIdAtual) { setErro("Salve a consulta antes de finalizar."); return; }
    setSalvando(true);
    setErro(null);
    try {
      // primeiro salva o que está no form
      await vetApi.atualizarConsulta(consultaIdAtual, buildFinalizacaoPayload(form));
      // cria prescrição se houver itens
      if (form.prescricao_itens.length > 0) {
        const itensPrescricao = buildItensPrescricao(form.prescricao_itens);

        if (itensPrescricao.length === 0) {
          setErro("Adicione ao menos 1 item de prescrição com nome e posologia.");
          return;
        }

        await vetApi.criarPrescricao({
          consulta_id: consultaIdAtual,
          pet_id: form.pet_id ? Number.parseInt(form.pet_id) : undefined,
          veterinario_id: form.veterinario_id ? Number.parseInt(form.veterinario_id) : undefined,
          tipo_receituario: "simples",
          itens: itensPrescricao,
        });
      }

      if (form.procedimentos_realizados.length > 0) {
        const procedimentosValidos = form.procedimentos_realizados.filter((item) => item.nome?.trim());
        for (const procedimento of procedimentosValidos) {
          await vetApi.adicionarProcedimento({
            consulta_id: consultaIdAtual,
            catalogo_id: procedimento.catalogo_id ? Number.parseInt(procedimento.catalogo_id) : undefined,
            nome: procedimento.nome,
            descricao: procedimento.descricao || undefined,
            valor: procedimento.valor ? Number(String(procedimento.valor).replace(",", ".")) : undefined,
            observacoes: procedimento.observacoes || undefined,
            realizado: true,
            baixar_estoque: procedimento.baixar_estoque !== false,
          });
        }
      }
      // finaliza (gera hash)
      await vetApi.finalizarConsulta(consultaIdAtual);
      setFinalizado(true);
      await carregarTimelineConsulta();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao finalizar.");
    } finally {
      setSalvando(false);
    }
  }

  // ---------- Prescrição helpers ----------
  function adicionarItem() {
    setForm((prev) => ({
      ...prev,
      prescricao_itens: [
        ...prev.prescricao_itens,
        criarPrescricaoItemInicial(),
      ],
    }));
  }

  function adicionarProcedimento() {
    setForm((prev) => ({
      ...prev,
      procedimentos_realizados: [
        ...prev.procedimentos_realizados,
        criarProcedimentoRealizadoInicial(),
      ],
    }));
  }

  function removerProcedimento(idx) {
    setForm((prev) => ({
      ...prev,
      procedimentos_realizados: prev.procedimentos_realizados.filter((_, i) => i !== idx),
    }));
  }

  function setProcedimentoItem(idx, campo, valor) {
    setForm((prev) => {
      const itens = [...prev.procedimentos_realizados];
      itens[idx] = { ...itens[idx], [campo]: valor };
      return { ...prev, procedimentos_realizados: itens };
    });
  }

  function selecionarProcedimentoCatalogo(idx, catalogoId) {
    const procedimento = procedimentosCatalogo.find((item) => String(item.id) === String(catalogoId));
    setForm((prev) => {
      const itens = [...prev.procedimentos_realizados];
      itens[idx] = {
        ...itens[idx],
        catalogo_id: catalogoId,
        nome: procedimento?.nome || itens[idx].nome,
        descricao: procedimento?.descricao || "",
        valor: procedimento?.valor_padrao != null ? String(procedimento.valor_padrao) : itens[idx].valor,
      };
      return { ...prev, procedimentos_realizados: itens };
    });
  }

  function removerItem(idx) {
    setForm((prev) => ({
      ...prev,
      prescricao_itens: prev.prescricao_itens.filter((_, i) => i !== idx),
    }));
  }

  function setItem(idx, chave, valor) {
    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      itens[idx] = { ...itens[idx], [chave]: valor };
      return { ...prev, prescricao_itens: itens };
    });
  }

  function calcularDosePorPeso(item) {
    const peso = parseNumero(form.peso_kg);
    if (!Number.isFinite(peso) || peso <= 0) {
      setErro("Informe o peso do pet para calcular a dose automaticamente.");
      return null;
    }

    const doseMin = parseNumero(item.dose_minima_mg_kg);
    const doseMax = parseNumero(item.dose_maxima_mg_kg);
    let doseMgKg = Number.isFinite(doseMin) ? doseMin : NaN;

    if (Number.isFinite(doseMin) && Number.isFinite(doseMax)) {
      doseMgKg = (doseMin + doseMax) / 2;
    } else if (!Number.isFinite(doseMgKg) && Number.isFinite(doseMax)) {
      doseMgKg = doseMax;
    }

    if (!Number.isFinite(doseMgKg) || doseMgKg <= 0) {
      setErro("Esse medicamento não tem dose mg/kg cadastrada no catálogo.");
      return null;
    }

    return {
      dose_mg: (doseMgKg * peso).toFixed(2),
      unidade: "mg",
    };
  }

  function selecionarMedicamentoNoItem(idx, medicamentoId) {
    const medicamento = medicamentosCatalogo.find((m) => String(m.id) === String(medicamentoId));
    if (!medicamento) return;

    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      const itemAtual = itens[idx] ?? {};
      const itemAtualizado = {
        ...itemAtual,
        medicamento_id: medicamento.id,
        nome: medicamento.nome ?? itemAtual.nome ?? "",
        principio_ativo: medicamento.principio_ativo ?? itemAtual.principio_ativo ?? "",
        via: medicamento.via_administracao ?? itemAtual.via ?? "oral",
        dose_minima_mg_kg: medicamento.dose_minima_mg_kg,
        dose_maxima_mg_kg: medicamento.dose_maxima_mg_kg,
      };

      const doseCalculada = calcularDosePorPeso(itemAtualizado);
      if (doseCalculada) {
        itemAtualizado.dose_mg = doseCalculada.dose_mg;
        itemAtualizado.unidade = doseCalculada.unidade;
      }

      itens[idx] = itemAtualizado;
      return { ...prev, prescricao_itens: itens };
    });
  }

  function recalcularDoseItem(idx) {
    const item = form.prescricao_itens[idx];
    if (!item) return;

    const doseCalculada = calcularDosePorPeso(item);
    if (!doseCalculada) return;

    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      itens[idx] = {
        ...itens[idx],
        dose_mg: doseCalculada.dose_mg,
        unidade: doseCalculada.unidade,
      };
      return { ...prev, prescricao_itens: itens };
    });
  }

  function baixarArquivo(blob, nomeArquivo) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = nomeArquivo;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  async function baixarProntuarioPdf() {
    if (!consultaIdAtual) return;
    setBaixandoPdf(true);
    setErro(null);
    try {
      const res = await vetApi.baixarProntuarioPdf(consultaIdAtual);
      baixarArquivo(res.data, `prontuario_consulta_${consultaIdAtual}.pdf`);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível baixar o prontuário em PDF.");
    } finally {
      setBaixandoPdf(false);
    }
  }

  async function baixarUltimaReceitaPdf() {
    if (!consultaIdAtual) return;
    setBaixandoPdf(true);
    setErro(null);
    try {
      const lista = await vetApi.listarPrescricoes(consultaIdAtual);
      const prescricoes = Array.isArray(lista.data) ? lista.data : (lista.data?.items ?? []);
      if (!prescricoes.length) {
        setErro("Essa consulta não tem prescrição emitida.");
        return;
      }

      const ultima = prescricoes[prescricoes.length - 1];
      const res = await vetApi.baixarPrescricaoPdf(ultima.id);
      baixarArquivo(res.data, `${ultima.numero || `prescricao_${ultima.id}`}.pdf`);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível baixar a receita em PDF.");
    } finally {
      setBaixandoPdf(false);
    }
  }

  function abrirFluxoConsulta(pathname, extras = {}) {
    if (!contextoConsultaParams) {
      setErro("Salve a consulta com um pet válido antes de abrir outro fluxo clínico.");
      return;
    }
    const params = new URLSearchParams(contextoConsultaParams);
    Object.entries(extras).forEach(([chave, valor]) => {
      if (valor == null || valor === "") return;
      params.set(chave, String(valor));
    });
    navigate(`${pathname}?${params.toString()}`);
  }

  async function salvarNovoExameRapido() {
    if (!form.pet_id || !novoExameForm.nome.trim()) {
      setErro("Selecione o pet e informe o nome do exame.");
      return;
    }

    setSalvandoNovoExame(true);
    setErro(null);
    try {
      const res = await vetApi.criarExame(buildNovoExamePayload({
        form,
        novoExameForm,
        consultaIdAtual,
        agendamentoIdQuery,
      }));

      if (novoExameArquivo) {
        await vetApi.uploadArquivoExame(res.data.id, novoExameArquivo);
        try {
          await vetApi.processarArquivoExameIA(res.data.id);
        } catch (erroProcessamento) {
          console.warn("Nao foi possivel processar o arquivo do exame com IA automaticamente.", erroProcessamento);
        }
      }

      setModalNovoExameAberto(false);
      setNovoExameForm(criarNovoExameFormInicial());
      setNovoExameArquivo(null);
      setRefreshExamesToken((prev) => prev + 1);
      setSucesso("Exame vinculado à consulta com sucesso.");
      await carregarTimelineConsulta();
      setEtapa(1);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível registrar o exame.");
    } finally {
      setSalvandoNovoExame(false);
    }
  }

  async function salvarInsumoRapidoConsulta() {
    if (!consultaIdAtual) {
      setErro("Salve a consulta primeiro para lançar insumos.");
      return;
    }
    if (!insumoRapidoSelecionado?.id) {
      setErro("Selecione o insumo do estoque.");
      return;
    }

    const quantidadeUtilizada = parseNumero(insumoRapidoForm.quantidade_utilizada);
    const quantidadeDesperdicio = parseNumero(insumoRapidoForm.quantidade_desperdicio) || 0;
    const quantidadeConsumida = quantidadeUtilizada + quantidadeDesperdicio;

    if (!Number.isFinite(quantidadeUtilizada) || quantidadeUtilizada <= 0) {
      setErro("Informe a quantidade efetivamente utilizada do insumo.");
      return;
    }
    if (!Number.isFinite(quantidadeConsumida) || quantidadeConsumida <= 0) {
      setErro("A baixa total do insumo precisa ser maior que zero.");
      return;
    }

    setSalvandoInsumoRapido(true);
    setErro(null);
    try {
      await vetApi.adicionarProcedimento(buildInsumoProcedimentoPayload({
        consultaIdAtual,
        insumoRapidoSelecionado,
        insumoRapidoForm,
        quantidadeUtilizada,
        quantidadeDesperdicio,
        quantidadeConsumida,
      }));

      setModalInsumoAberto(false);
      setInsumoRapidoSelecionado(null);
      setInsumoRapidoForm(criarInsumoRapidoFormInicial());
      setSucesso("Insumo lançado com sucesso na consulta.");
      await carregarTimelineConsulta();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível lançar o insumo.");
    } finally {
      setSalvandoInsumoRapido(false);
    }
  }

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
        onAbrirAssistente={() => abrirFluxoConsulta("/veterinario/assistente-ia")}
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
