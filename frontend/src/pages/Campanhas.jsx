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

const TIPO_LABELS = {
  loyalty_stamp: {
    label: "Cartão Fidelidade",
    color: "bg-purple-100 text-purple-800",
    emoji: "🏷️",
  },
  cashback: {
    label: "Cashback",
    color: "bg-green-100 text-green-800",
    emoji: "💰",
  },
  birthday: {
    label: "Aniversário",
    color: "bg-pink-100 text-pink-800",
    emoji: "🎂",
  },
  birthday_customer: {
    label: "Aniversário Cliente",
    color: "bg-pink-100 text-pink-800",
    emoji: "🎂",
  },
  birthday_pet: {
    label: "Aniversário Pet",
    color: "bg-orange-100 text-orange-800",
    emoji: "🐾",
  },
  welcome: {
    label: "Boas-vindas",
    color: "bg-blue-100 text-blue-800",
    emoji: "👋",
  },
  welcome_app: {
    label: "Boas-vindas App",
    color: "bg-blue-100 text-blue-800",
    emoji: "👋",
  },
  inactivity: {
    label: "Clientes Inativos",
    color: "bg-red-100 text-red-800",
    emoji: "😴",
  },
  ranking_monthly: {
    label: "Ranking Mensal",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "🏆",
  },
  quick_repurchase: {
    label: "Recompra Rápida",
    color: "bg-teal-100 text-teal-800",
    emoji: "🔁",
  },
  monthly_highlight: {
    label: "Destaque Mensal",
    color: "bg-amber-100 text-amber-800",
    emoji: "🌟",
  },
  win_back: {
    label: "Reativação",
    color: "bg-red-100 text-red-800",
    emoji: "🔄",
  },
  raffle: {
    label: "Sorteio",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "🎲",
  },
};

const USER_CREATABLE_TYPES = new Set([
  "inactivity",
  "quick_repurchase",
  "bulk_segment",
]);

const CUPOM_STATUS = {
  active: { label: "Ativo", color: "bg-green-100 text-green-700" },
  used: { label: "Usado", color: "bg-gray-100 text-gray-600" },
  expired: { label: "Expirado", color: "bg-red-100 text-red-600" },
  voided: { label: "Cancelado", color: "bg-red-100 text-red-600" },
};

const RANK_LABELS = {
  bronze: {
    label: "Bronze",
    color: "bg-amber-100 text-amber-800",
    border: "border-amber-300",
    emoji: "🥉",
  },
  silver: {
    label: "Prata",
    color: "bg-gray-100 text-gray-700",
    border: "border-gray-400",
    emoji: "🥈",
  },
  gold: {
    label: "Ouro",
    color: "bg-yellow-100 text-yellow-800",
    border: "border-yellow-400",
    emoji: "🥇",
  },
  diamond: {
    label: "Platina",
    color: "bg-purple-100 text-purple-800",
    border: "border-purple-400",
    emoji: "👑",
  },
  platinum: {
    label: "Diamante",
    color: "bg-cyan-100 text-cyan-800",
    border: "border-cyan-400",
    emoji: "💎",
  },
};

// Frases sugeridas para campanhas de aniversário (por tipo de campanha e tipo de presente)
const FRASES_ANIVERSARIO = {
  birthday_customer: {
    brinde:
      "🎂 Feliz aniversário, {nome}! Seu carinho merece uma celebração especial! Apareça na nossa loja para retirar seu presente surpresa. Será um prazer ver você! 🎁",
    cupom:
      "🎉 Feliz aniversário, {nome}! Neste dia tão especial preparamos um cupom de {desconto} de desconto pra você celebrar com muito mimo pro seu pet! Use o código {code}. 🐾",
  },
  birthday_pet: {
    brinde:
      "🐾🎂 Que dia mais fofo! {nome_pet} está fazendo aniversário e a gente não podia deixar passar em branco! Venha buscar o mimo especial que separamos pro seu melhor amigo — tem muito carinho esperando por vocês! Um beijo nas patinhas! 🥳",
    cupom:
      "🎈 O {nome_pet} tá de parabéns hoje, {nome}! Para comemorar esse dia tão especial, preparamos um cupom de {desconto} de desconto pra mimar o(a) aniversariante! Use o código {code} e vai fundo nos mimos! 🐕🎁",
  },
};

const hoje = new Date().toISOString().slice(0, 10);
const primeiroDiaMes = hoje.slice(0, 7) + "-01";

function CampanhaField({
  label,
  id,
  type = "number",
  step = "any",
  min,
  value,
  onChange,
  placeholder,
  colSpan,
}) {
  return (
    <div className={colSpan ? `col-span-${colSpan}` : ""}>
      <label
        htmlFor={id}
        className="block text-xs font-medium text-gray-600 mb-1"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        step={step}
        min={min}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
        className="w-full border rounded-lg px-3 py-1.5 text-sm"
      />
    </div>
  );
}

function CampanhaSel({ label, id, value, onChange, children }) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-xs font-medium text-gray-600 mb-1"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={onChange}
        className="w-full border rounded-lg px-3 py-1.5 text-sm"
      >
        {children}
      </select>
    </div>
  );
}

