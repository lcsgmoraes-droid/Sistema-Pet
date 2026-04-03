import { useCallback, useState } from "react";
import api from "../api";
import CanalDescontos from "./CanalDescontos";
import { formatBRL } from "../utils/formatters";
import { useCampanhasConsultas } from "../hooks/useCampanhasConsultas";
import CampanhasTabsBar from "../components/campanhas/CampanhasTabsBar";
import CampanhasDashboardTab from "../components/campanhas/CampanhasDashboardTab";
import CampanhasListTab from "../components/campanhas/CampanhasListTab";
import CampanhasRetencaoTab from "../components/campanhas/CampanhasRetencaoTab";
import CampanhasDestaqueTab from "../components/campanhas/CampanhasDestaqueTab";
import CampanhasSorteiosTab from "../components/campanhas/CampanhasSorteiosTab";
import CampanhasRankingTab from "../components/campanhas/CampanhasRankingTab";
import CampanhasRelatoriosTab from "../components/campanhas/CampanhasRelatoriosTab";
import CampanhasUnificacaoTab from "../components/campanhas/CampanhasUnificacaoTab";
import CampanhasGestorTab from "../components/campanhas/CampanhasGestorTab";
import CampanhasConfigTab from "../components/campanhas/CampanhasConfigTab";
import CampanhasModalsLayer from "../components/campanhas/CampanhasModalsLayer";
import useCampanhasGestor from "../hooks/useCampanhasGestor";
import useCampanhasConfiguracoes from "../hooks/useCampanhasConfiguracoes";
import useCampanhasGestao from "../hooks/useCampanhasGestao";
import {
  TIPO_LABELS,
  USER_CREATABLE_TYPES,
  CUPOM_STATUS,
  RANK_LABELS,
  hoje,
  primeiroDiaMes,
  createDefaultPremio,
} from "../components/campanhas/campanhasConstants";

