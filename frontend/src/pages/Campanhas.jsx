import { Fragment, useCallback, useState } from "react";
import api from "../api";
import CanalDescontos from "./CanalDescontos";
import { formatBRL } from "../utils/formatters";
import { useCampanhasConsultas } from "../hooks/useCampanhasConsultas";
import CampanhasTabsBar from "../components/campanhas/CampanhasTabsBar";
import CampanhasDashboardTab from "../components/campanhas/CampanhasDashboardTab";
import CampanhasListTab from "../components/campanhas/CampanhasListTab";
import CampanhasRetencaoTab from "../components/campanhas/CampanhasRetencaoTab";
import CampanhasDestaqueTab from "../components/campanhas/CampanhasDestaqueTab";

const TIPO_LABELS = {
  loyalty_stamp: {
    label: "CartÃƒÂ£o Fidelidade",
    color: "bg-purple-100 text-purple-800",
    emoji: "Ã°Å¸ÂÂ·Ã¯Â¸Â",
  },
  cashback: {
    label: "Cashback",
    color: "bg-green-100 text-green-800",
    emoji: "Ã°Å¸â€™Â°",
  },
  birthday: {
    label: "AniversÃƒÂ¡rio",
    color: "bg-pink-100 text-pink-800",
    emoji: "Ã°Å¸Å½â€š",
  },
  birthday_customer: {
    label: "AniversÃƒÂ¡rio Cliente",
    color: "bg-pink-100 text-pink-800",
    emoji: "Ã°Å¸Å½â€š",
  },
  birthday_pet: {
    label: "AniversÃƒÂ¡rio Pet",
    color: "bg-orange-100 text-orange-800",
    emoji: "Ã°Å¸ÂÂ¾",
  },
  welcome: {
    label: "Boas-vindas",
    color: "bg-blue-100 text-blue-800",
    emoji: "Ã°Å¸â€˜â€¹",
  },
  welcome_app: {
    label: "Boas-vindas App",
    color: "bg-blue-100 text-blue-800",
    emoji: "Ã°Å¸â€˜â€¹",
  },
  inactivity: {
    label: "Clientes Inativos",
    color: "bg-red-100 text-red-800",
    emoji: "Ã°Å¸ËœÂ´",
  },
  ranking_monthly: {
    label: "Ranking Mensal",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "Ã°Å¸Ââ€ ",
  },
  quick_repurchase: {
    label: "Recompra RÃƒÂ¡pida",
    color: "bg-teal-100 text-teal-800",
    emoji: "Ã°Å¸â€Â",
  },
  monthly_highlight: {
    label: "Destaque Mensal",
    color: "bg-amber-100 text-amber-800",
    emoji: "Ã°Å¸Å’Å¸",
  },
  win_back: {
    label: "ReativaÃƒÂ§ÃƒÂ£o",
    color: "bg-red-100 text-red-800",
    emoji: "Ã°Å¸â€â€ž",
  },
  raffle: {
    label: "Sorteio",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "Ã°Å¸Å½Â²",
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
    emoji: "Ã°Å¸Â¥â€°",
  },
  silver: {
    label: "Prata",
    color: "bg-gray-100 text-gray-700",
    border: "border-gray-400",
    emoji: "Ã°Å¸Â¥Ë†",
  },
  gold: {
    label: "Ouro",
    color: "bg-yellow-100 text-yellow-800",
    border: "border-yellow-400",
    emoji: "Ã°Å¸Â¥â€¡",
  },
  diamond: {
    label: "Platina",
    color: "bg-purple-100 text-purple-800",
    border: "border-purple-400",
    emoji: "Ã°Å¸â€˜â€˜",
  },
  platinum: {
    label: "Diamante",
    color: "bg-cyan-100 text-cyan-800",
    border: "border-cyan-400",
    emoji: "Ã°Å¸â€™Å½",
  },
};