export default function Campanhas() {

  // Campanhas
  const [toggling, setToggling] = useState(null);
  const [campanhaEditando, setCampanhaEditando] = useState(null);
  const [paramsEditando, setParamsEditando] = useState({});
  const [salvandoParams, setSalvandoParams] = useState(false);

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

  const _defaultPremio = () => ({
    tipo_premio: "cupom",
    coupon_value: 50,
    coupon_valid_days: 10,
    mensagem: "Parabéns! Você foi um dos nossos melhores clientes do mês! 🏆",
    mensagem_brinde:
      "Parabéns! Você foi um dos nossos melhores clientes do mês. Passe em nossa loja e retire seu brinde especial — será um prazer recebê-lo! 🎁",
    retirar_de: "",
    retirar_ate: "",
  });

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
    createDefaultPremio: _defaultPremio,
    hoje,
    primeiroDiaMes,
  });

  // Criar campanha
  const [modalCriarCampanha, setModalCriarCampanha] = useState(false);
  const [novaCampanha, setNovaCampanha] = useState({
    name: "",
    campaign_type: "inactivity",
    params: {},
  });
  const [criandoCampanha, setCriandoCampanha] = useState(false);
  const [erroCriarCampanha, setErroCriarCampanha] = useState("");
  const [arquivando, setArquivando] = useState(null);

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

  // Gestor de Benefícios
  const [gestorSearch, setGestorSearch] = useState("");
  const [gestorSugestoes, setGestorSugestoes] = useState([]);
  const [gestorBuscando, setGestorBuscando] = useState(false);
  const [gestorCliente, setGestorCliente] = useState(null);
  const [gestorSaldo, setGestorSaldo] = useState(null);
  const [gestorCarimbos, setGestorCarimbos] = useState(null);
  const [gestorCupons, setGestorCupons] = useState(null);
  const [gestorCarregando, setGestorCarregando] = useState(false);
  const [gestorSecao, setGestorSecao] = useState(null);
  const [gestorIncluirEstornados, setGestorIncluirEstornados] = useState(false);
  const [gestorCarimboNota, setGestorCarimboNota] = useState("");
  const [gestorLancandoCarimbo, setGestorLancandoCarimbo] = useState(false);
  const [gestorRemovendo, setGestorRemovendo] = useState(null);
  const [gestorCashbackTipo, setGestorCashbackTipo] = useState("credito");
  const [gestorCashbackValor, setGestorCashbackValor] = useState("");
  const [gestorCashbackDesc, setGestorCashbackDesc] = useState("");
  const [gestorLancandoCashback, setGestorLancandoCashback] = useState(false);
  const [gestorAnulando, setGestorAnulando] = useState(null);
  // Gestor — modo Por Campanha
  const [gestorModo, setGestorModo] = useState("cliente"); // 'cliente' | 'campanha'
  const [gestorCampanhaTipo, setGestorCampanhaTipo] = useState("carimbos");
  const [gestorCampanhaLista, setGestorCampanhaLista] = useState(null);
  const [gestorCampanhaCarregando, setGestorCampanhaCarregando] =
    useState(false);

  // Config de ranking
  const [rankingConfigSalvando, setRankingConfigSalvando] = useState(false);

  // Config de horários do scheduler
  const [schedulerConfigSalvando, setSchedulerConfigSalvando] = useState(false);

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
        const premio = premiosPorVencedor[cat] || _defaultPremio();
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

  const criarCampanha = async () => {
    setErroCriarCampanha("");
    if (!novaCampanha.name.trim()) {
      setErroCriarCampanha("Nome obrigatório.");
      return;
    }
    setCriandoCampanha(true);
    try {
      await api.post("/campanhas", {
        name: novaCampanha.name,
        campaign_type: novaCampanha.campaign_type,
        params: {},
        priority: 50,
      });
      setModalCriarCampanha(false);
      setNovaCampanha({ name: "", campaign_type: "inactivity", params: {} });
      carregarCampanhas();
    } catch (e) {
      setErroCriarCampanha(
        e?.response?.data?.detail || "Erro ao criar campanha.",
      );
    } finally {
      setCriandoCampanha(false);
    }
  };

  const arquivarCampanha = async (c) => {
    if (
      !window.confirm(
        `Arquivar a campanha "${c.name}"? Ela ficará inativa e não poderá ser reativada pela interface.`,
      )
    )
      return;
    setArquivando(c.id);
    try {
      await api.delete(`/campanhas/${c.id}`);
      setCampanhas((prev) => prev.filter((x) => x.id !== c.id));
    } catch (e) {
      if (e?.response?.status === 404) {
        // Campanha já não existe no servidor — remove da lista localmente
        setCampanhas((prev) => prev.filter((x) => x.id !== c.id));
        return;
      }
      alert("Erro ao arquivar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setArquivando(null);
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

  const carregarClientesPorCampanha = async (tipo) => {
    setGestorCampanhaCarregando(true);
    setGestorCampanhaLista(null);
    try {
      const res = await api.get(
        `/campanhas/gestor/clientes-por-tipo?tipo=${tipo}`,
      );
      setGestorCampanhaLista(res.data?.clientes || []);
    } catch (e) {
      alert("Erro ao carregar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setGestorCampanhaCarregando(false);
    }
  };

  const abrirClienteNoGestor = (cliente) => {
    setGestorModo("cliente");
    selecionarClienteGestor(cliente);
  };

  // ── Gestor de Benefícios ──────────────────────────────────────────────
  const buscarClientesGestor = async (termo) => {
    if (!termo || termo.length < 2) {
      setGestorSugestoes([]);
      return;
    }
    setGestorBuscando(true);
    try {
      const res = await api.get(
        `/campanhas/clientes/buscar?search=${encodeURIComponent(termo)}&limit=10`,
      );
      setGestorSugestoes(res.data?.clientes || []);
    } catch {
      setGestorSugestoes([]);
    } finally {
      setGestorBuscando(false);
    }
  };

  const selecionarClienteGestor = async (cliente) => {
    setGestorCliente(cliente);
    setGestorSearch(cliente.nome);
    setGestorSugestoes([]);
    setGestorCarregando(true);
    setGestorSecao(null);
    try {
      const [saldoRes, carimbosRes, cuponsRes] = await Promise.all([
        api.get(`/campanhas/clientes/${cliente.id}/saldo`),
        api.get(
          `/campanhas/clientes/${cliente.id}/carimbos?incluir_estornados=true`,
        ),
        api.get(`/campanhas/cupons?customer_id=${cliente.id}`),
      ]);
      setGestorSaldo(saldoRes.data);
      setGestorCarimbos(carimbosRes.data);
      setGestorCupons(cuponsRes.data);
    } catch (e) {
      alert(
        "Erro ao carregar dados: " + (e?.response?.data?.detail || e.message),
      );
    } finally {
      setGestorCarregando(false);
    }
  };

  const recarregarGestor = async () => {
    if (gestorCliente) await selecionarClienteGestor(gestorCliente);
  };

  const lancarCarimboGestor = async () => {
    if (!gestorCliente) return;
    setGestorLancandoCarimbo(true);
    try {
      await api.post("/campanhas/carimbos/manual", {
        customer_id: gestorCliente.id,
        nota: gestorCarimboNota || "Carimbo lançado manualmente pelo operador",
      });
      setGestorCarimboNota("");
      await recarregarGestor();
    } catch (e) {
      alert("Erro: " + (e?.response?.data?.detail || e.message));
    } finally {
      setGestorLancandoCarimbo(false);
    }
  };

  const estornarCarimboGestor = async (stampId) => {
    const motivo = window.prompt("Motivo do estorno (opcional):");
    if (motivo === null) return;
    setGestorRemovendo(stampId);
    try {
      const qs = motivo ? `?motivo=${encodeURIComponent(motivo)}` : "";
      await api.delete(`/campanhas/carimbos/${stampId}${qs}`);
      await recarregarGestor();
    } catch (e) {
      alert("Erro ao estornar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setGestorRemovendo(null);
    }
  };

  const ajustarCashbackGestor = async () => {
    const valor = parseFloat(gestorCashbackValor);
    if (!valor || valor <= 0) {
      alert("Informe um valor maior que zero.");
      return;
    }
    setGestorLancandoCashback(true);
    try {
      const amount = gestorCashbackTipo === "debito" ? -valor : valor;
      await api.post("/campanhas/cashback/manual", {
        customer_id: gestorCliente.id,
        amount,
        description:
          gestorCashbackDesc ||
          (gestorCashbackTipo === "debito"
            ? "Débito manual de cashback"
            : "Crédito manual de cashback"),
      });
      setGestorCashbackValor("");
      setGestorCashbackDesc("");
      await recarregarGestor();
    } catch (e) {
      alert("Erro: " + (e?.response?.data?.detail || e.message));
    } finally {
      setGestorLancandoCashback(false);
    }
  };

  const anularCupomGestor = async (code) => {
    if (!window.confirm(`Anular o cupom ${code}?`)) return;
    setGestorAnulando(code);
    try {
      await api.delete(`/campanhas/cupons/${code}`);
      await recarregarGestor();
    } catch (e) {
      alert("Erro ao anular: " + (e?.response?.data?.detail || e.message));
    } finally {
      setGestorAnulando(null);
    }
  };

  const salvarRankingConfig = async () => {
    setRankingConfigSalvando(true);
    try {
      await api.put("/campanhas/ranking/config", rankingConfig);
      alert("Critérios de ranking salvos!");
    } catch (e) {
      alert("Erro ao salvar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setRankingConfigSalvando(false);
    }
  };

  const salvarSchedulerConfig = async () => {
    setSchedulerConfigSalvando(true);
    try {
      await api.put("/campanhas/config/horarios", schedulerConfig);
      await carregarSchedulerConfig();
      alert("Configurações de envio salvas!");
    } catch (e) {
      alert("Erro ao salvar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setSchedulerConfigSalvando(false);
    }
  };

  const recalcularRanking = async () => {
    try {
      await api.post("/campanhas/ranking/recalcular");
      alert(
        "Recálculo de ranking enfileirado! O worker processará em até 10 segundos.",
      );
      setTimeout(() => carregarRanking(), 3000);
    } catch (e) {
      alert("Erro: " + (e?.response?.data?.detail || e.message));
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

  const toggleCampanha = async (campanha) => {
    setToggling(campanha.id);
    try {
      const res = await api.post(`/campanhas/${campanha.id}/pausar`);
      setCampanhas((prev) =>
        prev.map((c) =>
          c.id === campanha.id ? { ...c, status: res.data.status } : c,
        ),
      );
    } catch (e) {
      console.error("Erro ao alterar status:", e);
    } finally {
      setToggling(null);
    }
  };

  const abrirEdicao = (c) => {
    setCampanhaEditando(c.id);
    const params = { ...c.params };
    // Para campanhas de aniversário, pré-preenche a mensagem sugerida se ainda não foi configurada
    if (
      ["birthday_customer", "birthday_pet"].includes(c.campaign_type) &&
      !params.notification_message
    ) {
      const tipoPresente = params.tipo_presente || "cupom";
      const frases =
        FRASES_ANIVERSARIO[c.campaign_type] ||
        FRASES_ANIVERSARIO.birthday_customer;
      params.notification_message = frases[tipoPresente] || "";
    }
    setParamsEditando(params);
  };

  const fecharEdicao = () => {
    setCampanhaEditando(null);
    setParamsEditando({});
  };

  const salvarParametros = async (c) => {
    setSalvandoParams(true);
    try {
      await api.put(`/campanhas/${c.id}/parametros`, {
        params: paramsEditando,
      });
      setCampanhas((prev) =>
        prev.map((x) => (x.id === c.id ? { ...x, params: paramsEditando } : x)),
      );
      fecharEdicao();
    } catch (e) {
      console.error("Erro ao salvar parâmetros:", e);
      alert("Erro ao salvar os parâmetros.");
    } finally {
      setSalvandoParams(false);
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

  const formatarParams = (tipo, params) => {
    if (!params) return "—";
    if (tipo === "loyalty_stamp")
      return `${params.stamps_to_complete || "?"} carimbos → R$ ${formatBRL(params.reward_value || 0)} de recompensa`;
    if (tipo === "cashback")
      return `Bronze ${params.bronze_percent || 0}% / Prata ${params.silver_percent || 0}% / Ouro ${params.gold_percent || 0}%`;
    if (["birthday", "birthday_customer", "birthday_pet"].includes(tipo)) {
      const tipoPresente = params.tipo_presente || "cupom";
      if (tipoPresente === "brinde") return "🎁 Brinde na loja";
      return params.coupon_type === "percent"
        ? `🎫 Cupom ${params.coupon_value || "?"}% de desconto · ${params.coupon_valid_days || "?"} dias`
        : `🎫 Cupom R$ ${formatBRL(params.coupon_value || 0)} de desconto · ${params.coupon_valid_days || "?"} dias`;
    }
    if (tipo === "inactivity") {
      const valInact =
        params.coupon_type === "fixed"
          ? `R$ ${formatBRL(params.coupon_value || 0)}`
          : `${params.coupon_value || "?"}%`;
      return `Inativo ${params.inactivity_days || "?"} dias → ${valInact} desconto`;
    }
    if (tipo === "welcome" || tipo === "welcome_app")
      return `Boas-vindas: R$ ${formatBRL(params.coupon_value || 0)} de bônus`;
    if (tipo === "ranking_monthly")
      return `${Object.keys(params).length} níveis configurados`;
    if (tipo === "quick_repurchase") {
      const val =
        params.coupon_type === "fixed"
          ? `R$ ${formatBRL(params.coupon_value || 0)}`
          : `${params.coupon_value || "?"}%`;
      return `Pós-compra: ${val} desconto • ${params.coupon_valid_days || "?"} dias`;
    }
    return JSON.stringify(params).slice(0, 60) + "...";
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

  // ── Formulários de parâmetros por tipo de campanha ──
  const renderFormCampaign = (c) => {
    const tipo = c.campaign_type;
    const set = (key, val) => setParamsEditando((p) => ({ ...p, [key]: val }));
    const num = (key) => paramsEditando[key] ?? "";
    const str = (key) => paramsEditando[key] ?? "";

    if (tipo === "loyalty_stamp")
      return (
        <div className="grid grid-cols-2 gap-3">
          <CampanhaField
            label="Compra mínima (R$)"
            id="p-min"
            value={num("min_purchase_value")}
            onChange={(e) =>
              set("min_purchase_value", Number.parseFloat(e.target.value) || 0)
            }
          />
          <CampanhaField
            label="Carimbos para completar"
            id="p-stamps"
            step="1"
            min="1"
            value={num("stamps_to_complete")}
            onChange={(e) =>
              set(
                "stamps_to_complete",
                Number.parseInt(e.target.value, 10) || 0,
              )
            }
          />
          <CampanhaSel
            label="Tipo de recompensa"
            id="p-reward-type"
            value={str("reward_type") || "coupon"}
            onChange={(e) => set("reward_type", e.target.value)}
          >
            <option value="coupon">Cupom de desconto</option>
            <option value="credit">Crédito cashback</option>
          </CampanhaSel>
          <CampanhaField
            label="Valor da recompensa (R$)"
            id="p-reward-val"
            value={num("reward_value")}
            onChange={(e) =>
              set("reward_value", Number.parseFloat(e.target.value) || 0)
            }
          />
          <CampanhaField
            label="Carimbo intermediário (0 = sem)"
            id="p-inter"
            step="1"
            min="0"
            value={num("intermediate_stamp") || 0}
            onChange={(e) =>
              set(
                "intermediate_stamp",
                Number.parseInt(e.target.value, 10) || 0,
              )
            }
          />
          <CampanhaField
            label="Recompensa intermediária (R$)"
            id="p-inter-val"
            value={num("intermediate_reward_value") || 0}
            onChange={(e) =>
              set(
                "intermediate_reward_value",
                Number.parseFloat(e.target.value) || 0,
              )
            }
          />
          <CampanhaField
            label="Validade do cupom (dias)"
            id="p-validity"
            step="1"
            min="1"
            value={num("coupon_days_valid") || 30}
            onChange={(e) =>
              set(
                "coupon_days_valid",
                Number.parseInt(e.target.value, 10) || 30,
              )
            }
          />
          <div className="col-span-2">
            <CampanhaSel
              label="Quem participa?"
              id="p-rank-filter"
              value={str("rank_filter") || "all"}
              onChange={(e) => set("rank_filter", e.target.value)}
            >
              <option value="all">Todos os clientes</option>
              <option value="sem_rank">Sem classificação</option>
              <option value="bronze">Bronze</option>
              <option value="silver">Prata</option>
              <option value="gold">Ouro</option>
              <option value="diamond">Diamante</option>
              <option value="platinum">Platina</option>
            </CampanhaSel>
          </div>
        </div>
      );

    if (tipo === "cashback") {
      const levels = [
        { key: "bronze_percent", label: "🥉 Bronze" },
        { key: "silver_percent", label: "🥈 Prata" },
        { key: "gold_percent", label: "🥇 Ouro" },
        { key: "diamond_percent", label: "👑 Platina" },
        { key: "platinum_percent", label: "💎 Diamante" },
      ];
      const canais = [
        { key: "pdv_bonus_percent", label: "🖥️ PDV (bônus %)" },
        { key: "app_bonus_percent", label: "📱 App (bônus %)" },
        { key: "ecommerce_bonus_percent", label: "🛒 Ecommerce (bônus %)" },
      ];
      return (
        <div className="space-y-4">
          <div>
            <p className="text-xs text-gray-500 mb-2">
              % base por nível de ranking (crédito automático em toda compra).
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {levels.map((lv) => (
                <CampanhaField
                  key={lv.key}
                  label={`${lv.label} (%)`}
                  id={`p-${lv.key}`}
                  value={num(lv.key)}
                  onChange={(e) =>
                    set(lv.key, Number.parseFloat(e.target.value) || 0)
                  }
                />
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-2">
              Bônus adicional por canal (somado ao % do nível). Ex: App +1%
              incentiva uso do aplicativo.
            </p>
            <div className="grid grid-cols-3 gap-3">
              {canais.map((c) => (
                <CampanhaField
                  key={c.key}
                  label={c.label}
                  id={`p-${c.key}`}
                  value={num(c.key)}
                  onChange={(e) =>
                    set(c.key, Number.parseFloat(e.target.value) || 0)
                  }
                />
              ))}
            </div>
          </div>
          <div className="border-t pt-4">
            <p className="text-xs font-semibold text-gray-700 mb-2">
              ⏰ Validade e Alertas
            </p>
            <div className="grid grid-cols-2 gap-3">
              <CampanhaField
                label="Validade do cashback (dias, 0 = sem prazo)"
                id="p-cashback_valid_days"
                value={num("cashback_valid_days")}
                onChange={(e) =>
                  set(
                    "cashback_valid_days",
                    Number.parseInt(e.target.value) || 0,
                  )
                }
              />
              <CampanhaField
                label="Alertar cliente X dias antes de expirar"
                id="p-cashback_alerta_dias"
                value={num("cashback_alerta_dias") || 7}
                onChange={(e) =>
                  set(
                    "cashback_alerta_dias",
                    Number.parseInt(e.target.value) || 7,
                  )
                }
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Se validade = 0, o cashback nunca expira. O alerta envia e-mail ou
              push ao cliente quando faltar X dias para o vencimento.
            </p>
          </div>
        </div>
      );
    }

    if (["birthday", "birthday_customer", "birthday_pet"].includes(tipo)) {
      const frases =
        FRASES_ANIVERSARIO[tipo] || FRASES_ANIVERSARIO.birthday_customer;
      const tipoPresente = str("tipo_presente") || "cupom";
      const fraseSugerida = frases[tipoPresente] || "";
      const ehPet = tipo === "birthday_pet";

      return (
        <div className="space-y-4">
          {/* Tipo de presente */}
          <div>
            <p className="text-xs font-semibold text-gray-700 mb-2">
              🎁 O que o cliente recebe no aniversário?
            </p>
            <div className="flex gap-4">
              {[
                { value: "cupom", label: "🎫 Cupom de desconto" },
                { value: "brinde", label: "🎁 Brinde na loja" },
              ].map((opt) => (
                <label
                  key={opt.value}
                  className={`flex items-center gap-2 cursor-pointer px-4 py-2 rounded-lg border-2 transition-colors ${
                    tipoPresente === opt.value
                      ? "border-blue-500 bg-blue-50 text-blue-800 font-semibold"
                      : "border-gray-200 bg-white text-gray-600 hover:border-blue-300"
                  }`}
                >
                  <input
                    type="radio"
                    name={`tipo_presente_${tipo}`}
                    value={opt.value}
                    checked={tipoPresente === opt.value}
                    onChange={() => {
                      set("tipo_presente", opt.value);
                      // Atualiza a frase automaticamente ao trocar o tipo
                      set("notification_message", frases[opt.value] || "");
                    }}
                    className="accent-blue-600 w-4 h-4"
                  />
                  <span className="text-sm">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Campos do cupom (visível apenas se tipo_presente = cupom) */}
          {tipoPresente === "cupom" && (
            <div className="grid grid-cols-2 gap-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
              <CampanhaSel
                label="Tipo de desconto"
                id="p-bday-type"
                value={str("coupon_type") || "fixed"}
                onChange={(e) => set("coupon_type", e.target.value)}
              >
                <option value="fixed">Valor fixo (R$)</option>
                <option value="percent">Percentual (%)</option>
              </CampanhaSel>
              <CampanhaField
                label={
                  str("coupon_type") === "percent"
                    ? "Percentual (%)"
                    : "Valor (R$)"
                }
                id="p-bday-val"
                value={num("coupon_value")}
                onChange={(e) =>
                  set("coupon_value", Number.parseFloat(e.target.value) || 0)
                }
              />
              <CampanhaField
                label="Validade (dias)"
                id="p-bday-days"
                step="1"
                min="1"
                value={num("coupon_valid_days") || 3}
                onChange={(e) =>
                  set(
                    "coupon_valid_days",
                    Number.parseInt(e.target.value, 10) || 3,
                  )
                }
              />
              <CampanhaSel
                label="Canal"
                id="p-bday-canal"
                value={str("coupon_channel") || "all"}
                onChange={(e) => set("coupon_channel", e.target.value)}
              >
                <option value="all">Todos os canais</option>
                <option value="pdv">PDV</option>
                <option value="app">App</option>
                <option value="ecommerce">Ecommerce</option>
              </CampanhaSel>
            </div>
          )}

          {/* Mensagem personalizada */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label
                htmlFor="p-bday-msg"
                className="block text-xs font-semibold text-gray-700"
              >
                ✉️ Mensagem enviada ao cliente
              </label>
              <button
                type="button"
                onClick={() => set("notification_message", fraseSugerida)}
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                🔄 Usar frase sugerida
              </button>
            </div>
            <textarea
              id="p-bday-msg"
              rows={4}
              value={str("notification_message")}
              onChange={(e) => set("notification_message", e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            <p className="text-xs text-gray-400 mt-1">
              Variáveis disponíveis:{" "}
              <code className="bg-gray-100 px-1 rounded">{"{nome}"}</code>
              {ehPet && (
                <>
                  {" "}
                  <code className="bg-gray-100 px-1 rounded">
                    {"{nome_pet}"}
                  </code>
                </>
              )}
              {tipoPresente === "cupom" && (
                <>
                  {" "}
                  <code className="bg-gray-100 px-1 rounded">
                    {"{code}"}
                  </code>{" "}
                  <code className="bg-gray-100 px-1 rounded">
                    {"{desconto}"}
                  </code>
                </>
              )}
            </p>
          </div>
        </div>
      );
    }

    if (tipo === "quick_repurchase")
      return (
        <div className="grid grid-cols-2 gap-3">
          <CampanhaField
            label="Compra mínima (R$)"
            id="p-qr-min"
            value={num("min_purchase_value")}
            onChange={(e) =>
              set("min_purchase_value", Number.parseFloat(e.target.value) || 0)
            }
          />
          <CampanhaSel
            label="Tipo de desconto"
            id="p-qr-type"
            value={str("coupon_type") || "percent"}
            onChange={(e) => set("coupon_type", e.target.value)}
          >
            <option value="percent">Percentual (%)</option>
            <option value="fixed">Valor fixo (R$)</option>
          </CampanhaSel>
          <CampanhaField
            label={
              str("coupon_type") === "fixed" ? "Valor (R$)" : "Percentual (%)"
            }
            id="p-qr-val"
            value={num("coupon_value")}
            onChange={(e) =>
              set("coupon_value", Number.parseFloat(e.target.value) || 0)
            }
          />
          <CampanhaField
            label="Validade do cupom (dias)"
            id="p-qr-days"
            step="1"
            min="1"
            value={num("coupon_valid_days") || 15}
            onChange={(e) =>
              set(
                "coupon_valid_days",
                Number.parseInt(e.target.value, 10) || 15,
              )
            }
          />
          <CampanhaSel
            label="Canal"
            id="p-qr-chan"
            value={str("coupon_channel") || "pdv"}
            onChange={(e) => set("coupon_channel", e.target.value)}
          >
            <option value="pdv">PDV</option>
            <option value="app">App</option>
            <option value="ecommerce">E-commerce</option>
            <option value="all">Todos</option>
          </CampanhaSel>
          <div className="col-span-2">
            <label
              htmlFor="p-qr-msg"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Mensagem personalizada
            </label>
            <input
              id="p-qr-msg"
              type="text"
              value={str("notification_message")}
              onChange={(e) => set("notification_message", e.target.value)}
              placeholder="Ex: Obrigado pela compra! Use o cupom {code} na próxima visita."
              className="w-full border rounded-lg px-3 py-1.5 text-sm"
            />
          </div>
        </div>
      );

    if (tipo === "inactivity")
      return (
        <div className="grid grid-cols-2 gap-3">
          <CampanhaField
            label="Dias de inatividade"
            id="p-inact-days"
            step="1"
            min="1"
            value={num("inactivity_days") || 30}
            onChange={(e) =>
              set("inactivity_days", Number.parseInt(e.target.value, 10) || 30)
            }
          />
          <CampanhaSel
            label="Tipo de desconto"
            id="p-inact-type"
            value={str("coupon_type") || "percent"}
            onChange={(e) => set("coupon_type", e.target.value)}
          >
            <option value="fixed">Valor fixo (R$)</option>
            <option value="percent">Percentual (%)</option>
          </CampanhaSel>
          <CampanhaField
            label={
              str("coupon_type") === "fixed" ? "Valor (R$)" : "Percentual (%)"
            }
            id="p-inact-val"
            value={num("coupon_value")}
            onChange={(e) =>
              set("coupon_value", Number.parseFloat(e.target.value) || 0)
            }
          />
          <CampanhaField
            label="Validade do cupom (dias)"
            id="p-inact-valid"
            step="1"
            min="1"
            value={num("coupon_valid_days") || 7}
            onChange={(e) =>
              set("coupon_valid_days", Number.parseInt(e.target.value, 10) || 7)
            }
          />
          <div className="col-span-2">
            <label
              htmlFor="p-inact-msg"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Mensagem
            </label>
            <input
              id="p-inact-msg"
              type="text"
              value={str("notification_message")}
              onChange={(e) => set("notification_message", e.target.value)}
              placeholder="Ex: Sentimos sua falta! Use este cupom."
              className="w-full border rounded-lg px-3 py-1.5 text-sm"
            />
          </div>
        </div>
      );

    if (tipo === "welcome" || tipo === "welcome_app")
      return (
        <div className="grid grid-cols-2 gap-3">
          <CampanhaSel
            label="Tipo de desconto"
            id="p-wel-type"
            value={str("coupon_type") || "fixed"}
            onChange={(e) => set("coupon_type", e.target.value)}
          >
            <option value="fixed">Valor fixo (R$)</option>
            <option value="percent">Percentual (%)</option>
          </CampanhaSel>
          <CampanhaField
            label={
              str("coupon_type") === "percent" ? "Percentual (%)" : "Valor (R$)"
            }
            id="p-wel-val"
            value={num("coupon_value")}
            onChange={(e) =>
              set("coupon_value", Number.parseFloat(e.target.value) || 0)
            }
          />
          <CampanhaField
            label="Validade (dias)"
            id="p-wel-days"
            step="1"
            min="1"
            value={num("coupon_valid_days") || 30}
            onChange={(e) =>
              set(
                "coupon_valid_days",
                Number.parseInt(e.target.value, 10) || 30,
              )
            }
          />
          <CampanhaSel
            label="Canal"
            id="p-wel-chan"
            value={str("coupon_channel") || "app"}
            onChange={(e) => set("coupon_channel", e.target.value)}
          >
            <option value="app">App</option>
            <option value="pdv">PDV</option>
            <option value="ecommerce">E-commerce</option>
          </CampanhaSel>
        </div>
      );

    if (tipo === "ranking_monthly") {
      const levels = ["bronze", "silver", "gold", "diamond", "platinum"];
      const lvLabels = {
        bronze: "🥉 Bronze",
        silver: "🥈 Prata",
        gold: "🥇 Ouro",
        diamond: "👑 Platina",
        platinum: "💎 Diamante",
      };
      const getLv = (lv) => paramsEditando[lv] || {};
      const setLv = (lv, key, val) =>
        setParamsEditando((p) => ({ ...p, [lv]: { ...p[lv], [key]: val } }));
      return (
        <div>
          <p className="text-xs text-gray-500 mb-2">
            Critérios mínimos para cada nível. Recalculado mensalmente.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Nível
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Gasto mín. (R$)
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Compras mín.
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Meses ativos mín.
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {levels.map((lv) => (
                  <tr key={lv}>
                    <td className="px-3 py-2 font-medium text-sm">
                      {lvLabels[lv]}
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        step="any"
                        min="0"
                        value={getLv(lv).min_spent ?? ""}
                        onChange={(e) =>
                          setLv(
                            lv,
                            "min_spent",
                            Number.parseFloat(e.target.value) || 0,
                          )
                        }
                        className="w-24 border rounded px-2 py-1 text-xs"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        step="1"
                        min="0"
                        value={getLv(lv).min_purchases ?? ""}
                        onChange={(e) =>
                          setLv(
                            lv,
                            "min_purchases",
                            Number.parseInt(e.target.value, 10) || 0,
                          )
                        }
                        className="w-20 border rounded px-2 py-1 text-xs"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        step="1"
                        min="0"
                        value={getLv(lv).min_active_months ?? ""}
                        onChange={(e) =>
                          setLv(
                            lv,
                            "min_active_months",
                            Number.parseInt(e.target.value, 10) || 0,
                          )
                        }
                        className="w-20 border rounded px-2 py-1 text-xs"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }

    // fallback: editor genérico
    return (
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(paramsEditando).map(([chave, valor]) => (
          <div key={chave}>
            <label
              htmlFor={`param-${chave}`}
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              {chave}
            </label>
            <input
              id={`param-${chave}`}
              type="text"
              value={
                typeof valor === "object"
                  ? JSON.stringify(valor)
                  : String(valor ?? "")
              }
              onChange={(e) =>
                setParamsEditando((prev) => ({
                  ...prev,
                  [chave]: e.target.value,
                }))
              }
              className="w-full border rounded-lg px-3 py-1.5 text-sm"
            />
          </div>
        ))}
      </div>
    );
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
          campanhaEditando={campanhaEditando}
          arquivando={arquivando}
          toggling={toggling}
          salvandoParams={salvandoParams}
          tipoLabels={TIPO_LABELS}
          userCreatableTypes={USER_CREATABLE_TYPES}
          formatarParams={formatarParams}
          renderFormCampaign={renderFormCampaign}
          onNovaCampanha={() => {
            setErroCriarCampanha("");
            setModalCriarCampanha(true);
          }}
          onAbrirEdicao={abrirEdicao}
          onFecharEdicao={fecharEdicao}
          onArquivarCampanha={arquivarCampanha}
          onToggleCampanha={toggleCampanha}
          onSalvarParametros={salvarParametros}
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
                "Ol?, {nome}! Sentimos sua falta. Use o cupom {code} e ganhe {value}% de desconto.",
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
          createDefaultPremio={_defaultPremio}
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
          onRecalcularRanking={recalcularRanking}
          loadingRanking={loadingRanking}
          ranking={ranking}
          formatBRL={formatBRL}
          setResultadoLote={setResultadoLote}
          setModalLote={setModalLote}
          rankingConfig={rankingConfig}
          setRankingConfig={setRankingConfig}
          rankingConfigLoading={rankingConfigLoading}
          salvarRankingConfig={salvarRankingConfig}
          rankingConfigSalvando={rankingConfigSalvando}
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
          modalCriarCampanha,
          setModalCriarCampanha,
          novaCampanha,
          setNovaCampanha,
          erroCriarCampanha,
          criarCampanha,
          criandoCampanha,
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
          gestorModo={gestorModo}
          setGestorModo={setGestorModo}
          gestorSearch={gestorSearch}
          setGestorSearch={setGestorSearch}
          buscarClientesGestor={buscarClientesGestor}
          setGestorSugestoes={setGestorSugestoes}
          gestorBuscando={gestorBuscando}
          gestorSugestoes={gestorSugestoes}
          selecionarClienteGestor={selecionarClienteGestor}
          gestorCampanhaTipo={gestorCampanhaTipo}
          setGestorCampanhaTipo={setGestorCampanhaTipo}
          carregarClientesPorCampanha={carregarClientesPorCampanha}
          gestorCampanhaCarregando={gestorCampanhaCarregando}
          gestorCampanhaLista={gestorCampanhaLista}
          abrirClienteNoGestor={abrirClienteNoGestor}
          gestorCarregando={gestorCarregando}
          gestorCliente={gestorCliente}
          gestorSaldo={gestorSaldo}
          gestorCarimbos={gestorCarimbos}
          gestorSecao={gestorSecao}
          setGestorSecao={setGestorSecao}
          gestorIncluirEstornados={gestorIncluirEstornados}
          setGestorIncluirEstornados={setGestorIncluirEstornados}
          gestorCarimboNota={gestorCarimboNota}
          setGestorCarimboNota={setGestorCarimboNota}
          gestorLancandoCarimbo={gestorLancandoCarimbo}
          lancarCarimboGestor={lancarCarimboGestor}
          gestorRemovendo={gestorRemovendo}
          estornarCarimboGestor={estornarCarimboGestor}
          formatBRL={formatBRL}
          RANK_LABELS={RANK_LABELS}
          gestorCashbackTipo={gestorCashbackTipo}
          setGestorCashbackTipo={setGestorCashbackTipo}
          gestorCashbackValor={gestorCashbackValor}
          setGestorCashbackValor={setGestorCashbackValor}
          gestorCashbackDesc={gestorCashbackDesc}
          setGestorCashbackDesc={setGestorCashbackDesc}
          gestorLancandoCashback={gestorLancandoCashback}
          ajustarCashbackGestor={ajustarCashbackGestor}
          gestorCupons={gestorCupons}
          CUPOM_STATUS={CUPOM_STATUS}
          anularCupomGestor={anularCupomGestor}
          gestorAnulando={gestorAnulando}
        />
      )}

      {/* ── ABA: CONFIGURAÇÕES ── */}
      {aba === "config" && (
        <CampanhasConfigTab
          schedulerConfigLoading={schedulerConfigLoading}
          schedulerConfig={schedulerConfig}
          setSchedulerConfig={setSchedulerConfig}
          salvarSchedulerConfig={salvarSchedulerConfig}
          schedulerConfigSalvando={schedulerConfigSalvando}
        />
      )}

      {/* ── ABA: DESCONTOS POR CANAL ── */}
      {aba === "canais" && <CanalDescontos />}
    </div>
  );
}