export default function Campanhas() {

  // Envio escalonado de inativos
  const [modalEnvioInativos, setModalEnvioInativos] = useState(null); // null | 30 | 60 | 90
  const [envioInativosForm, setEnvioInativosForm] = useState({
    assunto: "Sentimos sua falta! 🐾",
    mensagem: "",
  });
  const [enviandoInativos, setEnviandoInativos] = useState(false);
  const [resultadoEnvioInativos, setResultadoEnvioInativos] = useState(null);

  // Retenção Dinâmica
  const [retencaoEditando, setRetencaoEditando] = useState(null); // null | {} (nova) | {id,...} (existente)
  const [salvandoRetencao, setSalvandoRetencao] = useState(false);
  const [deletandoRetencao, setDeletandoRetencao] = useState(null);

  // Ranking
  // Cupons
  const [anulando, setAnulando] = useState(null);
  const [modalCupomAberto, setModalCupomAberto] = useState(false);
  const [novoCupom, setNovoCupom] = useState({
    coupon_type: "fixed",
    discount_value: "",
    discount_percent: "",
    channel: "pdv",
    valid_until: "",
    min_purchase_value: "",
    customer_id: "",
    descricao: "",
  });
  const [criandoCupom, setCriandoCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState("");

  // Destaque mensal
  const [enviandoDestaque, setEnviandoDestaque] = useState(false);
  const [destaqueResultado, setDestaqueResultado] = useState(null);
  // premiosPorVencedor: { maior_gasto: { tipo_premio, coupon_value, coupon_valid_days, mensagem, mensagem_brinde, retirar_de, retirar_ate }, ... }

  const {
    aba,
    setAba,
    campanhas,
    setCampanhas,
    loadingCampanhas,
    dashboard,
    loadingDashboard,
    retencaoRegras,
    setRetencaoRegras,
    loadingRetencao,
    ranking,
    setRanking,
    loadingRanking,
    filtroNivel,
    setFiltroNivel,
    cupons,
    setCupons,
    loadingCupons,
    filtroCupomStatus,
    setFiltroCupomStatus,
    filtroCupomBusca,
    setFiltroCupomBusca,
    filtroCupomDataInicio,
    setFiltroCupomDataInicio,
    filtroCupomDataFim,
    setFiltroCupomDataFim,
    filtroCupomCampanha,
    setFiltroCupomCampanha,
    cupomDetalhes,
    setCupomDetalhes,
    destaque,
    setDestaque,
    loadingDestaque,
    premiosPorVencedor,
    setPremiosPorVencedor,
    vencedoresSelecionados,
    setVencedoresSelecionados,
    sorteios,
    setSorteios,
    loadingSorteios,
    codigosOffline,
    setCodigosOffline,
    loadingCodigosOffline,
    setLoadingCodigosOffline,
    sugestoes,
    setSugestoes,
    loadingSugestoes,
    relatorio,
    setRelatorio,
    loadingRelatorio,
    relDataInicio,
    setRelDataInicio,
    relDataFim,
    setRelDataFim,
    relTipo,
    setRelTipo,
    rankingConfig,
    setRankingConfig,
    rankingConfigLoading,
    schedulerConfig,
    setSchedulerConfig,
    schedulerConfigLoading,
    carregarCampanhas,
    carregarCupons,
    carregarRetencao,
    carregarRanking,
    carregarDestaque,
    carregarSorteios,
    carregarSugestoes,
    carregarRelatorio,
    carregarRankingConfig,
    carregarSchedulerConfig,
  } = useCampanhasConsultas({
    createDefaultPremio,
    hoje,
    primeiroDiaMes,
  });

  // Sorteios
  const [modalSorteio, setModalSorteio] = useState(false);
  const [novoSorteio, setNovoSorteio] = useState({
    name: "",
    description: "",
    prize_description: "",
    rank_filter: "",
    draw_date: "",
    auto_execute: false,
  });
  const [criandoSorteio, setCriandoSorteio] = useState(false);
  const [erroCriarSorteio, setErroCriarSorteio] = useState("");
  const [executandoSorteio, setExecutandoSorteio] = useState(null);
  const [inscrevendo, setInscrevendo] = useState(null);
  const [sorteioResultado, setSorteioResultado] = useState(null);
  const [modalCodigosOffline, setModalCodigosOffline] = useState(null); // sorteio obj

  // Envio em lote
  const [modalLote, setModalLote] = useState(false);
  const [loteForm, setLoteForm] = useState({
    nivel: "todos",
    assunto: "",
    mensagem: "",
  });
  const [enviandoLote, setEnviandoLote] = useState(false);
  const [resultadoLote, setResultadoLote] = useState(null);

  // Unificação cross-canal
  const [confirmandoMerge, setConfirmandoMerge] = useState(null);
  const [resultadoMerge, setResultadoMerge] = useState(null);

  // Relatórios

  // Fidelidade — carimbos por cliente (legado — mantido para modal existente)
  const [fidClienteId, setFidClienteId] = useState("");
  const [fidCarimbos, setFidCarimbos] = useState(null);
  const [fidLoadingCarimbos, setFidLoadingCarimbos] = useState(false);
  const [fidRemovendo, setFidRemovendo] = useState(null);
  const [fidIncluirEstornados, setFidIncluirEstornados] = useState(false);
  const [fidModalManual, setFidModalManual] = useState(false);
  const [fidLancandoManual, setFidLancandoManual] = useState(false);
  const [fidManualNota, setFidManualNota] = useState("");

  const campanhasGestor = useCampanhasGestor();
  const campanhasConfiguracoes = useCampanhasConfiguracoes({
    rankingConfig,
    setRankingConfig,
    schedulerConfig,
    setSchedulerConfig,
    carregarRanking,
    carregarSchedulerConfig,
  });
  const campanhasGestao = useCampanhasGestao({
    setCampanhas,
    carregarCampanhas,
  });

  const enviarParaInativos = async () => {
    if (
      !envioInativosForm.assunto.trim() ||
      !envioInativosForm.mensagem.trim()
    ) {
      alert("Preencha o assunto e a mensagem antes de enviar.");
      return;
    }
    setEnviandoInativos(true);
    setResultadoEnvioInativos(null);
    try {
      const res = await api.post("/campanhas/notificacoes/inativos", {
        dias_sem_compra: modalEnvioInativos,
        assunto: envioInativosForm.assunto,
        mensagem: envioInativosForm.mensagem,
      });
      setResultadoEnvioInativos(res.data);
    } catch (e) {
      alert("Erro ao enviar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setEnviandoInativos(false);
    }
  };

  const anularCupom = useCallback(async (code) => {
    if (
      !window.confirm(
        `Anular o cupão ${code}? Esta ação não pode ser desfeita.`,
      )
    )
      return;
    setAnulando(code);
    try {
      await api.delete(`/campanhas/cupons/${code}`);
      setCupons((prev) =>
        prev.map((c) => (c.code === code ? { ...c, status: "voided" } : c)),
      );
    } catch (e) {
      alert(e?.response?.data?.detail || "Erro ao anular cupão.");
    } finally {
      setAnulando(null);
    }
  }, []);

  const enviarDestaque = async () => {
    if (!destaque?.vencedores || Object.keys(destaque.vencedores).length === 0)
      return;
    setEnviandoDestaque(true);
    setDestaqueResultado(null);
    try {
      // Monta vencedores com config individual de prêmio (só os selecionados)
      const vencedoresComPremio = {};
      for (const [cat, info] of Object.entries(destaque.vencedores)) {
        if (!vencedoresSelecionados[cat]) continue;
        const premio = premiosPorVencedor[cat] || createDefaultPremio();
        vencedoresComPremio[cat] = {
          ...info,
          tipo_premio: premio.tipo_premio,
          coupon_value: premio.coupon_value,
          coupon_valid_days: premio.coupon_valid_days,
          mensagem:
            premio.tipo_premio === "cupom"
              ? premio.mensagem || ""
              : premio.mensagem_brinde || "",
          mensagem_brinde: premio.mensagem_brinde || "",
          retirar_de: premio.retirar_de || "",
          retirar_ate: premio.retirar_ate || "",
        };
      }
      const res = await api.post("/campanhas/destaque-mensal/enviar", {
        vencedores: vencedoresComPremio,
      });
      setDestaqueResultado(res.data);
    } catch (e) {
      alert(
        "Erro ao enviar prêmios: " + (e?.response?.data?.detail || e.message),
      );
    } finally {
      setEnviandoDestaque(false);
    }
  };

  const confirmarMerge = async (keepId, removeId, motivo) => {
    if (
      !globalThis.confirm(
        `Unificar clientes? O cliente #${removeId} será mesclado no #${keepId}. Os dados de campanhas serão transferidos.`,
      )
    )
      return;
    setConfirmandoMerge(`${keepId}-${removeId}`);
    try {
      const res = await api.post("/campanhas/unificacao/confirmar", {
        customer_keep_id: keepId,
        customer_remove_id: removeId,
        motivo,
      });
      setResultadoMerge(res.data);
      setSugestoes((prev) =>
        prev.filter(
          (s) =>
            !(s.cliente_a.id === keepId && s.cliente_b.id === removeId) &&
            !(s.cliente_a.id === removeId && s.cliente_b.id === keepId),
        ),
      );
    } catch (e) {
      alert("Erro ao unificar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setConfirmandoMerge(null);
    }
  };

  const desfazerMerge = async (mergeId) => {
    if (
      !globalThis.confirm(
        "Desfazer esta unificação? Os dados de campanhas serão restaurados.",
      )
    )
      return;
    try {
      await api.delete(`/campanhas/unificacao/${mergeId}`);
      setResultadoMerge(null);
      carregarSugestoes();
    } catch (e) {
      alert("Erro ao desfazer: " + (e?.response?.data?.detail || e.message));
    }
  };

  const criarSorteio = async () => {
    setErroCriarSorteio("");
    if (!novoSorteio.name.trim()) {
      setErroCriarSorteio("Nome obrigatório.");
      return;
    }
    setCriandoSorteio(true);
    try {
      await api.post("/campanhas/sorteios", novoSorteio);
      setModalSorteio(false);
      setNovoSorteio({
        name: "",
        description: "",
        prize_description: "",
        rank_filter: "",
        draw_date: "",
        auto_execute: false,
      });
      carregarSorteios();
    } catch (e) {
      setErroCriarSorteio(
        e?.response?.data?.detail || "Erro ao criar sorteio.",
      );
    } finally {
      setCriandoSorteio(false);
    }
  };

  const inscreverSorteio = async (drawingId) => {
    setInscrevendo(drawingId);
    try {
      const res = await api.post(`/campanhas/sorteios/${drawingId}/inscrever`);
      setSorteios((prev) =>
        prev.map((s) =>
          s.id === drawingId
            ? {
                ...s,
                status: res.data.status,
                total_participantes: res.data.total_inscritos,
              }
            : s,
        ),
      );
    } catch (e) {
      alert("Erro ao inscrever: " + (e?.response?.data?.detail || e.message));
    } finally {
      setInscrevendo(null);
    }
  };

  const executarSorteio = async (drawingId) => {
    if (!window.confirm("Executar o sorteio agora? Esta ação é irreversível."))
      return;
    setExecutandoSorteio(drawingId);
    try {
      const res = await api.post(`/campanhas/sorteios/${drawingId}/executar`);
      setSorteioResultado(res.data);
      carregarSorteios();
    } catch (e) {
      alert("Erro ao executar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setExecutandoSorteio(null);
    }
  };

  const cancelarSorteio = async (drawingId, nome) => {
    if (!window.confirm(`Cancelar o sorteio "${nome}"?`)) return;
    try {
      await api.delete(`/campanhas/sorteios/${drawingId}`);
      setSorteios((prev) => prev.filter((s) => s.id !== drawingId));
    } catch (e) {
      alert("Erro ao cancelar: " + (e?.response?.data?.detail || e.message));
    }
  };

  const abrirCodigosOffline = async (sorteio) => {
    setModalCodigosOffline(sorteio);
    setCodigosOffline([]);
    setLoadingCodigosOffline(true);
    try {
      const res = await api.get(
        `/campanhas/sorteios/${sorteio.id}/codigos-offline`,
        { params: { limit: 500 } },
      );
      setCodigosOffline(res.data.codigos || res.data);
    } catch (e) {
      alert(
        "Erro ao carregar códigos: " + (e?.response?.data?.detail || e.message),
      );
      setModalCodigosOffline(null);
    } finally {
      setLoadingCodigosOffline(false);
    }
  };

  const enviarLote = async () => {
    if (!loteForm.assunto.trim() || !loteForm.mensagem.trim()) {
      alert("Preencha assunto e mensagem.");
      return;
    }
    setEnviandoLote(true);
    setResultadoLote(null);
    try {
      const res = await api.post("/campanhas/ranking/envio-em-lote", loteForm);
      setResultadoLote(res.data);
    } catch (e) {
      alert("Erro ao enviar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setEnviandoLote(false);
    }
  };

  const carregarCarimbosCliente = async () => {
    if (!fidClienteId) return;
    setFidLoadingCarimbos(true);
    setFidCarimbos(null);
    try {
      const qs = fidIncluirEstornados ? "?incluir_estornados=true" : "";
      const res = await api.get(
        `/campanhas/clientes/${fidClienteId}/carimbos${qs}`,
      );
      setFidCarimbos(res.data);
    } catch (e) {
      alert("Erro: " + (e?.response?.data?.detail || e.message));
    } finally {
      setFidLoadingCarimbos(false);
    }
  };

  const estornarCarimbo = async (stampId) => {
    const motivo = window.prompt("Motivo do estorno (opcional):");
    if (motivo === null) return;
    setFidRemovendo(stampId);
    try {
      const qs = motivo ? `?motivo=${encodeURIComponent(motivo)}` : "";
      await api.delete(`/campanhas/carimbos/${stampId}${qs}`);
      await carregarCarimbosCliente();
    } catch (e) {
      alert("Erro ao estornar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setFidRemovendo(null);
    }
  };

  const lancarCarimboManual = async () => {
    if (!fidClienteId) {
      alert("Digite o ID do cliente primeiro.");
      return;
    }
    setFidLancandoManual(true);
    try {
      await api.post("/campanhas/carimbos/manual", {
        customer_id: Number(fidClienteId),
        nota: fidManualNota || "Carimbo lançado manualmente pelo operador",
      });
      setFidModalManual(false);
      setFidManualNota("");
      await carregarCarimbosCliente();
      alert("✅ Carimbo lançado com sucesso!");
    } catch (e) {
      alert("Erro: " + (e?.response?.data?.detail || e.message));
    } finally {
      setFidLancandoManual(false);
    }
  };

  const salvarRetencao = async (form) => {
    setSalvandoRetencao(true);
    try {
      if (form.id) {
        await api.put(`/campanhas/retencao/${form.id}`, form);
      } else {
        await api.post("/campanhas/retencao", form);
      }
      setRetencaoEditando(null);
      await carregarRetencao();
    } catch (e) {
      alert("Erro ao salvar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setSalvandoRetencao(false);
    }
  };

  const deletarRetencao = async (id) => {
    if (!window.confirm("Remover esta regra de retenção?")) return;
    setDeletandoRetencao(id);
    try {
      await api.delete(`/campanhas/retencao/${id}`);
      await carregarRetencao();
    } catch (e) {
      alert("Erro ao remover: " + (e?.response?.data?.detail || e.message));
    } finally {
      setDeletandoRetencao(null);
    }
  };

  const criarCupomManual = async () => {
    setErroCupom("");
    setCriandoCupom(true);
    try {
      const body = {
        coupon_type: novoCupom.coupon_type,
        channel: novoCupom.channel,
      };
      if (novoCupom.descricao) body.descricao = novoCupom.descricao;
      if (novoCupom.coupon_type === "fixed" && novoCupom.discount_value)
        body.discount_value = Number.parseFloat(
          String(novoCupom.discount_value).replace(",", "."),
        );
      if (novoCupom.coupon_type === "percent" && novoCupom.discount_percent)
        body.discount_percent = Number.parseFloat(novoCupom.discount_percent);
      if (novoCupom.valid_until) body.valid_until = novoCupom.valid_until;
      if (novoCupom.min_purchase_value)
        body.min_purchase_value = Number.parseFloat(
          String(novoCupom.min_purchase_value).replace(",", "."),
        );
      if (novoCupom.customer_id)
        body.customer_id = Number.parseInt(novoCupom.customer_id, 10);

      await api.post("/campanhas/cupons/manual", body);
      setModalCupomAberto(false);
      setNovoCupom({
        coupon_type: "fixed",
        discount_value: "",
        discount_percent: "",
        channel: "pdv",
        valid_until: "",
        min_purchase_value: "",
        customer_id: "",
        descricao: "",
      });
      carregarCupons();
      if (aba !== "cupons") setAba("cupons");
    } catch (e) {
      setErroCupom(e?.response?.data?.detail || "Erro ao criar cupom.");
    } finally {
      setCriandoCupom(false);
    }
  };

  const formatarValorCupom = (cupom) => {
    if (cupom.coupon_type === "percent" && cupom.discount_percent)
      return `${cupom.discount_percent}% off`;
    if (cupom.coupon_type === "fixed" && cupom.discount_value)
      return `R$ ${formatBRL(cupom.discount_value)} off`;
    return "—";
  };

  const formatarData = (iso) => {
    if (!iso) return "—";
    const d = iso.split("T")[0].split("-");
    return `${d[2]}/${d[1]}/${d[0]}`;
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            🎯 Campanhas de Fidelidade
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Gerencie campanhas automáticas, ranking de clientes e cupons.
          </p>
        </div>

      </div>

      <CampanhasTabsBar aba={aba} onChange={setAba} />

      {/* ── ABA: DASHBOARD ── */}
      {aba === "dashboard" && (
        <CampanhasDashboardTab
          loadingDashboard={loadingDashboard}
          dashboard={dashboard}
          onAbrirEnvioInativos={(dias) => {
            setModalEnvioInativos(dias);
            setResultadoEnvioInativos(null);
          }}
          onAbrirAba={setAba}
        />
      )}

      {/* ── Modal: Envio para Inativos ── */}
      {aba === "campanhas" && (
        <CampanhasListTab
          campanhas={campanhas}
          loadingCampanhas={loadingCampanhas}
          campanhaEditando={campanhasGestao.campanhaEditando}
          paramsEditando={campanhasGestao.paramsEditando}
          setParamsEditando={campanhasGestao.setParamsEditando}
          arquivando={campanhasGestao.arquivando}
          toggling={campanhasGestao.toggling}
          salvandoParams={campanhasGestao.salvandoParams}
          tipoLabels={TIPO_LABELS}
          userCreatableTypes={USER_CREATABLE_TYPES}
          formatarParams={campanhasGestao.formatarParams}
          onNovaCampanha={() => {
            campanhasGestao.setErroCriarCampanha("");
            campanhasGestao.setModalCriarCampanha(true);
          }}
          onAbrirEdicao={campanhasGestao.abrirEdicao}
          onFecharEdicao={campanhasGestao.fecharEdicao}
          onArquivarCampanha={campanhasGestao.arquivarCampanha}
          onToggleCampanha={campanhasGestao.toggleCampanha}
          onSalvarParametros={campanhasGestao.salvarParametros}
        />
      )}


      {/* ── ABA: RETENÇÃO DINÂMICA ── */}
      {aba === "retencao" && (
        <CampanhasRetencaoTab
          retencaoEditando={retencaoEditando}
          salvandoRetencao={salvandoRetencao}
          loadingRetencao={loadingRetencao}
          retencaoRegras={retencaoRegras}
          deletandoRetencao={deletandoRetencao}
          onSalvarRetencao={salvarRetencao}
          onCancelarEdicao={() => setRetencaoEditando(null)}
          onNovaRegra={() =>
            setRetencaoEditando({
              name: "",
              inactivity_days: 30,
              coupon_type: "percent",
              coupon_value: 10,
              coupon_valid_days: 7,
              coupon_channel: "all",
              notification_message:
                "Olá, {nome}! Sentimos sua falta. Use o cupom {code} e ganhe {value}% de desconto.",
              priority: 50,
            })
          }
          onEditarRegra={setRetencaoEditando}
          onDeletarRegra={deletarRetencao}
        />
      )}

      {aba === "destaque" && (
        <CampanhasDestaqueTab
          loadingDestaque={loadingDestaque}
          destaque={destaque}
          carregarDestaque={carregarDestaque}
          premiosPorVencedor={premiosPorVencedor}
          setPremiosPorVencedor={setPremiosPorVencedor}
          vencedoresSelecionados={vencedoresSelecionados}
          setVencedoresSelecionados={setVencedoresSelecionados}
          createDefaultPremio={createDefaultPremio}
          destaqueResultado={destaqueResultado}
          setDestaqueResultado={setDestaqueResultado}
          enviarDestaque={enviarDestaque}
          enviandoDestaque={enviandoDestaque}
        />
      )}

      {aba === "sorteios" && (
        <CampanhasSorteiosTab
          loadingSorteios={loadingSorteios}
          sorteios={sorteios}
          sorteioResultado={sorteioResultado}
          setSorteioResultado={setSorteioResultado}
          setErroCriarSorteio={setErroCriarSorteio}
          setModalSorteio={setModalSorteio}
          inscrevendo={inscrevendo}
          inscreverSorteio={inscreverSorteio}
          executandoSorteio={executandoSorteio}
          executarSorteio={executarSorteio}
          cancelarSorteio={cancelarSorteio}
          abrirCodigosOffline={abrirCodigosOffline}
          rankLabels={RANK_LABELS}
        />
      )}

      {/* ── ABA: RANKING ── */}
      {aba === "ranking" && (
        <CampanhasRankingTab
          rankLabels={RANK_LABELS}
          filtroNivel={filtroNivel}
          setFiltroNivel={setFiltroNivel}
          onRecalcularRanking={campanhasConfiguracoes.recalcularRanking}
          loadingRanking={loadingRanking}
          ranking={ranking}
          formatBRL={formatBRL}
          setResultadoLote={setResultadoLote}
          setModalLote={setModalLote}
          rankingConfig={rankingConfig}
          setRankingConfig={setRankingConfig}
          rankingConfigLoading={rankingConfigLoading}
          salvarRankingConfig={campanhasConfiguracoes.salvarRankingConfig}
          rankingConfigSalvando={campanhasConfiguracoes.rankingConfigSalvando}
          campanhas={campanhas}
          filtroCupomBusca={filtroCupomBusca}
          setFiltroCupomBusca={setFiltroCupomBusca}
          filtroCupomDataInicio={filtroCupomDataInicio}
          setFiltroCupomDataInicio={setFiltroCupomDataInicio}
          filtroCupomDataFim={filtroCupomDataFim}
          setFiltroCupomDataFim={setFiltroCupomDataFim}
          filtroCupomCampanha={filtroCupomCampanha}
          setFiltroCupomCampanha={setFiltroCupomCampanha}
          carregarCupons={carregarCupons}
          filtroCupomStatus={filtroCupomStatus}
          setFiltroCupomStatus={setFiltroCupomStatus}
          loadingCupons={loadingCupons}
          cupons={cupons}
          cupomStatus={CUPOM_STATUS}
          cupomDetalhes={cupomDetalhes}
          setCupomDetalhes={setCupomDetalhes}
          anularCupom={anularCupom}
          anulando={anulando}
          formatarValorCupom={formatarValorCupom}
        />
      )}

      {/* ── ABA: RELATÓRIOS ── */}
      {aba === "relatorios" && (
        <CampanhasRelatoriosTab
          relDataInicio={relDataInicio}
          setRelDataInicio={setRelDataInicio}
          relDataFim={relDataFim}
          setRelDataFim={setRelDataFim}
          relTipo={relTipo}
          setRelTipo={setRelTipo}
          relatorio={relatorio}
          loadingRelatorio={loadingRelatorio}
          formatBRL={formatBRL}
          formatarData={formatarData}
        />
      )}

      {/* ── ABA: UNIFICAÇÃO CROSS-CANAL ── */}
      {aba === "unificacao" && (
        <CampanhasUnificacaoTab
          carregarSugestoes={carregarSugestoes}
          loadingSugestoes={loadingSugestoes}
          resultadoMerge={resultadoMerge}
          desfazerMerge={desfazerMerge}
          sugestoes={sugestoes}
          confirmarMerge={confirmarMerge}
          confirmandoMerge={confirmandoMerge}
        />
      )}

      {/* ── MODAL: CRIAR SORTEIO ── */}
      <CampanhasModalsLayer
        {...{
          modalEnvioInativos,
          setModalEnvioInativos,
          resultadoEnvioInativos,
          setResultadoEnvioInativos,
          envioInativosForm,
          setEnvioInativosForm,
          enviandoInativos,
          enviarParaInativos,
          modalSorteio,
          setModalSorteio,
          novoSorteio,
          setNovoSorteio,
          erroCriarSorteio,
          criarSorteio,
          criandoSorteio,
          modalCodigosOffline,
          setModalCodigosOffline,
          loadingCodigosOffline,
          codigosOffline,
          RANK_LABELS,
          fidModalManual,
          setFidModalManual,
          fidClienteId,
          fidManualNota,
          setFidManualNota,
          lancarCarimboManual,
          fidLancandoManual,
          modalLote,
          setModalLote,
          loteForm,
          setLoteForm,
          resultadoLote,
          enviarLote,
          enviandoLote,
          modalCriarCampanha: campanhasGestao.modalCriarCampanha,
          setModalCriarCampanha: campanhasGestao.setModalCriarCampanha,
          novaCampanha: campanhasGestao.novaCampanha,
          setNovaCampanha: campanhasGestao.setNovaCampanha,
          erroCriarCampanha: campanhasGestao.erroCriarCampanha,
          criarCampanha: campanhasGestao.criarCampanha,
          criandoCampanha: campanhasGestao.criandoCampanha,
          modalCupomAberto,
          setModalCupomAberto,
          setErroCupom,
          novoCupom,
          setNovoCupom,
          erroCupom,
          criarCupomManual,
          criandoCupom,
        }}
      />

      {aba === "gestor" && (
        <CampanhasGestorTab
          {...campanhasGestor}
          formatBRL={formatBRL}
          RANK_LABELS={RANK_LABELS}
          CUPOM_STATUS={CUPOM_STATUS}
        />
      )}

      {/* ── ABA: CONFIGURAÇÕES ── */}
      {aba === "config" && (
        <CampanhasConfigTab
          schedulerConfigLoading={schedulerConfigLoading}
          schedulerConfig={campanhasConfiguracoes.schedulerConfig}
          setSchedulerConfig={campanhasConfiguracoes.setSchedulerConfig}
          salvarSchedulerConfig={campanhasConfiguracoes.salvarSchedulerConfig}
          schedulerConfigSalvando={
            campanhasConfiguracoes.schedulerConfigSalvando
          }
        />
      )}

      {/* ── ABA: DESCONTOS POR CANAL ── */}
      {aba === "canais" && <CanalDescontos />}
    </div>
  );
}