// Frases sugeridas para campanhas de aniversÃƒÂ¡rio (por tipo de campanha e tipo de presente)
const FRASES_ANIVERSARIO = {
  birthday_customer: {
    brinde:
      "Ã°Å¸Å½â€š Feliz aniversÃƒÂ¡rio, {nome}! Seu carinho merece uma celebraÃƒÂ§ÃƒÂ£o especial! ApareÃƒÂ§a na nossa loja para retirar seu presente surpresa. SerÃƒÂ¡ um prazer ver vocÃƒÂª! Ã°Å¸Å½Â",
    cupom:
      "Ã°Å¸Å½â€° Feliz aniversÃƒÂ¡rio, {nome}! Neste dia tÃƒÂ£o especial preparamos um cupom de {desconto} de desconto pra vocÃƒÂª celebrar com muito mimo pro seu pet! Use o cÃƒÂ³digo {code}. Ã°Å¸ÂÂ¾",
  },
  birthday_pet: {
    brinde:
      "Ã°Å¸ÂÂ¾Ã°Å¸Å½â€š Que dia mais fofo! {nome_pet} estÃƒÂ¡ fazendo aniversÃƒÂ¡rio e a gente nÃƒÂ£o podia deixar passar em branco! Venha buscar o mimo especial que separamos pro seu melhor amigo Ã¢â‚¬â€ tem muito carinho esperando por vocÃƒÂªs! Um beijo nas patinhas! Ã°Å¸Â¥Â³",
    cupom:
      "Ã°Å¸Å½Ë† O {nome_pet} tÃƒÂ¡ de parabÃƒÂ©ns hoje, {nome}! Para comemorar esse dia tÃƒÂ£o especial, preparamos um cupom de {desconto} de desconto pra mimar o(a) aniversariante! Use o cÃƒÂ³digo {code} e vai fundo nos mimos! Ã°Å¸Ââ€¢Ã°Å¸Å½Â",
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
    assunto: "Sentimos sua falta! Ã°Å¸ÂÂ¾",
    mensagem: "",
  });
  const [enviandoInativos, setEnviandoInativos] = useState(false);
  const [resultadoEnvioInativos, setResultadoEnvioInativos] = useState(null);

  // RetenÃƒÂ§ÃƒÂ£o DinÃƒÂ¢mica
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
    mensagem: "ParabÃƒÂ©ns! VocÃƒÂª foi um dos nossos melhores clientes do mÃƒÂªs! Ã°Å¸Ââ€ ",
    mensagem_brinde:
      "ParabÃƒÂ©ns! VocÃƒÂª foi um dos nossos melhores clientes do mÃƒÂªs. Passe em nossa loja e retire seu brinde especial Ã¢â‚¬â€ serÃƒÂ¡ um prazer recebÃƒÂª-lo! Ã°Å¸Å½Â",
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

  // UnificaÃƒÂ§ÃƒÂ£o cross-canal
  const [confirmandoMerge, setConfirmandoMerge] = useState(null);
  const [resultadoMerge, setResultadoMerge] = useState(null);

  // RelatÃƒÂ³rios

  // Fidelidade Ã¢â‚¬â€ carimbos por cliente (legado Ã¢â‚¬â€ mantido para modal existente)
  const [fidClienteId, setFidClienteId] = useState("");
  const [fidCarimbos, setFidCarimbos] = useState(null);
  const [fidLoadingCarimbos, setFidLoadingCarimbos] = useState(false);
  const [fidRemovendo, setFidRemovendo] = useState(null);
  const [fidIncluirEstornados, setFidIncluirEstornados] = useState(false);
  const [fidModalManual, setFidModalManual] = useState(false);
  const [fidLancandoManual, setFidLancandoManual] = useState(false);
  const [fidManualNota, setFidManualNota] = useState("");

  // Gestor de BenefÃƒÂ­cios
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
  // Gestor Ã¢â‚¬â€ modo Por Campanha
  const [gestorModo, setGestorModo] = useState("cliente"); // 'cliente' | 'campanha'
  const [gestorCampanhaTipo, setGestorCampanhaTipo] = useState("carimbos");
  const [gestorCampanhaLista, setGestorCampanhaLista] = useState(null);
  const [gestorCampanhaCarregando, setGestorCampanhaCarregando] =
    useState(false);

  // Config de ranking
  const [rankingConfigSalvando, setRankingConfigSalvando] = useState(false);

  // Config de horÃƒÂ¡rios do scheduler
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
        `Anular o cupÃƒÂ£o ${code}? Esta aÃƒÂ§ÃƒÂ£o nÃƒÂ£o pode ser desfeita.`,
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
      alert(e?.response?.data?.detail || "Erro ao anular cupÃƒÂ£o.");
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
      // Monta vencedores com config individual de prÃƒÂªmio (sÃƒÂ³ os selecionados)
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
        "Erro ao enviar prÃƒÂªmios: " + (e?.response?.data?.detail || e.message),
      );
    } finally {
      setEnviandoDestaque(false);
    }
  };

  const criarCampanha = async () => {
    setErroCriarCampanha("");
    if (!novaCampanha.name.trim()) {
      setErroCriarCampanha("Nome obrigatÃƒÂ³rio.");
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
        `Arquivar a campanha "${c.name}"? Ela ficarÃƒÂ¡ inativa e nÃƒÂ£o poderÃƒÂ¡ ser reativada pela interface.`,
      )
    )
      return;
    setArquivando(c.id);
    try {
      await api.delete(`/campanhas/${c.id}`);
      setCampanhas((prev) => prev.filter((x) => x.id !== c.id));
    } catch (e) {
      if (e?.response?.status === 404) {
        // Campanha jÃƒÂ¡ nÃƒÂ£o existe no servidor Ã¢â‚¬â€ remove da lista localmente
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
        `Unificar clientes? O cliente #${removeId} serÃƒÂ¡ mesclado no #${keepId}. Os dados de campanhas serÃƒÂ£o transferidos.`,
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
        "Desfazer esta unificaÃƒÂ§ÃƒÂ£o? Os dados de campanhas serÃƒÂ£o restaurados.",
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
      setErroCriarSorteio("Nome obrigatÃƒÂ³rio.");
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
    if (!window.confirm("Executar o sorteio agora? Esta aÃƒÂ§ÃƒÂ£o ÃƒÂ© irreversÃƒÂ­vel."))
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
        "Erro ao carregar cÃƒÂ³digos: " + (e?.response?.data?.detail || e.message),
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
        nota: fidManualNota || "Carimbo lanÃƒÂ§ado manualmente pelo operador",
      });
      setFidModalManual(false);
      setFidManualNota("");
      await carregarCarimbosCliente();
      alert("Ã¢Å“â€¦ Carimbo lanÃƒÂ§ado com sucesso!");
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

  // Ã¢â€â‚¬Ã¢â€â‚¬ Gestor de BenefÃƒÂ­cios Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
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
        nota: gestorCarimboNota || "Carimbo lanÃƒÂ§ado manualmente pelo operador",
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
            ? "DÃƒÂ©bito manual de cashback"
            : "CrÃƒÂ©dito manual de cashback"),
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
      alert("CritÃƒÂ©rios de ranking salvos!");
    } catch (e) {
      alert("Erro ao salvar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setRankingConfigSalvando(false);
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
    if (!window.confirm("Remover esta regra de retenÃƒÂ§ÃƒÂ£o?")) return;
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
    // Para campanhas de aniversÃƒÂ¡rio, prÃƒÂ©-preenche a mensagem sugerida se ainda nÃƒÂ£o foi configurada
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
      console.error("Erro ao salvar parÃƒÂ¢metros:", e);
      alert("Erro ao salvar os parÃƒÂ¢metros.");
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
    if (!params) return "Ã¢â‚¬â€";
    if (tipo === "loyalty_stamp")
      return `${params.stamps_to_complete || "?"} carimbos Ã¢â€ â€™ R$ ${formatBRL(params.reward_value || 0)} de recompensa`;
    if (tipo === "cashback")
      return `Bronze ${params.bronze_percent || 0}% / Prata ${params.silver_percent || 0}% / Ouro ${params.gold_percent || 0}%`;
    if (["birthday", "birthday_customer", "birthday_pet"].includes(tipo)) {
      const tipoPresente = params.tipo_presente || "cupom";
      if (tipoPresente === "brinde") return "Ã°Å¸Å½Â Brinde na loja";
      return params.coupon_type === "percent"
        ? `Ã°Å¸Å½Â« Cupom ${params.coupon_value || "?"}% de desconto Ã‚Â· ${params.coupon_valid_days || "?"} dias`
        : `Ã°Å¸Å½Â« Cupom R$ ${formatBRL(params.coupon_value || 0)} de desconto Ã‚Â· ${params.coupon_valid_days || "?"} dias`;
    }
    if (tipo === "inactivity") {
      const valInact =
        params.coupon_type === "fixed"
          ? `R$ ${formatBRL(params.coupon_value || 0)}`
          : `${params.coupon_value || "?"}%`;
      return `Inativo ${params.inactivity_days || "?"} dias Ã¢â€ â€™ ${valInact} desconto`;
    }
    if (tipo === "welcome" || tipo === "welcome_app")
      return `Boas-vindas: R$ ${formatBRL(params.coupon_value || 0)} de bÃƒÂ´nus`;
    if (tipo === "ranking_monthly")
      return `${Object.keys(params).length} nÃƒÂ­veis configurados`;
    if (tipo === "quick_repurchase") {
      const val =
        params.coupon_type === "fixed"
          ? `R$ ${formatBRL(params.coupon_value || 0)}`
          : `${params.coupon_value || "?"}%`;
      return `PÃƒÂ³s-compra: ${val} desconto Ã¢â‚¬Â¢ ${params.coupon_valid_days || "?"} dias`;
    }
    return JSON.stringify(params).slice(0, 60) + "...";
  };

  const formatarValorCupom = (cupom) => {
    if (cupom.coupon_type === "percent" && cupom.discount_percent)
      return `${cupom.discount_percent}% off`;
    if (cupom.coupon_type === "fixed" && cupom.discount_value)
      return `R$ ${formatBRL(cupom.discount_value)} off`;
    return "Ã¢â‚¬â€";
  };

  const formatarData = (iso) => {
    if (!iso) return "Ã¢â‚¬â€";
    const d = iso.split("T")[0].split("-");
    return `${d[2]}/${d[1]}/${d[0]}`;
  };

  // Ã¢â€â‚¬Ã¢â€â‚¬ FormulÃƒÂ¡rios de parÃƒÂ¢metros por tipo de campanha Ã¢â€â‚¬Ã¢â€â‚¬
  const renderFormCampaign = (c) => {
    const tipo = c.campaign_type;
    const set = (key, val) => setParamsEditando((p) => ({ ...p, [key]: val }));
    const num = (key) => paramsEditando[key] ?? "";
    const str = (key) => paramsEditando[key] ?? "";

    if (tipo === "loyalty_stamp")
      return (
        <div className="grid grid-cols-2 gap-3">
          <CampanhaField
            label="Compra mÃƒÂ­nima (R$)"
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
            <option value="credit">CrÃƒÂ©dito cashback</option>
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
            label="Carimbo intermediÃƒÂ¡rio (0 = sem)"
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
            label="Recompensa intermediÃƒÂ¡ria (R$)"
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
              <option value="sem_rank">Sem classificaÃƒÂ§ÃƒÂ£o</option>
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
        { key: "bronze_percent", label: "Ã°Å¸Â¥â€° Bronze" },
        { key: "silver_percent", label: "Ã°Å¸Â¥Ë† Prata" },
        { key: "gold_percent", label: "Ã°Å¸Â¥â€¡ Ouro" },
        { key: "diamond_percent", label: "Ã°Å¸â€˜â€˜ Platina" },
        { key: "platinum_percent", label: "Ã°Å¸â€™Å½ Diamante" },
      ];
      const canais = [
        { key: "pdv_bonus_percent", label: "Ã°Å¸â€“Â¥Ã¯Â¸Â PDV (bÃƒÂ´nus %)" },
        { key: "app_bonus_percent", label: "Ã°Å¸â€œÂ± App (bÃƒÂ´nus %)" },
        { key: "ecommerce_bonus_percent", label: "Ã°Å¸â€ºâ€™ Ecommerce (bÃƒÂ´nus %)" },
      ];
      return (
        <div className="space-y-4">
          <div>
            <p className="text-xs text-gray-500 mb-2">
              % base por nÃƒÂ­vel de ranking (crÃƒÂ©dito automÃƒÂ¡tico em toda compra).
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
              BÃƒÂ´nus adicional por canal (somado ao % do nÃƒÂ­vel). Ex: App +1%
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
              Ã¢ÂÂ° Validade e Alertas
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
              Ã°Å¸Å½Â O que o cliente recebe no aniversÃƒÂ¡rio?
            </p>
            <div className="flex gap-4">
              {[
                { value: "cupom", label: "Ã°Å¸Å½Â« Cupom de desconto" },
                { value: "brinde", label: "Ã°Å¸Å½Â Brinde na loja" },
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

          {/* Campos do cupom (visÃƒÂ­vel apenas se tipo_presente = cupom) */}
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
                Ã¢Å“â€°Ã¯Â¸Â Mensagem enviada ao cliente
              </label>
              <button
                type="button"
                onClick={() => set("notification_message", fraseSugerida)}
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                Ã°Å¸â€â€ž Usar frase sugerida
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
              VariÃƒÂ¡veis disponÃƒÂ­veis:{" "}
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
            label="Compra mÃƒÂ­nima (R$)"
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
              placeholder="Ex: Obrigado pela compra! Use o cupom {code} na prÃƒÂ³xima visita."
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
        bronze: "Ã°Å¸Â¥â€° Bronze",
        silver: "Ã°Å¸Â¥Ë† Prata",
        gold: "Ã°Å¸Â¥â€¡ Ouro",
        diamond: "Ã¯Â¿Â½ Platina",
        platinum: "Ã°Å¸â€™Å½ Diamante",
      };
      const getLv = (lv) => paramsEditando[lv] || {};
      const setLv = (lv, key, val) =>
        setParamsEditando((p) => ({ ...p, [lv]: { ...p[lv], [key]: val } }));
      return (
        <div>
          <p className="text-xs text-gray-500 mb-2">
            CritÃƒÂ©rios mÃƒÂ­nimos para cada nÃƒÂ­vel. Recalculado mensalmente.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    NÃƒÂ­vel
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Gasto mÃƒÂ­n. (R$)
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Compras mÃƒÂ­n.
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Meses ativos mÃƒÂ­n.
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

    // fallback: editor genÃƒÂ©rico
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
            Ã°Å¸Å½Â¯ Campanhas de Fidelidade
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Gerencie campanhas automÃƒÂ¡ticas, ranking de clientes e cupons.
          </p>
        </div>

      </div>

      <CampanhasTabsBar aba={aba} onChange={setAba} />

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: DASHBOARD Ã¢â€â‚¬Ã¢â€â‚¬ */}
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

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ Modal: Envio para Inativos Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {modalEnvioInativos && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900">
                  Ã¢Å“â€°Ã¯Â¸Â Enviar e-mail de reativaÃƒÂ§ÃƒÂ£o
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Clientes sem compra hÃƒÂ¡ mais de {modalEnvioInativos} dias Ã‚Â· Os
                  e-mails sÃƒÂ£o enfileirados e enviados em lotes
                </p>
              </div>
              <button
                onClick={() => {
                  setModalEnvioInativos(null);
                  setResultadoEnvioInativos(null);
                }}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold"
              >
                Ãƒâ€”
              </button>
            </div>
            <div className="p-6 space-y-4">
              {resultadoEnvioInativos ? (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-1">
                  <p className="font-semibold text-green-800">
                    Ã¢Å“â€¦ E-mails enfileirados com sucesso!
                  </p>
                  <p className="text-sm text-green-700">
                    {resultadoEnvioInativos.enfileirados} e-mail(s)
                    adicionado(s) ÃƒÂ  fila.
                  </p>
                  {resultadoEnvioInativos.sem_email > 0 && (
                    <p className="text-xs text-gray-500">
                      {resultadoEnvioInativos.sem_email} cliente(s) nÃƒÂ£o tÃƒÂªm
                      e-mail cadastrado e foram ignorados.
                    </p>
                  )}
                  <button
                    onClick={() => {
                      setModalEnvioInativos(null);
                      setResultadoEnvioInativos(null);
                    }}
                    className="mt-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
                  >
                    Fechar
                  </button>
                </div>
              ) : (
                <>
                  <div>
                    <label className="text-xs font-semibold text-gray-500 uppercase block mb-1">
                      Assunto do e-mail
                    </label>
                    <input
                      type="text"
                      value={envioInativosForm.assunto}
                      onChange={(e) =>
                        setEnvioInativosForm((f) => ({
                          ...f,
                          assunto: e.target.value,
                        }))
                      }
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
                      placeholder="Ex: Sentimos sua falta! Ã°Å¸ÂÂ¾"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-gray-500 uppercase block mb-1">
                      Mensagem
                    </label>
                    <textarea
                      rows={5}
                      value={envioInativosForm.mensagem}
                      onChange={(e) =>
                        setEnvioInativosForm((f) => ({
                          ...f,
                          mensagem: e.target.value,
                        }))
                      }
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300 resize-none"
                      placeholder="Escreva a mensagem para os clientes inativos..."
                    />
                  </div>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => setModalEnvioInativos(null)}
                      className="flex-1 py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={enviarParaInativos}
                      disabled={
                        enviandoInativos ||
                        !envioInativosForm.assunto.trim() ||
                        !envioInativosForm.mensagem.trim()
                      }
                      className="flex-1 py-2.5 bg-orange-500 text-white rounded-lg text-sm font-semibold hover:bg-orange-600 disabled:opacity-50 transition-colors"
                    >
                      {enviandoInativos
                        ? "Enfileirando..."
                        : "Ã¢Å“â€°Ã¯Â¸Â Enfileirar e-mails"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: CAMPANHAS Ã¢â€â‚¬Ã¢â€â‚¬ */}
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


      {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: RETENÃƒâ€¡ÃƒÆ’O DINÃƒâ€šMICA Ã¢â€â‚¬Ã¢â€â‚¬ */}
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
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Ã°Å¸Å½Â² Sorteios
              </h2>
              <p className="text-sm text-gray-500">
                Crie sorteios exclusivos por nÃƒÂ­vel de ranking. O resultado ÃƒÂ©
                auditÃƒÂ¡vel via seed UUID.
              </p>
            </div>
            <button
              onClick={() => {
                setErroCriarSorteio("");
                setModalSorteio(true);
              }}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
            >
              + Novo Sorteio
            </button>
          </div>

          {sorteioResultado && (
            <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
              <p className="font-semibold text-purple-800 text-lg mb-1">
                Ã°Å¸Å½â€° Sorteio executado!
              </p>
              <p className="text-purple-700">
                Ganhador: <strong>{sorteioResultado.winner_name}</strong>
              </p>
              <p className="text-sm text-purple-600 mt-1">
                {sorteioResultado.total_participantes} participante(s) Ã‚Â· Seed:{" "}
                <span className="font-mono text-xs">
                  {sorteioResultado.seed_uuid?.slice(0, 16)}Ã¢â‚¬Â¦
                </span>
              </p>
              <button
                onClick={() => setSorteioResultado(null)}
                className="mt-2 text-xs text-purple-500 hover:underline"
              >
                Fechar
              </button>
            </div>
          )}

          {loadingSorteios ? (
            <div className="p-8 text-center text-gray-400">
              Carregando sorteios...
            </div>
          ) : sorteios.length === 0 ? (
            <div className="bg-white rounded-xl border shadow-sm p-8 text-center text-gray-400">
              <p className="text-3xl mb-2">Ã°Å¸Å½Â²</p>
              <p>Nenhum sorteio criado ainda.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sorteios.map((s) => {
                const statusColors = {
                  draft: "bg-gray-100 text-gray-600",
                  open: "bg-blue-100 text-blue-700",
                  drawn: "bg-green-100 text-green-700",
                  cancelled: "bg-red-100 text-red-600",
                };
                const statusLabels = {
                  draft: "Ã°Å¸â€œÂ Rascunho",
                  open: "Ã¢Å“â€¦ Inscrito",
                  drawn: "Ã°Å¸Ââ€  Realizado",
                  cancelled: "Ã¢ÂÅ’ Cancelado",
                };
                return (
                  <div
                    key={s.id}
                    className="bg-white rounded-xl border shadow-sm p-5"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className="font-semibold text-gray-900">
                            {s.name}
                          </span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[s.status] || "bg-gray-100 text-gray-600"}`}
                          >
                            {statusLabels[s.status] || s.status}
                          </span>
                          {s.rank_filter && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                              {RANK_LABELS[s.rank_filter]?.emoji}{" "}
                              {RANK_LABELS[s.rank_filter]?.label ||
                                s.rank_filter}
                              +
                            </span>
                          )}
                        </div>
                        {s.prize_description && (
                          <p className="text-sm text-gray-600">
                            Ã°Å¸Å½Â {s.prize_description}
                          </p>
                        )}
                        {s.description && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            {s.description}
                          </p>
                        )}
                        <p className="text-xs text-gray-400 mt-1">
                          {s.total_participantes || 0} participante(s)
                          {s.draw_date &&
                            ` Ã‚Â· Sorteio: ${new Date(s.draw_date).toLocaleDateString("pt-BR")}`}
                        </p>
                      </div>
                      <div className="flex flex-col gap-2 items-end shrink-0">
                        {s.status === "draft" && (
                          <button
                            onClick={() => inscreverSorteio(s.id)}
                            disabled={inscrevendo === s.id}
                            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                          >
                            {inscrevendo === s.id
                              ? "..."
                              : "Ã°Å¸â€œâ€¹ Inscrever ElegÃƒÂ­veis"}
                          </button>
                        )}
                        {s.status === "open" && (
                          <button
                            onClick={() => executarSorteio(s.id)}
                            disabled={executandoSorteio === s.id}
                            className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs font-medium hover:bg-purple-700 disabled:opacity-50"
                          >
                            {executandoSorteio === s.id
                              ? "..."
                              : "Ã°Å¸Å½Â² Executar Sorteio"}
                          </button>
                        )}
                        {(s.status === "draft" || s.status === "open") && (
                          <button
                            onClick={() => cancelarSorteio(s.id, s.name)}
                            className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-xs font-medium hover:bg-red-100"
                          >
                            Cancelar
                          </button>
                        )}
                        {(s.status === "open" || s.status === "drawn") && (
                          <button
                            onClick={() => abrirCodigosOffline(s)}
                            className="px-3 py-1.5 bg-gray-50 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-100 border"
                          >
                            Ã°Å¸â€œâ€¹ CÃƒÂ³digos Offline
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: RANKING Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {aba === "ranking" && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap items-center">
            {["todos", "bronze", "silver", "gold", "diamond", "platinum"].map(
              (n) => {
                const rl = n === "todos" ? null : RANK_LABELS[n];
                return (
                  <button
                    key={n}
                    onClick={() => setFiltroNivel(n)}
                    className={`px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
                      filtroNivel === n
                        ? rl
                          ? `${rl.color} ${rl.border} border-2`
                          : "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    {rl ? `${rl.emoji} ${rl.label}` : "Todos"}
                  </button>
                );
              },
            )}
            <button
              onClick={async () => {
                try {
                  await api.post("/campanhas/ranking/recalcular");
                  alert(
                    "Ã¢Å“â€¦ RecÃƒÂ¡lculo de ranking enfileirado! O worker processarÃƒÂ¡ em atÃƒÂ© 10 segundos.",
                  );
                  setTimeout(() => carregarRanking(), 3000);
                } catch (e) {
                  alert("Erro: " + (e?.response?.data?.detail || e.message));
                }
              }}
              className="ml-auto px-4 py-2 bg-gray-700 text-white rounded-full text-sm font-medium hover:bg-gray-800 transition-colors"
            >
              Ã°Å¸â€â€ž Recalcular Agora
            </button>
          </div>

          {loadingRanking ? (
            <div className="p-8 text-center text-gray-400">
              Carregando ranking...
            </div>
          ) : !ranking ? (
            <div className="p-8 text-center text-gray-400">Carregando...</div>
          ) : (
            <>
              {ranking.distribuicao && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {["bronze", "silver", "gold", "diamond", "platinum"].map(
                    (n) => {
                      const rl = RANK_LABELS[n];
                      const count = ranking.distribuicao[n] || 0;
                      return (
                        <div
                          key={n}
                          className={`rounded-xl border p-3 text-center ${rl.color} ${rl.border}`}
                        >
                          <p className="text-2xl">{rl.emoji}</p>
                          <p className="font-bold text-lg">{count}</p>
                          <p className="text-xs font-medium">{rl.label}</p>
                        </div>
                      );
                    },
                  )}
                </div>
              )}

              <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b bg-gray-50">
                  <h2 className="font-semibold text-gray-800">
                    Clientes no Ranking
                  </h2>
                  <p className="text-xs text-gray-500">
                    PerÃƒÂ­odo: {ranking.periodo}
                  </p>
                </div>
                {ranking.clientes.length === 0 ? (
                  <div className="p-8 text-center text-gray-400">
                    Nenhum cliente neste nÃƒÂ­vel.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">
                            #
                          </th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">
                            Cliente
                          </th>
                          <th className="px-4 py-3 text-left font-medium text-gray-600">
                            NÃƒÂ­vel
                          </th>
                          <th className="px-4 py-3 text-right font-medium text-gray-600">
                            Gasto Total
                          </th>
                          <th className="px-4 py-3 text-center font-medium text-gray-600">
                            Compras
                          </th>
                          <th className="px-4 py-3 text-center font-medium text-gray-600">
                            Meses ativos
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {ranking.clientes.map((cl, i) => {
                          const rl =
                            RANK_LABELS[cl.rank_level] || RANK_LABELS.bronze;
                          return (
                            <tr
                              key={cl.customer_id}
                              className="hover:bg-gray-50"
                            >
                              <td className="px-4 py-3 text-gray-400 font-medium">
                                {i + 1}
                              </td>
                              <td className="px-4 py-3">
                                <p className="font-medium text-gray-900">
                                  {cl.nome || `Cliente #${cl.customer_id}`}
                                </p>
                                {cl.telefone && (
                                  <p className="text-xs text-gray-400">
                                    {cl.telefone}
                                  </p>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                <span
                                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${rl.color} ${rl.border}`}
                                >
                                  {rl.emoji} {rl.label}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-right font-semibold text-gray-900">
                                R$ {formatBRL(cl.total_spent)}
                              </td>
                              <td className="px-4 py-3 text-center text-gray-600">
                                {cl.total_purchases}
                              </td>
                              <td className="px-4 py-3 text-center text-gray-500">
                                {cl.active_months}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}

          {/* BotÃƒÂ£o Envio em Lote */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-blue-800">Ã°Å¸â€œÂ§ Envio em Lote</p>
              <p className="text-sm text-blue-600">
                Envie um e-mail personalizado para todos os clientes de um
                nÃƒÂ­vel.
              </p>
            </div>
            <button
              onClick={() => {
                setResultadoLote(null);
                setModalLote(true);
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Enviar para NÃƒÂ­vel
            </button>
          </div>

          {/* Config de critÃƒÂ©rios de ranking */}
          <div className="bg-white rounded-xl border shadow-sm">
            <button
              className="w-full px-6 py-4 flex items-center justify-between text-left"
              onClick={() =>
                setRankingConfig((prev) =>
                  prev
                    ? prev._aberto
                      ? { ...prev, _aberto: false }
                      : { ...prev, _aberto: true }
                    : prev,
                )
              }
            >
              <span className="font-semibold text-gray-800">
                Ã¢Å¡â„¢Ã¯Â¸Â Configurar CritÃƒÂ©rios de Ranking
              </span>
              <span className="text-gray-400 text-sm">
                {rankingConfig?._aberto ? "Ã¢â€“Â² Fechar" : "Ã¢â€“Â¼ Expandir"}
              </span>
            </button>
            {rankingConfig?._aberto && (
              <div className="px-6 pb-6 space-y-4">
                {rankingConfigLoading ? (
                  <div className="text-center text-gray-400 py-4">
                    Carregando...
                  </div>
                ) : !rankingConfig ? (
                  <div className="text-center text-gray-400 py-4">
                    NÃƒÂ£o foi possÃƒÂ­vel carregar.
                  </div>
                ) : (
                  <>
                    <p className="text-xs text-gray-500">
                      O cliente precisa atingir <strong>todos</strong> os
                      critÃƒÂ©rios de um nÃƒÂ­vel para alcanÃƒÂ§ÃƒÂ¡-lo (gasto, compras e
                      meses ativos nos ÃƒÂºltimos 12 meses). Quem nÃƒÂ£o atingir o
                      mÃƒÂ­nimo de Prata fica como Bronze.
                    </p>
                    {[
                      { key: "silver", label: "Ã°Å¸Â¥Ë† Prata" },
                      { key: "gold", label: "Ã°Å¸Â¥â€¡ Ouro" },
                      { key: "diamond", label: "Ã°Å¸â€˜â€˜ Platina" },
                      { key: "platinum", label: "Ã°Å¸â€™Â¸ Diamante" },
                    ].map(({ key, label }) => (
                      <div
                        key={key}
                        className="border rounded-xl p-4 space-y-2"
                      >
                        <p className="font-medium text-gray-700">{label}</p>
                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">
                              Gasto mÃƒÂ­nimo (R$)
                            </label>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              value={rankingConfig[`${key}_min_spent`] ?? ""}
                              onChange={(e) =>
                                setRankingConfig((p) => ({
                                  ...p,
                                  [`${key}_min_spent`]:
                                    parseFloat(e.target.value) || 0,
                                }))
                              }
                              className="w-full border rounded-lg px-3 py-1.5 text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">
                              Compras mÃƒÂ­nimas
                            </label>
                            <input
                              type="number"
                              min="1"
                              step="1"
                              value={
                                rankingConfig[`${key}_min_purchases`] ?? ""
                              }
                              onChange={(e) =>
                                setRankingConfig((p) => ({
                                  ...p,
                                  [`${key}_min_purchases`]:
                                    parseInt(e.target.value, 10) || 0,
                                }))
                              }
                              className="w-full border rounded-lg px-3 py-1.5 text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">
                              Meses ativos mÃƒÂ­nimos
                            </label>
                            <input
                              type="number"
                              min="1"
                              step="1"
                              value={rankingConfig[`${key}_min_months`] ?? ""}
                              onChange={(e) =>
                                setRankingConfig((p) => ({
                                  ...p,
                                  [`${key}_min_months`]:
                                    parseInt(e.target.value, 10) || 0,
                                }))
                              }
                              className="w-full border rounded-lg px-3 py-1.5 text-sm"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                    <div className="flex justify-end">
                      <button
                        onClick={salvarRankingConfig}
                        disabled={rankingConfigSalvando}
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                      >
                        {rankingConfigSalvando
                          ? "Salvando..."
                          : "Salvar CritÃƒÂ©rios"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* BenefÃƒÂ­cios por NÃƒÂ­vel */}
          <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
            <button
              className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
              onClick={() =>
                setRankingConfig((prev) => ({
                  ...prev,
                  _beneficios_aberto: !prev?._beneficios_aberto,
                }))
              }
            >
              <span className="font-semibold text-gray-800">
                Ã°Å¸â€œÅ  BenefÃƒÂ­cios por NÃƒÂ­vel
              </span>
              <span className="text-gray-400 text-sm">
                {rankingConfig?._beneficios_aberto ? "Ã¢â€“Â² Fechar" : "Ã¢â€“Â¼ Expandir"}
              </span>
            </button>
            {rankingConfig?._beneficios_aberto && (
              <div className="px-6 pb-6 space-y-4">
                <p className="text-xs text-gray-500">
                  VisÃƒÂ£o geral dos critÃƒÂ©rios de cada nÃƒÂ­vel. Para configurar
                  benefÃƒÂ­cios especÃƒÂ­ficos (cashback %, carimbos, sorteios
                  exclusivos), acesse a campanha correspondente.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="bg-gray-50 text-gray-600 text-xs uppercase">
                        <th className="text-left p-3 border-b">NÃƒÂ­vel</th>
                        <th className="text-center p-3 border-b">
                          Gasto mÃƒÂ­n. (R$)
                        </th>
                        <th className="text-center p-3 border-b">
                          Compras mÃƒÂ­n.
                        </th>
                        <th className="text-center p-3 border-b">
                          Meses ativos mÃƒÂ­n.
                        </th>
                        <th className="text-center p-3 border-b">
                          Cashback
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { key: "bronze", label: "Ã°Å¸Â¥â€° Bronze", base: true },
                        { key: "silver", label: "Ã°Å¸Â¥Ë† Prata" },
                        { key: "gold", label: "Ã°Å¸Â¥â€¡ Ouro" },
                        { key: "diamond", label: "Ã°Å¸â€˜â€˜ Platina" },
                        { key: "platinum", label: "Ã°Å¸â€™Â¸ Diamante" },
                      ].map(({ key, label, base }) => (
                        <tr
                          key={key}
                          className="border-b last:border-0 hover:bg-gray-50"
                        >
                          <td className="p-3 font-medium text-gray-700">
                            {label}
                          </td>
                          <td className="p-3 text-center text-gray-600">
                            {base
                              ? "Ã¢â‚¬â€"
                              : rankingConfig
                                ? `R$ ${formatBRL(rankingConfig[`${key}_min_spent`] ?? 0)}`
                                : "Ã¢â‚¬Â¦"}
                          </td>
                          <td className="p-3 text-center text-gray-600">
                            {base
                              ? "Ã¢â‚¬â€"
                              : (rankingConfig?.[`${key}_min_purchases`] ??
                                "Ã¢â‚¬Â¦")}
                          </td>
                          <td className="p-3 text-center text-gray-600">
                            {base
                              ? "Ã¢â‚¬â€"
                              : (rankingConfig?.[`${key}_min_months`] ?? "Ã¢â‚¬Â¦")}
                          </td>
                          <td className="p-3 text-center text-gray-600">
                            {(() => {
                              const cashPct = campanhas.find(c => c.campaign_type === 'cashback')?.params?.[`${key}_percent`];
                              return cashPct != null ? `${cashPct}%` : 'Ã¢â‚¬â€';
                            })()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="bg-blue-50 rounded-lg p-4 text-xs text-blue-700 space-y-1.5">
                  <p className="font-semibold">
                    Ã¢â€žÂ¹Ã¯Â¸Â Como configurar os benefÃƒÂ­cios por nÃƒÂ­vel:
                  </p>
                  <p>
                    Ã¢â‚¬Â¢ <strong>Cashback % por nÃƒÂ­vel:</strong> acesse a campanha
                    de Cashback e configure os campos Bronze / Prata / Ouro /
                    Platina / Diamante.
                  </p>
                  <p>
                    Ã¢â‚¬Â¢ <strong>Carimbos exclusivos:</strong> crie uma campanha de
                    Carimbo com o campo "NÃƒÂ­vel mÃƒÂ­nimo" definido para restringir
                    a um grupo.
                  </p>
                  <p>
                    Ã¢â‚¬Â¢ <strong>Sorteios exclusivos:</strong> na aba Sorteios,
                    defina o campo "RestriÃƒÂ§ÃƒÂ£o de nÃƒÂ­vel" ao criar o sorteio.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      {aba === "cupons" && (
        <div className="space-y-4">
          {/* Barra de filtros */}
          <div className="bg-white rounded-xl border shadow-sm p-4 flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Busca (cÃƒÂ³digo ou cliente)
              </label>
              <input
                type="text"
                value={filtroCupomBusca}
                onChange={(e) => setFiltroCupomBusca(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && carregarCupons()}
                placeholder="Ex: ANIV ou JoÃƒÂ£o Silva"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Criado a partir de
              </label>
              <input
                type="date"
                value={filtroCupomDataInicio}
                onChange={(e) => setFiltroCupomDataInicio(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Criado atÃƒÂ©
              </label>
              <input
                type="date"
                value={filtroCupomDataFim}
                onChange={(e) => setFiltroCupomDataFim(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Campanha
              </label>
              <select
                value={filtroCupomCampanha}
                onChange={(e) => setFiltroCupomCampanha(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                <option value="">Todas as campanhas</option>
                {campanhas.map((cp) => (
                  <option key={cp.id} value={cp.id}>
                    {cp.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={carregarCupons}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Ã°Å¸â€Â Filtrar
            </button>
            {(filtroCupomBusca ||
              filtroCupomDataInicio ||
              filtroCupomDataFim ||
              filtroCupomCampanha) && (
              <button
                onClick={() => {
                  setFiltroCupomBusca("");
                  setFiltroCupomDataInicio("");
                  setFiltroCupomDataFim("");
                  setFiltroCupomCampanha("");
                }}
                className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Limpar
              </button>
            )}
          </div>

          <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between flex-wrap gap-2">
              <h2 className="font-semibold text-gray-800">Cupons Gerados</h2>
              <div className="flex gap-2 flex-wrap">
                {["active", "used", "expired", "voided", "todos"].map((s) => (
                  <button
                    key={s}
                    onClick={() => setFiltroCupomStatus(s)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      filtroCupomStatus === s
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {
                      {
                        active: "Ativos",
                        used: "Usados",
                        expired: "Expirados",
                        voided: "Cancelados",
                        todos: "Todos",
                      }[s]
                    }
                  </button>
                ))}
              </div>
            </div>
            {loadingCupons ? (
              <div className="p-8 text-center text-gray-400">
                Carregando cupons...
              </div>
            ) : cupons.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <p className="text-2xl mb-2">Ã°Å¸Å½Å¸Ã¯Â¸Â</p>
                <p>Nenhum cupom encontrado.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        CÃƒÂ³digo
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Tipo
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Canal
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Desconto
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Cliente
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Criado em
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Validade
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Status
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        AÃƒÂ§ÃƒÂ£o
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {cupons.map((c) => {
                      const st = CUPOM_STATUS[c.status] || {
                        label: c.status,
                        color: "bg-gray-100 text-gray-600",
                      };
                      const isDetalhes = cupomDetalhes?.id === c.id;
                      return (
                        <Fragment key={c.id}>
                          <tr
                            className={`hover:bg-gray-50 cursor-pointer ${isDetalhes ? "bg-blue-50" : ""}`}
                            onClick={() =>
                              setCupomDetalhes(isDetalhes ? null : c)
                            }
                          >
                            <td className="px-4 py-3 font-mono font-semibold text-gray-800">
                              {c.code}
                            </td>
                            <td className="px-4 py-3 text-gray-600">
                              {c.coupon_type === "percent"
                                ? "Percentual"
                                : c.coupon_type === "fixed"
                                  ? "Valor fixo"
                                  : c.coupon_type === "gift"
                                    ? "Ã°Å¸Å½Â Brinde"
                                    : c.coupon_type}
                            </td>
                            <td className="px-4 py-3 text-gray-500">
                              {c.channel || "pdv"}
                            </td>
                            <td className="px-4 py-3 font-medium text-gray-900">
                              {formatarValorCupom(c)}
                            </td>
                            <td className="px-4 py-3 text-gray-600">
                              {c.nome_cliente ? (
                                <span title={`ID ${c.customer_id}`}>
                                  {c.nome_cliente}
                                </span>
                              ) : c.customer_id ? (
                                <span className="text-gray-400">
                                  #{c.customer_id}
                                </span>
                              ) : (
                                <span className="text-gray-300">Ã¢â‚¬â€</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-gray-500 text-xs">
                              {c.created_at
                                ? new Date(c.created_at).toLocaleDateString(
                                    "pt-BR",
                                  )
                                : "Ã¢â‚¬â€"}
                            </td>
                            <td className="px-4 py-3 text-gray-500">
                              {c.valid_until
                                ? new Date(c.valid_until).toLocaleDateString(
                                    "pt-BR",
                                  )
                                : "Ã¢â‚¬â€"}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`px-2 py-0.5 rounded-full text-xs font-medium ${st.color}`}
                              >
                                {st.label}
                              </span>
                            </td>
                            <td className="px-4 py-3 flex items-center gap-2">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setCupomDetalhes(isDetalhes ? null : c);
                                }}
                                className="text-xs text-blue-600 hover:underline"
                              >
                                {isDetalhes ? "Fechar" : "Detalhes"}
                              </button>
                              {c.status === "active" && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    anularCupom(c.code);
                                  }}
                                  disabled={anulando === c.code}
                                  className="text-xs text-red-600 hover:text-red-800 disabled:opacity-40 font-medium"
                                >
                                  {anulando === c.code
                                    ? "Anulando..."
                                    : "Ã°Å¸Å¡Â« Anular"}
                                </button>
                              )}
                            </td>
                          </tr>
                          {isDetalhes && (
                            <tr
                              key={`det-${c.id}`}
                              className="bg-blue-50 border-b"
                            >
                              <td colSpan={9} className="px-6 py-4">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                                  <div>
                                    <p className="text-xs text-gray-500 font-medium mb-0.5">
                                      CÃƒÂ³digo
                                    </p>
                                    <p className="font-mono font-bold text-gray-800">
                                      {c.code}
                                    </p>
                                  </div>
                                  {c.nome_campanha && (
                                    <div>
                                      <p className="text-xs text-gray-500 font-medium mb-0.5">
                                        Campanha
                                      </p>
                                      <p className="text-gray-700">
                                        {c.nome_campanha}
                                      </p>
                                    </div>
                                  )}
                                  <div>
                                    <p className="text-xs text-gray-500 font-medium mb-0.5">
                                      Criado em
                                    </p>
                                    <p className="text-gray-700">
                                      {c.created_at
                                        ? new Date(c.created_at).toLocaleString(
                                            "pt-BR",
                                          )
                                        : "Ã¢â‚¬â€"}
                                    </p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-gray-500 font-medium mb-0.5">
                                      VÃƒÂ¡lido atÃƒÂ©
                                    </p>
                                    <p className="text-gray-700">
                                      {c.valid_until
                                        ? new Date(
                                            c.valid_until,
                                          ).toLocaleDateString("pt-BR")
                                        : "Sem validade"}
                                    </p>
                                  </div>
                                  {c.used_at && (
                                    <div>
                                      <p className="text-xs text-gray-500 font-medium mb-0.5">
                                        Usado em
                                      </p>
                                      <p className="text-gray-700">
                                        {new Date(c.used_at).toLocaleString(
                                          "pt-BR",
                                        )}
                                      </p>
                                    </div>
                                  )}
                                  {c.coupon_type === "gift" &&
                                    c.meta?.mensagem && (
                                      <div className="col-span-2">
                                        <p className="text-xs text-gray-500 font-medium mb-0.5">
                                          Mensagem do brinde
                                        </p>
                                        <p className="text-gray-700">
                                          {c.meta.mensagem}
                                        </p>
                                      </div>
                                    )}
                                  {c.meta?.retirar_de && (
                                    <div>
                                      <p className="text-xs text-gray-500 font-medium mb-0.5">
                                        Retirada a partir de
                                      </p>
                                      <p className="text-gray-700">
                                        {new Date(
                                          c.meta.retirar_de,
                                        ).toLocaleDateString("pt-BR")}
                                      </p>
                                    </div>
                                  )}
                                  {c.meta?.retirar_ate && (
                                    <div>
                                      <p className="text-xs text-gray-500 font-medium mb-0.5">
                                        Retirada atÃƒÂ©
                                      </p>
                                      <p className="text-gray-700">
                                        {new Date(
                                          c.meta.retirar_ate,
                                        ).toLocaleDateString("pt-BR")}
                                      </p>
                                    </div>
                                  )}
                                  {c.meta?.categoria && (
                                    <div>
                                      <p className="text-xs text-gray-500 font-medium mb-0.5">
                                        Categoria destaque
                                      </p>
                                      <p className="text-gray-700">
                                        {c.meta.categoria === "maior_gasto"
                                          ? "Ã°Å¸â€™Â° Maior Gasto"
                                          : c.meta.categoria === "mais_compras"
                                            ? "Ã°Å¸â€ºâ€™ Mais Compras"
                                            : c.meta.categoria}
                                      </p>
                                    </div>
                                  )}
                                  {c.meta?.periodo && (
                                    <div>
                                      <p className="text-xs text-gray-500 font-medium mb-0.5">
                                        PerÃƒÂ­odo
                                      </p>
                                      <p className="text-gray-700">
                                        {c.meta.periodo}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: RELATÃƒâ€œRIOS Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {aba === "relatorios" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border shadow-sm p-4 flex flex-wrap gap-4 items-end">
            <div>
              <label
                htmlFor="rel-data-inicio"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Data inÃƒÂ­cio
              </label>
              <input
                id="rel-data-inicio"
                type="date"
                value={relDataInicio}
                onChange={(e) => setRelDataInicio(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label
                htmlFor="rel-data-fim"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Data fim
              </label>
              <input
                id="rel-data-fim"
                type="date"
                value={relDataFim}
                onChange={(e) => setRelDataFim(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label
                htmlFor="rel-tipo"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Tipo
              </label>
              <select
                id="rel-tipo"
                value={relTipo}
                onChange={(e) => setRelTipo(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                <option value="todos">Todos</option>
                <option value="credito">SÃƒÂ³ crÃƒÂ©ditos</option>
                <option value="resgate">SÃƒÂ³ resgates</option>
              </select>
            </div>
          </div>

          {relatorio && (
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
                <p className="text-xs text-green-600 font-medium mb-1">
                  Total Creditado
                </p>
                <p className="text-xl font-bold text-green-700">
                  R$ {formatBRL(relatorio.total_creditado)}
                </p>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
                <p className="text-xs text-red-600 font-medium mb-1">
                  Total Resgatado
                </p>
                <p className="text-xl font-bold text-red-700">
                  R$ {formatBRL(relatorio.total_resgatado)}
                </p>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
                <p className="text-xs text-blue-600 font-medium mb-1">
                  Saldo Atual (Passivo)
                </p>
                <p className="text-xl font-bold text-blue-700">
                  R$ {formatBRL(relatorio.saldo_total)}
                </p>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b bg-gray-50">
              <h2 className="font-semibold text-gray-800">
                HistÃƒÂ³rico de MovimentaÃƒÂ§ÃƒÂµes
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                CrÃƒÂ©ditos = cashback gerado ao cliente. Resgates = cashback usado
                como pagamento numa venda.
              </p>
            </div>
            {loadingRelatorio ? (
              <div className="p-8 text-center text-gray-400">
                Carregando relatÃƒÂ³rio...
              </div>
            ) : !relatorio || relatorio.transacoes.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <p className="text-2xl mb-2">Ã°Å¸â€œÂ­</p>
                <p>Nenhuma movimentaÃƒÂ§ÃƒÂ£o no perÃƒÂ­odo.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Data
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Cliente
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Tipo
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Venda
                      </th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">
                        Valor
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        DescriÃƒÂ§ÃƒÂ£o
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {relatorio.transacoes.map((t) => (
                      <tr key={t.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                          {formatarData(t.data)}
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-900">
                          {t.cliente_nome}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              t.tipo === "credito"
                                ? "bg-green-100 text-green-700"
                                : "bg-orange-100 text-orange-700"
                            }`}
                          >
                            {t.tipo === "credito" ? "Ã¢Â¬â€ Ã¯Â¸Â CrÃƒÂ©dito" : "Ã¢Â¬â€¡Ã¯Â¸Â Resgate"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-500">
                          {t.venda_id || "Ã¢â‚¬â€"}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold">
                          R$ {formatBRL(t.valor)}
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs max-w-[200px] truncate">
                          {t.descricao || "Ã¢â‚¬â€"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: UNIFICAÃƒâ€¡ÃƒÆ’O CROSS-CANAL Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {aba === "unificacao" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="font-semibold text-gray-800">
                  Ã°Å¸â€â€” UnificaÃƒÂ§ÃƒÂ£o Cross-Canal por CPF/Telefone
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Clientes que parecem ser a mesma pessoa (mesmo CPF ou mesmo
                  telefone) aparecem aqui para unificaÃƒÂ§ÃƒÂ£o manual.
                </p>
              </div>
              <button
                onClick={carregarSugestoes}
                disabled={loadingSugestoes}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {loadingSugestoes ? "Buscando..." : "Ã°Å¸â€Â Buscar Duplicatas"}
              </button>
            </div>

            {resultadoMerge && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 text-sm flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-green-800">
                    Ã¢Å“â€¦ Clientes unificados! (Merge #{resultadoMerge.merge_id})
                  </p>
                  <p className="text-green-600">
                    Transferidos: {resultadoMerge.transferencias?.cashback ?? 0}{" "}
                    cashbacks, {resultadoMerge.transferencias?.carimbos ?? 0}{" "}
                    carimbos, {resultadoMerge.transferencias?.cupons ?? 0}{" "}
                    cupons, {resultadoMerge.transferencias?.ranking ?? 0}{" "}
                    posiÃƒÂ§ÃƒÂµes de ranking,{" "}
                    {resultadoMerge.transferencias?.vendas ?? 0} vendas,{" "}
                    {resultadoMerge.transferencias?.execucoes_campanhas ?? 0}{" "}
                    execuÃƒÂ§ÃƒÂµes de campanha.
                  </p>
                </div>
                <button
                  onClick={() => desfazerMerge(resultadoMerge.merge_id)}
                  className="text-xs text-red-600 hover:underline whitespace-nowrap"
                >
                  Desfazer
                </button>
              </div>
            )}

            {loadingSugestoes && (
              <div className="p-8 text-center text-gray-400">
                Buscando duplicatas...
              </div>
            )}

            {!loadingSugestoes && sugestoes.length === 0 && (
              <div className="p-8 text-center text-gray-400">
                <p className="text-3xl mb-2">Ã¢Å“â€¦</p>
                <p>
                  Nenhuma duplicata encontrada. Clique em "Buscar Duplicatas"
                  para verificar.
                </p>
              </div>
            )}

            {sugestoes.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Motivo
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Cliente A
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Cliente B
                      </th>
                      <th className="px-4 py-3 text-center font-medium text-gray-600">
                        AÃƒÂ§ÃƒÂ£o
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {sugestoes.map((s, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              s.motivo === "mesmo_cpf"
                                ? "bg-purple-100 text-purple-700"
                                : "bg-blue-100 text-blue-700"
                            }`}
                          >
                            {s.motivo === "mesmo_cpf"
                              ? "Ã°Å¸ÂªÂª Mesmo CPF"
                              : "Ã°Å¸â€œÅ¾ Mesmo Telefone"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-900">
                            {s.cliente_a.nome}
                          </p>
                          {s.cliente_a.cpf && (
                            <p className="text-xs text-gray-400">
                              CPF: {s.cliente_a.cpf}
                            </p>
                          )}
                          {s.cliente_a.telefone && (
                            <p className="text-xs text-gray-400">
                              Tel: {s.cliente_a.telefone}
                            </p>
                          )}
                          <p className="text-xs text-gray-300">
                            ID #{s.cliente_a.id}
                          </p>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-900">
                            {s.cliente_b.nome}
                          </p>
                          {s.cliente_b.cpf && (
                            <p className="text-xs text-gray-400">
                              CPF: {s.cliente_b.cpf}
                            </p>
                          )}
                          {s.cliente_b.telefone && (
                            <p className="text-xs text-gray-400">
                              Tel: {s.cliente_b.telefone}
                            </p>
                          )}
                          <p className="text-xs text-gray-300">
                            ID #{s.cliente_b.id}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex flex-col gap-1 items-center">
                            <button
                              onClick={() =>
                                confirmarMerge(
                                  s.cliente_a.id,
                                  s.cliente_b.id,
                                  s.motivo,
                                )
                              }
                              disabled={
                                confirmandoMerge ===
                                `${s.cliente_a.id}-${s.cliente_b.id}`
                              }
                              className="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50 w-full"
                            >
                              Unir A Ã¢â€ Â B
                            </button>
                            <button
                              onClick={() =>
                                confirmarMerge(
                                  s.cliente_b.id,
                                  s.cliente_a.id,
                                  s.motivo,
                                )
                              }
                              disabled={
                                confirmandoMerge ===
                                `${s.cliente_b.id}-${s.cliente_a.id}`
                              }
                              className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300 disabled:opacity-50 w-full"
                            >
                              Unir B Ã¢â€ Â A
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: CRIAR SORTEIO Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {modalSorteio && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Ã°Å¸Å½Â² Novo Sorteio</h3>
              <button
                onClick={() => setModalSorteio(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ãƒâ€”
              </button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <div>
                <label
                  htmlFor="s-nome"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Nome do sorteio
                </label>
                <input
                  id="s-nome"
                  type="text"
                  placeholder="Ex: Sorteio de MarÃƒÂ§o"
                  value={novoSorteio.name}
                  onChange={(e) =>
                    setNovoSorteio((p) => ({ ...p, name: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="s-premio"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  PrÃƒÂªmio
                </label>
                <input
                  id="s-premio"
                  type="text"
                  placeholder="Ex: Kit banho + tosa grÃƒÂ¡tis"
                  value={novoSorteio.prize_description}
                  onChange={(e) =>
                    setNovoSorteio((p) => ({
                      ...p,
                      prize_description: e.target.value,
                    }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="s-nivel"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  NÃƒÂ­vel mÃƒÂ­nimo elegantÃƒÂ­vel (opcional)
                </label>
                <select
                  id="s-nivel"
                  value={novoSorteio.rank_filter}
                  onChange={(e) =>
                    setNovoSorteio((p) => ({
                      ...p,
                      rank_filter: e.target.value,
                    }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Todos os clientes</option>
                  <option value="bronze">Ã°Å¸Â¥â€° Bronze+</option>
                  <option value="silver">Ã°Å¸Â¥Ë† Prata+</option>
                  <option value="gold">Ã°Å¸Â¥â€¡ Ouro+</option>
                  <option value="platinum">Ã°Å¸â€™Å½ Diamante+</option>
                  <option value="diamond">Ã°Å¸â€˜â€˜ Platina</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="s-data"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Data do sorteio (opcional)
                </label>
                <input
                  id="s-data"
                  type="date"
                  value={novoSorteio.draw_date}
                  onChange={(e) =>
                    setNovoSorteio((p) => ({ ...p, draw_date: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="s-desc"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  DescriÃƒÂ§ÃƒÂ£o (opcional)
                </label>
                <textarea
                  id="s-desc"
                  rows={2}
                  value={novoSorteio.description}
                  onChange={(e) =>
                    setNovoSorteio((p) => ({
                      ...p,
                      description: e.target.value,
                    }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={novoSorteio.auto_execute}
                  onChange={(e) =>
                    setNovoSorteio((p) => ({
                      ...p,
                      auto_execute: e.target.checked,
                    }))
                  }
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm text-gray-700">
                  Ã°Å¸Â¤â€“ Executar automaticamente na data do sorteio
                </span>
              </label>
              {erroCriarSorteio && (
                <p className="text-sm text-red-600">{erroCriarSorteio}</p>
              )}
            </div>
            <div className="px-6 py-4 border-t flex gap-3 justify-end">
              <button
                onClick={() => setModalSorteio(false)}
                className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
              >
                Cancelar
              </button>
              <button
                onClick={criarSorteio}
                disabled={criandoSorteio}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
              >
                {criandoSorteio ? "Criando..." : "Criar Sorteio"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: CÃƒâ€œDIGOS OFFLINE (SORTEIO) Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {modalCodigosOffline && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900">
                  Ã°Å¸â€œâ€¹ CÃƒÂ³digos Offline Ã¢â‚¬â€ {modalCodigosOffline.name}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Lista de participantes para sorteio fÃƒÂ­sico
                </p>
              </div>
              <div className="flex gap-2 items-center">
                <button
                  onClick={() => window.print()}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200"
                >
                  Ã°Å¸â€“Â¨Ã¯Â¸Â Imprimir
                </button>
                <button
                  onClick={() => setModalCodigosOffline(null)}
                  className="text-gray-400 hover:text-gray-600 text-xl ml-2"
                >
                  Ãƒâ€”
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {loadingCodigosOffline ? (
                <div className="text-center text-gray-400 py-8">
                  Carregando...
                </div>
              ) : codigosOffline.length === 0 ? (
                <div className="text-center text-gray-400 py-8">
                  Nenhum participante encontrado.
                </div>
              ) : (
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-50 text-gray-600 text-xs uppercase">
                      <th className="text-center p-2 border-b w-16">NÃ‚Âº</th>
                      <th className="text-left p-2 border-b">Cliente</th>
                      <th className="text-center p-2 border-b">NÃƒÂ­vel</th>
                    </tr>
                  </thead>
                  <tbody>
                    {codigosOffline.map((c) => (
                      <tr
                        key={c.numero}
                        className="border-b last:border-0 hover:bg-gray-50"
                      >
                        <td className="p-2 text-center font-mono font-semibold text-gray-700">
                          {c.numero}
                        </td>
                        <td className="p-2 text-gray-700">
                          {c.nome || `Cliente #${c.customer_id}`}
                        </td>
                        <td className="p-2 text-center text-xs text-gray-500">
                          {c.rank_level
                            ? `${RANK_LABELS[c.rank_level]?.emoji || ""} ${RANK_LABELS[c.rank_level]?.label || c.rank_level}`
                            : "Ã¢â‚¬â€"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="px-6 py-3 border-t text-xs text-gray-400">
              {codigosOffline.length} participante(s) Ã‚Â· Sorteio:{" "}
              {modalCodigosOffline.name}
            </div>
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: LANÃƒâ€¡AR CARIMBO MANUAL Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {fidModalManual && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                Ã°Å¸ÂÂ·Ã¯Â¸Â LanÃƒÂ§ar Carimbo Manual
              </h3>
              <button
                onClick={() => setFidModalManual(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ãƒâ€”
              </button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <p className="text-sm text-gray-500">
                Cliente <strong>#{fidClienteId}</strong> Ã¢â‚¬â€ Esse carimbo serÃƒÂ¡
                registrado como manual (sem vÃƒÂ­nculo com uma venda).
              </p>
              <div>
                <label
                  htmlFor="fid-nota"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  ObservaÃƒÂ§ÃƒÂ£o (opcional)
                </label>
                <input
                  id="fid-nota"
                  type="text"
                  value={fidManualNota}
                  onChange={(e) => setFidManualNota(e.target.value)}
                  placeholder="Ex: ConversÃƒÂ£o de cartÃƒÂ£o fÃƒÂ­sico"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t flex gap-3 justify-end">
              <button
                onClick={() => setFidModalManual(false)}
                className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
              >
                Cancelar
              </button>
              <button
                onClick={lancarCarimboManual}
                disabled={fidLancandoManual}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {fidLancandoManual ? "LanÃƒÂ§ando..." : "Confirmar Carimbo"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: ENVIO EM LOTE Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {modalLote && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Ã°Å¸â€œÂ§ Envio em Lote</h3>
              <button
                onClick={() => setModalLote(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ãƒâ€”
              </button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <div>
                <label
                  htmlFor="lote-nivel"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  NÃƒÂ­vel de ranking
                </label>
                <select
                  id="lote-nivel"
                  value={loteForm.nivel}
                  onChange={(e) =>
                    setLoteForm((p) => ({ ...p, nivel: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="todos">Todos os nÃƒÂ­veis</option>
                  <option value="platinum">Ã°Å¸â€™Å½ Diamante</option>
                  <option value="diamond">Ã°Å¸â€˜â€˜ Platina</option>
                  <option value="gold">Ã°Å¸Â¥â€¡ Ouro</option>
                  <option value="silver">Ã°Å¸Â¥Ë† Prata</option>
                  <option value="bronze">Ã°Å¸Â¥â€° Bronze</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="lote-assunto"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Assunto do e-mail
                </label>
                <input
                  id="lote-assunto"
                  type="text"
                  placeholder="Ex: PromoÃƒÂ§ÃƒÂ£o exclusiva para clientes Ouro!"
                  value={loteForm.assunto}
                  onChange={(e) =>
                    setLoteForm((p) => ({ ...p, assunto: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="lote-msg"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Mensagem
                </label>
                <textarea
                  id="lote-msg"
                  rows={4}
                  placeholder="Escreva a mensagem que serÃƒÂ¡ enviada para os clientes..."
                  value={loteForm.mensagem}
                  onChange={(e) =>
                    setLoteForm((p) => ({ ...p, mensagem: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              {resultadoLote && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
                  <p className="font-semibold text-green-800">
                    Ã¢Å“â€¦ {resultadoLote.enfileirados} e-mail(s) enfileirado(s)!
                  </p>
                  {resultadoLote.sem_email > 0 && (
                    <p className="text-green-600">
                      {resultadoLote.sem_email} cliente(s) sem e-mail cadastrado
                      foram ignorados.
                    </p>
                  )}
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t flex gap-3 justify-end">
              <button
                onClick={() => setModalLote(false)}
                className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
              >
                Fechar
              </button>
              <button
                onClick={enviarLote}
                disabled={enviandoLote}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {enviandoLote ? "Enviando..." : "Enfileirar Envio"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: NOVA CAMPANHA Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {modalCriarCampanha && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Ã¢Å¾â€¢ Nova Campanha</h3>
              <button
                onClick={() => setModalCriarCampanha(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ãƒâ€”
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div>
                <label
                  htmlFor="nc-nome"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Nome da campanha
                </label>
                <input
                  id="nc-nome"
                  type="text"
                  placeholder="Ex: Recompra RÃƒÂ¡pida VerÃƒÂ£o"
                  value={novaCampanha.name}
                  onChange={(e) =>
                    setNovaCampanha((p) => ({ ...p, name: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="nc-tipo"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Tipo
                </label>
                <select
                  id="nc-tipo"
                  value={novaCampanha.campaign_type}
                  onChange={(e) =>
                    setNovaCampanha((p) => ({
                      ...p,
                      campaign_type: e.target.value,
                    }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="inactivity">Ã°Å¸ËœÂ´ Clientes Inativos</option>
                  <option value="quick_repurchase">Ã°Å¸â€Â Recompra RÃƒÂ¡pida</option>
                </select>
              </div>
              <p className="text-xs text-gray-500">
                Os parÃƒÂ¢metros poderÃƒÂ£o ser configurados depois de criar a
                campanha.
              </p>
              {erroCriarCampanha && (
                <p className="text-sm text-red-600">{erroCriarCampanha}</p>
              )}
            </div>
            <div className="px-6 py-4 border-t flex gap-3 justify-end">
              <button
                onClick={() => setModalCriarCampanha(false)}
                className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
              >
                Cancelar
              </button>
              <button
                onClick={criarCampanha}
                disabled={criandoCampanha}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {criandoCampanha ? "Criando..." : "Criar Campanha"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: CRIAR CUPOM MANUAL Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {modalCupomAberto && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                Ã°Å¸Å½Å¸Ã¯Â¸Â Criar Cupom Manual
              </h3>
              <button
                onClick={() => {
                  setModalCupomAberto(false);
                  setErroCupom("");
                }}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ãƒâ€”
              </button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <div>
                <label
                  htmlFor="cupom-tipo"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Tipo de desconto
                </label>
                <select
                  id="cupom-tipo"
                  value={novoCupom.coupon_type}
                  onChange={(e) =>
                    setNovoCupom((p) => ({ ...p, coupon_type: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="fixed">Valor fixo (R$)</option>
                  <option value="percent">Percentual (%)</option>
                  <option value="gift">Brinde (sem valor)</option>
                </select>
              </div>
              {novoCupom.coupon_type === "fixed" && (
                <div>
                  <label
                    htmlFor="cupom-valor"
                    className="block text-xs font-medium text-gray-600 mb-1"
                  >
                    Valor do desconto (R$)
                  </label>
                  <input
                    id="cupom-valor"
                    type="text"
                    placeholder="Ex: 20,00"
                    value={novoCupom.discount_value}
                    onChange={(e) =>
                      setNovoCupom((p) => ({
                        ...p,
                        discount_value: e.target.value,
                      }))
                    }
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              )}
              {novoCupom.coupon_type === "percent" && (
                <div>
                  <label
                    htmlFor="cupom-pct"
                    className="block text-xs font-medium text-gray-600 mb-1"
                  >
                    Percentual (%)
                  </label>
                  <input
                    id="cupom-pct"
                    type="number"
                    min="1"
                    max="100"
                    placeholder="Ex: 10"
                    value={novoCupom.discount_percent}
                    onChange={(e) =>
                      setNovoCupom((p) => ({
                        ...p,
                        discount_percent: e.target.value,
                      }))
                    }
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              )}
              <div>
                <label
                  htmlFor="cupom-canal"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Canal
                </label>
                <select
                  id="cupom-canal"
                  value={novoCupom.channel}
                  onChange={(e) =>
                    setNovoCupom((p) => ({ ...p, channel: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="pdv">PDV (caixa)</option>
                  <option value="ecommerce">E-commerce</option>
                  <option value="app">App</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="cupom-validade"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  VÃƒÂ¡lido atÃƒÂ© (opcional)
                </label>
                <input
                  id="cupom-validade"
                  type="date"
                  value={novoCupom.valid_until}
                  onChange={(e) =>
                    setNovoCupom((p) => ({ ...p, valid_until: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="cupom-mincompra"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Compra mÃƒÂ­nima (R$, opcional)
                </label>
                <input
                  id="cupom-mincompra"
                  type="text"
                  placeholder="Ex: 50,00"
                  value={novoCupom.min_purchase_value}
                  onChange={(e) =>
                    setNovoCupom((p) => ({
                      ...p,
                      min_purchase_value: e.target.value,
                    }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="cupom-cliente"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  ID do cliente (opcional)
                </label>
                <input
                  id="cupom-cliente"
                  type="number"
                  placeholder="Deixe vazio para cupom genÃƒÂ©rico"
                  value={novoCupom.customer_id}
                  onChange={(e) =>
                    setNovoCupom((p) => ({ ...p, customer_id: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="cupom-descricao"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  DescriÃƒÂ§ÃƒÂ£o (opcional)
                </label>
                <input
                  id="cupom-descricao"
                  type="text"
                  placeholder="Ex: Cupom de cortesia"
                  value={novoCupom.descricao}
                  onChange={(e) =>
                    setNovoCupom((p) => ({ ...p, descricao: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              {erroCupom && <p className="text-red-600 text-sm">{erroCupom}</p>}
            </div>
            <div className="px-6 py-4 border-t flex gap-3 justify-end">
              <button
                onClick={() => {
                  setModalCupomAberto(false);
                  setErroCupom("");
                }}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200"
              >
                Cancelar
              </button>
              <button
                onClick={criarCupomManual}
                disabled={criandoCupom}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {criandoCupom ? "Criando..." : "Criar Cupom"}
              </button>
            </div>
          </div>
        </div>
      )}

      {aba === "gestor" && (
        <div className="space-y-4">
          {/* HEADER + TOGGLE DE MODO */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
              <div>
                <h2 className="font-semibold text-gray-800">
                  Ã°Å¸â€ºÂ Ã¯Â¸Â Gestor de BenefÃƒÂ­cios
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {gestorModo === "cliente"
                    ? "Busque um cliente para gerenciar seus benefÃƒÂ­cios."
                    : "Selecione um tipo e veja todos os clientes participantes."}
                </p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => setGestorModo("cliente")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    gestorModo === "cliente"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  Ã°Å¸â€Â Por Cliente
                </button>
                <button
                  onClick={() => setGestorModo("campanha")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    gestorModo === "campanha"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  Ã°Å¸ÂÂ·Ã¯Â¸Â Por Campanha
                </button>
              </div>
            </div>

            {/* MODO: POR CLIENTE */}
            {gestorModo === "cliente" && (
              <div className="relative max-w-md">
                <input
                  type="text"
                  value={gestorSearch}
                  onChange={(e) => {
                    setGestorSearch(e.target.value);
                    buscarClientesGestor(e.target.value);
                  }}
                  onKeyDown={(e) =>
                    e.key === "Escape" && setGestorSugestoes([])
                  }
                  placeholder="Nome, CPF ou telefone do cliente..."
                  className="w-full border rounded-lg px-3 py-2.5 text-sm"
                  autoComplete="off"
                />
                {gestorBuscando && (
                  <span className="absolute right-3 top-3 text-xs text-gray-400 animate-pulse">
                    Buscando...
                  </span>
                )}
                {gestorSugestoes.length > 0 && (
                  <div className="absolute z-20 mt-1 w-full bg-white rounded-xl border shadow-xl overflow-hidden max-h-72 overflow-y-auto">
                    {gestorSugestoes.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => selecionarClienteGestor(c)}
                        className="w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors border-b last:border-b-0"
                      >
                        <p className="text-sm font-medium text-gray-900">
                          {c.nome}
                        </p>
                        <p className="text-xs text-gray-400">
                          {c.cpf ? `CPF: ${c.cpf}` : ""}
                          {c.cpf && c.telefone ? " Ã‚Â· " : ""}
                          {c.telefone || ""}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* MODO: POR CAMPANHA */}
            {gestorModo === "campanha" && (
              <div className="flex gap-3 flex-wrap items-center">
                <select
                  value={gestorCampanhaTipo}
                  onChange={(e) => setGestorCampanhaTipo(e.target.value)}
                  className="border rounded-lg px-3 py-2 text-sm min-w-[200px]"
                >
                  <option value="carimbos">Ã°Å¸ÂÂ·Ã¯Â¸Â CartÃƒÂ£o Fidelidade</option>
                  <option value="cashback">Ã°Å¸â€™Â° Cashback (saldo positivo)</option>
                  <option value="cupons">Ã°Å¸Å½Å¸Ã¯Â¸Â Cupons Ativos</option>
                  <option value="ranking">Ã°Å¸Ââ€  Ranking (mÃƒÂªs atual)</option>
                </select>
                <button
                  onClick={() =>
                    carregarClientesPorCampanha(gestorCampanhaTipo)
                  }
                  disabled={gestorCampanhaCarregando}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  {gestorCampanhaCarregando
                    ? "Carregando..."
                    : "Buscar Clientes"}
                </button>
              </div>
            )}
          </div>

          {/* LISTA DE CLIENTES POR CAMPANHA */}
          {gestorModo === "campanha" && gestorCampanhaCarregando && (
            <div className="text-center py-12 text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-sm">Carregando clientes...</p>
            </div>
          )}
          {gestorModo === "campanha" &&
            gestorCampanhaLista !== null &&
            !gestorCampanhaCarregando && (
              <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <div className="px-6 py-3 bg-gray-50 border-b flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-700">
                    {gestorCampanhaLista.length === 0
                      ? "Nenhum cliente encontrado"
                      : `${gestorCampanhaLista.length} cliente(s) encontrado(s)`}
                  </p>
                  <p className="text-xs text-gray-400">
                    Clique em Ã¢â‚¬Å“Ver detalhesÃ¢â‚¬Â para gerenciar
                  </p>
                </div>
                {gestorCampanhaLista.length === 0 ? (
                  <div className="p-10 text-center text-gray-400 text-sm">
                    Nenhum cliente ativo neste tipo de campanha.
                  </div>
                ) : (
                  <div className="divide-y max-h-[600px] overflow-y-auto">
                    {gestorCampanhaLista.map((c) => (
                      <div
                        key={c.id}
                        className="flex items-center gap-4 px-6 py-3 hover:bg-gray-50 transition-colors"
                      >
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold text-sm shrink-0">
                          {c.nome?.[0]?.toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {c.nome}
                          </p>
                          <p className="text-xs text-gray-400">
                            {c.cpf ? `CPF: ${c.cpf}` : ""}
                            {c.cpf && c.telefone ? " Ã‚Â· " : ""}
                            {c.telefone || ""}
                          </p>
                        </div>
                        <span className="px-3 py-1 bg-blue-50 text-blue-700 text-xs rounded-full font-medium shrink-0">
                          {c.detalhe}
                        </span>
                        <button
                          onClick={() => abrirClienteNoGestor(c)}
                          className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 font-medium shrink-0"
                        >
                          Ver detalhes Ã¢â€ â€™
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

          {/* LOADING E DETALHES DO CLIENTE (modo Por Cliente) */}
          {gestorModo === "cliente" && gestorCarregando && (
            <div className="text-center py-12 text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-sm">Carregando dados do cliente...</p>
            </div>
          )}

          {gestorModo === "cliente" &&
            gestorCliente &&
            gestorSaldo &&
            !gestorCarregando && (
              <>
                {/* CARD DO CLIENTE */}
                <div className="bg-white rounded-xl border shadow-sm p-4 flex items-center gap-4">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold text-lg shrink-0">
                    {gestorCliente.nome?.[0]?.toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 truncate">
                      {gestorCliente.nome}
                    </p>
                    <p className="text-xs text-gray-400">
                      ID #{gestorCliente.id} Ã‚Â·{" "}
                      {gestorCliente.telefone ||
                        gestorCliente.celular ||
                        "Sem telefone"}
                    </p>
                  </div>
                  {(() => {
                    const r =
                      RANK_LABELS[gestorSaldo.rank_level] || RANK_LABELS.bronze;
                    return (
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium shrink-0 ${r.color}`}
                      >
                        {r.emoji} {r.label}
                      </span>
                    );
                  })()}
                </div>

                {/* Ã¢â€â‚¬Ã¢â€â‚¬ SeÃƒÂ§ÃƒÂ£o: Carimbos Ã¢â€â‚¬Ã¢â€â‚¬ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(
                        gestorSecao === "carimbos" ? null : "carimbos",
                      )
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">Ã°Å¸ÂÂ·Ã¯Â¸Â</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">
                          CartÃƒÂ£o Fidelidade
                        </p>
                        <p className="text-xs text-gray-500">
                          {gestorSaldo.total_carimbos} carimbo(s) ativo(s)
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "carimbos" ? "Ã¢â€“Â²" : "Ã¢â€“Â¼"}
                    </span>
                  </button>
                  {gestorSecao === "carimbos" && (
                    <div className="border-t p-6 space-y-4">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <p className="text-sm font-medium text-green-800 mb-3">
                          Ã¢Å¾â€¢ LanÃƒÂ§ar Carimbo Manual
                        </p>
                        <div className="flex gap-3 flex-wrap items-end">
                          <div className="flex-1 min-w-[200px]">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              ObservaÃƒÂ§ÃƒÂ£o (opcional)
                            </label>
                            <input
                              type="text"
                              value={gestorCarimboNota}
                              onChange={(e) =>
                                setGestorCarimboNota(e.target.value)
                              }
                              placeholder="Ex: ConversÃƒÂ£o de cartÃƒÂ£o fÃƒÂ­sico"
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            />
                          </div>
                          <button
                            onClick={lancarCarimboGestor}
                            disabled={gestorLancandoCarimbo}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                          >
                            {gestorLancandoCarimbo
                              ? "LanÃƒÂ§ando..."
                              : "Ã¢Å“â€¦ LanÃƒÂ§ar Carimbo"}
                          </button>
                        </div>
                      </div>
                      {gestorCarimbos && gestorCarimbos.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                                  #ID
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                                  Data
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                                  Origem
                                </th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                                  Obs
                                </th>
                                <th className="px-4 py-2 text-center text-xs font-medium text-gray-600">
                                  Status
                                </th>
                                <th className="px-4 py-2 text-center text-xs font-medium text-gray-600">
                                  AÃƒÂ§ÃƒÂ£o
                                </th>
                              </tr>
                            </thead>
                            <tbody className="divide-y">
                              {gestorCarimbos
                                .filter(
                                  (s) =>
                                    !s.voided_at || gestorIncluirEstornados,
                                )
                                .map((s) => (
                                  <tr
                                    key={s.id}
                                    className={
                                      s.voided_at
                                        ? "bg-red-50 opacity-60"
                                        : "hover:bg-gray-50"
                                    }
                                  >
                                    <td className="px-4 py-2 text-gray-500 font-mono text-xs">
                                      {s.id}
                                    </td>
                                    <td className="px-4 py-2 text-gray-700 text-xs whitespace-nowrap">
                                      {new Date(s.created_at).toLocaleString(
                                        "pt-BR",
                                      )}
                                    </td>
                                    <td className="px-4 py-2">
                                      {s.is_manual ? (
                                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                                          Manual
                                        </span>
                                      ) : (
                                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                                          AutomÃƒÂ¡tico
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-4 py-2 text-gray-500 text-xs max-w-[180px] truncate">
                                      {s.notes || "Ã¢â‚¬â€"}
                                    </td>
                                    <td className="px-4 py-2 text-center">
                                      {s.voided_at ? (
                                        <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">
                                          Estornado
                                        </span>
                                      ) : (
                                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                                          Ativo
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-4 py-2 text-center">
                                      {!s.voided_at && (
                                        <button
                                          onClick={() =>
                                            estornarCarimboGestor(s.id)
                                          }
                                          disabled={gestorRemovendo === s.id}
                                          className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 disabled:opacity-50"
                                        >
                                          {gestorRemovendo === s.id
                                            ? "..."
                                            : "Ã¢ÂÅ’ Remover"}
                                        </button>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-center text-gray-400 py-4 text-sm">
                          Nenhum carimbo encontrado.
                        </p>
                      )}
                      <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={gestorIncluirEstornados}
                          onChange={(e) =>
                            setGestorIncluirEstornados(e.target.checked)
                          }
                          className="rounded"
                        />
                        Mostrar estornados
                      </label>
                    </div>
                  )}
                </div>

                {/* Ã¢â€â‚¬Ã¢â€â‚¬ SeÃƒÂ§ÃƒÂ£o: Cashback Ã¢â€â‚¬Ã¢â€â‚¬ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(
                        gestorSecao === "cashback" ? null : "cashback",
                      )
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">Ã°Å¸â€™Â°</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Cashback</p>
                        <p className="text-xs text-gray-500">
                          Saldo: R$ {formatBRL(gestorSaldo.saldo_cashback)}
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "cashback" ? "Ã¢â€“Â²" : "Ã¢â€“Â¼"}
                    </span>
                  </button>
                  {gestorSecao === "cashback" && (
                    <div className="border-t p-6 space-y-4">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                        <p className="text-xs text-gray-500 mb-1">
                          Saldo atual
                        </p>
                        <p className="text-3xl font-bold text-green-700">
                          R$ {formatBRL(gestorSaldo.saldo_cashback)}
                        </p>
                      </div>
                      <div
                        className={`border rounded-lg p-4 space-y-3 ${gestorCashbackTipo === "debito" ? "bg-red-50 border-red-200" : "bg-blue-50 border-blue-200"}`}
                      >
                        <p className="text-sm font-medium text-gray-700">
                          Ã¢Å“ÂÃ¯Â¸Â Ajuste Manual
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              Tipo
                            </label>
                            <select
                              value={gestorCashbackTipo}
                              onChange={(e) =>
                                setGestorCashbackTipo(e.target.value)
                              }
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            >
                              <option value="credito">
                                Ã¢Å¾â€¢ CrÃƒÂ©dito (adicionar)
                              </option>
                              <option value="debito">
                                Ã¢Å¾â€“ DÃƒÂ©bito (remover)
                              </option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              Valor (R$)
                            </label>
                            <input
                              type="number"
                              min="0.01"
                              step="0.01"
                              value={gestorCashbackValor}
                              onChange={(e) =>
                                setGestorCashbackValor(e.target.value)
                              }
                              placeholder="0,00"
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            />
                          </div>
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              Motivo (opcional)
                            </label>
                            <input
                              type="text"
                              value={gestorCashbackDesc}
                              onChange={(e) =>
                                setGestorCashbackDesc(e.target.value)
                              }
                              placeholder="Ex: CorreÃƒÂ§ÃƒÂ£o de campanha"
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            />
                          </div>
                        </div>
                        <button
                          onClick={ajustarCashbackGestor}
                          disabled={
                            gestorLancandoCashback || !gestorCashbackValor
                          }
                          className={`w-full py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50 ${gestorCashbackTipo === "debito" ? "bg-red-600 hover:bg-red-700" : "bg-blue-600 hover:bg-blue-700"}`}
                        >
                          {gestorLancandoCashback
                            ? "Salvando..."
                            : gestorCashbackTipo === "debito"
                              ? "Ã¢Å¾â€“ Confirmar DÃƒÂ©bito"
                              : "Ã¢Å¾â€¢ Confirmar CrÃƒÂ©dito"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Ã¢â€â‚¬Ã¢â€â‚¬ SeÃƒÂ§ÃƒÂ£o: Cupons Ã¢â€â‚¬Ã¢â€â‚¬ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(gestorSecao === "cupons" ? null : "cupons")
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">Ã°Å¸Å½Å¸Ã¯Â¸Â</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Cupons</p>
                        <p className="text-xs text-gray-500">
                          {gestorCupons?.filter((c) => c.status === "active")
                            .length || 0}{" "}
                          ativo(s) Ã‚Â· {gestorCupons?.length || 0} no total
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "cupons" ? "Ã¢â€“Â²" : "Ã¢â€“Â¼"}
                    </span>
                  </button>
                  {gestorSecao === "cupons" && (
                    <div className="border-t">
                      {gestorCupons && gestorCupons.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                                  CÃƒÂ³digo
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                                  Desconto
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                                  Validade
                                </th>
                                <th className="px-4 py-3 text-center text-xs font-medium text-gray-600">
                                  Status
                                </th>
                                <th className="px-4 py-3 text-center text-xs font-medium text-gray-600">
                                  AÃƒÂ§ÃƒÂ£o
                                </th>
                              </tr>
                            </thead>
                            <tbody className="divide-y">
                              {gestorCupons.map((c) => (
                                <tr
                                  key={c.id}
                                  className={
                                    c.status !== "active"
                                      ? "bg-gray-50 opacity-70"
                                      : "hover:bg-gray-50"
                                  }
                                >
                                  <td className="px-4 py-3 font-mono text-xs font-bold text-gray-800">
                                    {c.code}
                                  </td>
                                  <td className="px-4 py-3 text-xs text-gray-700">
                                    {c.coupon_type === "gift"
                                      ? "Ã°Å¸Å½Â Brinde"
                                      : c.coupon_type === "percent"
                                        ? `${c.discount_percent}%`
                                        : `R$ ${formatBRL(c.discount_value)}`}
                                  </td>
                                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                                    {c.valid_until
                                      ? new Date(
                                          c.valid_until,
                                        ).toLocaleDateString("pt-BR")
                                      : "Indeterminado"}
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <span
                                      className={`px-2 py-0.5 text-xs rounded-full ${CUPOM_STATUS[c.status]?.color || "bg-gray-100 text-gray-600"}`}
                                    >
                                      {CUPOM_STATUS[c.status]?.label ||
                                        c.status}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    {c.status === "active" && (
                                      <button
                                        onClick={() =>
                                          anularCupomGestor(c.code)
                                        }
                                        disabled={gestorAnulando === c.code}
                                        className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 disabled:opacity-50"
                                      >
                                        {gestorAnulando === c.code
                                          ? "..."
                                          : "Ã°Å¸Å¡Â« Anular"}
                                      </button>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="p-8 text-center text-gray-400 text-sm">
                          Nenhum cupom encontrado.
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Ã¢â€â‚¬Ã¢â€â‚¬ SeÃƒÂ§ÃƒÂ£o: Ranking Ã¢â€â‚¬Ã¢â€â‚¬ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(
                        gestorSecao === "ranking" ? null : "ranking",
                      )
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">Ã°Å¸Ââ€ </span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Ranking</p>
                        <p className="text-xs text-gray-500">
                          {(() => {
                            const r =
                              RANK_LABELS[gestorSaldo.rank_level] ||
                              RANK_LABELS.bronze;
                            return `${r.emoji} ${r.label}`;
                          })()}
                          {gestorSaldo.rank_period
                            ? ` Ã‚Â· ${gestorSaldo.rank_period}`
                            : ""}
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "ranking" ? "Ã¢â€“Â²" : "Ã¢â€“Â¼"}
                    </span>
                  </button>
                  {gestorSecao === "ranking" && (
                    <div className="border-t p-6">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                          {
                            label: "NÃƒÂ­vel",
                            value: (() => {
                              const r =
                                RANK_LABELS[gestorSaldo.rank_level] ||
                                RANK_LABELS.bronze;
                              return `${r.emoji} ${r.label}`;
                            })(),
                          },
                          {
                            label: "PerÃƒÂ­odo",
                            value: gestorSaldo.rank_period || "Ã¢â‚¬â€",
                          },
                          {
                            label: "Total Gasto (12m)",
                            value: `R$ ${formatBRL(gestorSaldo.rank_total_spent || 0)}`,
                          },
                          {
                            label: "Compras (12m)",
                            value: String(
                              gestorSaldo.rank_total_purchases || 0,
                            ),
                          },
                        ].map((item) => (
                          <div
                            key={item.label}
                            className="bg-gray-50 rounded-lg p-3 text-center"
                          >
                            <p className="text-xs text-gray-500 mb-1">
                              {item.label}
                            </p>
                            <p className="font-semibold text-gray-800 text-sm">
                              {item.value}
                            </p>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-400 mt-4 text-center">
                        O nÃƒÂ­vel de ranking ÃƒÂ© recalculado automaticamente no dia
                        1 de cada mÃƒÂªs.
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: CONFIGURAÃƒâ€¡Ãƒâ€¢ES Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {aba === "config" && (
        <div className="space-y-6">
          {/* Header */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="font-semibold text-gray-800 mb-1">
              Ã¢Å¡â„¢Ã¯Â¸Â ConfiguraÃƒÂ§ÃƒÂµes de Envio
            </h2>
            <p className="text-xs text-gray-500">
              Defina os horÃƒÂ¡rios em que o sistema envia as mensagens automÃƒÂ¡ticas
              de cada campanha.
            </p>
          </div>

          {/* Loading */}
          {schedulerConfigLoading && (
            <div className="text-center py-12 text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-sm">Carregando configuraÃƒÂ§ÃƒÂµes...</p>
            </div>
          )}

          {/* FormulÃƒÂ¡rio */}
          {schedulerConfig && !schedulerConfigLoading && (
            <div className="space-y-4">
              {/* Card: AniversÃƒÂ¡rios */}
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-3 mb-5">
                  <span className="text-2xl">Ã°Å¸Å½â€š</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Mensagens de AniversÃƒÂ¡rio
                    </h3>
                    <p className="text-xs text-gray-500">
                      Enviadas todos os dias para aniversariantes do dia
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-sm text-gray-600 w-44">
                    Hora de envio:
                  </label>
                  <select
                    value={schedulerConfig.birthday_send_hour}
                    onChange={(e) =>
                      setSchedulerConfig({
                        ...schedulerConfig,
                        birthday_send_hour: Number(e.target.value),
                      })
                    }
                    className="border rounded-lg px-3 py-2 text-sm"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>
                        {String(i).padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Card: Inatividade */}
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-3 mb-5">
                  <span className="text-2xl">Ã°Å¸ËœÂ´</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Mensagens de ReativaÃƒÂ§ÃƒÂ£o (Clientes Inativos)
                    </h3>
                    <p className="text-xs text-gray-500">
                      Enviadas uma vez por semana para clientes sem compras hÃƒÂ¡
                      muito tempo
                    </p>
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-4">
                  <div className="flex items-center gap-3">
                    <label className="text-sm text-gray-600 w-44">
                      Dia da semana:
                    </label>
                    <select
                      value={schedulerConfig.inactivity_day_of_week}
                      onChange={(e) =>
                        setSchedulerConfig({
                          ...schedulerConfig,
                          inactivity_day_of_week: e.target.value,
                        })
                      }
                      className="border rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="mon">Segunda-feira</option>
                      <option value="tue">TerÃƒÂ§a-feira</option>
                      <option value="wed">Quarta-feira</option>
                      <option value="thu">Quinta-feira</option>
                      <option value="fri">Sexta-feira</option>
                      <option value="sat">SÃƒÂ¡bado</option>
                      <option value="sun">Domingo</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="text-sm text-gray-600 w-44">
                      Hora de envio:
                    </label>
                    <select
                      value={schedulerConfig.inactivity_send_hour}
                      onChange={(e) =>
                        setSchedulerConfig({
                          ...schedulerConfig,
                          inactivity_send_hour: Number(e.target.value),
                        })
                      }
                      className="border rounded-lg px-3 py-2 text-sm"
                    >
                      {Array.from({ length: 24 }, (_, i) => (
                        <option key={i} value={i}>
                          {String(i).padStart(2, "0")}:00
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Auto-envio do Destaque Mensal */}
              <div className="border rounded-xl p-5">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">Ã°Å¸Ââ€¦</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Auto-envio do Destaque Mensal
                    </h3>
                    <p className="text-xs text-gray-500">
                      Calcula e envia automaticamente o cupom ao vencedor do mÃƒÂªs
                      no dia 1 ÃƒÂ s 08:00
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={schedulerConfig.auto_destaque_mensal ?? false}
                      onChange={(e) =>
                        setSchedulerConfig({
                          ...schedulerConfig,
                          auto_destaque_mensal: e.target.checked,
                        })
                      }
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-sm text-gray-700">
                      Ativar envio automÃƒÂ¡tico do Destaque Mensal
                    </span>
                  </label>
                  {schedulerConfig.auto_destaque_mensal && (
                    <div className="flex flex-col sm:flex-row gap-4 pl-6">
                      <div className="flex items-center gap-3">
                        <label className="text-sm text-gray-600 w-44">
                          Valor do cupom (R$):
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={
                            schedulerConfig.auto_destaque_coupon_value ?? 50
                          }
                          onChange={(e) =>
                            setSchedulerConfig({
                              ...schedulerConfig,
                              auto_destaque_coupon_value:
                                parseFloat(e.target.value) || 0,
                            })
                          }
                          className="border rounded-lg px-3 py-2 text-sm w-28"
                        />
                      </div>
                      <div className="flex items-center gap-3">
                        <label className="text-sm text-gray-600 w-44">
                          Validade (dias):
                        </label>
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={
                            schedulerConfig.auto_destaque_coupon_days ?? 10
                          }
                          onChange={(e) =>
                            setSchedulerConfig({
                              ...schedulerConfig,
                              auto_destaque_coupon_days:
                                parseInt(e.target.value, 10) || 10,
                            })
                          }
                          className="border rounded-lg px-3 py-2 text-sm w-28"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* BotÃƒÂ£o salvar */}
              <div className="flex justify-end">
                <button
                  onClick={salvarSchedulerConfig}
                  disabled={schedulerConfigSalvando}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {schedulerConfigSalvando
                    ? "Salvando..."
                    : "Ã°Å¸â€™Â¾ Salvar ConfiguraÃƒÂ§ÃƒÂµes"}
                </button>
              </div>

              {/* Nota informativa */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <p className="text-xs text-amber-700">
                  Ã¢Å¡Â Ã¯Â¸Â <strong>AtenÃƒÂ§ÃƒÂ£o:</strong> Os horÃƒÂ¡rios aqui salvos sÃƒÂ£o
                  registrados no sistema. O scheduler usarÃƒÂ¡ os novos valores a
                  partir do prÃƒÂ³ximo reinÃƒÂ­cio do servidor. Para aplicar
                  imediatamente em produÃƒÂ§ÃƒÂ£o, avise o suporte tÃƒÂ©cnico.
                </p>
              </div>
            </div>
          )}

          {/* Estado vazio */}
          {!schedulerConfig && !schedulerConfigLoading && (
            <div className="bg-white rounded-xl border shadow-sm p-6 text-center">
              <p className="text-sm text-gray-500 mb-2">
                NÃƒÂ£o foi possÃƒÂ­vel carregar as configuraÃƒÂ§ÃƒÂµes.
              </p>
              <p className="text-xs text-gray-400">
                Certifique-se de que as campanhas padrÃƒÂ£o foram inicializadas
                (botÃƒÂ£o &quot;Inicializar Campanhas&quot; na aba Campanhas).
              </p>
            </div>
          )}
        </div>
      )}

      {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: DESCONTOS POR CANAL Ã¢â€â‚¬Ã¢â€â‚¬ */}
      {aba === "canais" && <CanalDescontos />}
    </div>
  );
}

