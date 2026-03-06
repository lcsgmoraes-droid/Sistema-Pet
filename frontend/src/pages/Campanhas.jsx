import { useCallback, useEffect, useState } from "react";
import api from "../api";
import { formatBRL } from "../utils/formatters";

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

function RetencaoForm({ inicial, salvando, onSalvar, onCancelar }) {
  const [form, setForm] = useState({ ...inicial });
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const isNew = !form.id;
  return (
    <div className="bg-orange-50 border border-orange-300 rounded-xl p-4 space-y-3">
      <p className="font-semibold text-orange-800">
        {isNew ? "➕ Nova Regra" : "✏️ Editar Regra"}
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="md:col-span-2">
          <label
            htmlFor="ret-name"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Nome da regra
          </label>
          <input
            id="ret-name"
            type="text"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="Ex: Retenção 30 dias"
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
        </div>
        <CampanhaField
          label="Dias sem compra"
          id="ret-dias"
          type="number"
          step="1"
          min="1"
          value={form.inactivity_days}
          onChange={(e) =>
            set("inactivity_days", Number.parseInt(e.target.value) || 30)
          }
        />
        <CampanhaSel
          label="Tipo de desconto"
          id="ret-tipo"
          value={form.coupon_type}
          onChange={(e) => set("coupon_type", e.target.value)}
        >
          <option value="percent">Percentual (%)</option>
          <option value="fixed">Valor fixo (R$)</option>
        </CampanhaSel>
        <CampanhaField
          label={
            form.coupon_type === "percent" ? "Percentual (%)" : "Valor (R$)"
          }
          id="ret-val"
          value={form.coupon_value}
          onChange={(e) =>
            set("coupon_value", Number.parseFloat(e.target.value) || 0)
          }
        />
        <CampanhaField
          label="Validade do cupom (dias)"
          id="ret-valid"
          type="number"
          step="1"
          min="1"
          value={form.coupon_valid_days}
          onChange={(e) =>
            set("coupon_valid_days", Number.parseInt(e.target.value) || 7)
          }
        />
        <CampanhaSel
          label="Canal"
          id="ret-canal"
          value={form.coupon_channel}
          onChange={(e) => set("coupon_channel", e.target.value)}
        >
          <option value="all">Todos os canais</option>
          <option value="pdv">PDV</option>
          <option value="app">App</option>
          <option value="ecommerce">Ecommerce</option>
        </CampanhaSel>
        <div className="md:col-span-2">
          <label
            htmlFor="ret-msg"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Mensagem de notificação
          </label>
          <input
            id="ret-msg"
            type="text"
            value={form.notification_message}
            onChange={(e) => set("notification_message", e.target.value)}
            placeholder="Olá, {nome}! Sentimos sua falta. Cupom: {code}"
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
          <p className="text-xs text-gray-400 mt-0.5">
            Variáveis: {"{nome}"}, {"{code}"}, {"{value}"}
          </p>
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onSalvar(form)}
          disabled={salvando || !form.name.trim()}
          className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm font-medium disabled:opacity-50"
        >
          {salvando ? "Salvando..." : "💾 Salvar"}
        </button>
        <button
          onClick={onCancelar}
          disabled={salvando}
          className="px-4 py-2 border text-gray-600 rounded-lg hover:bg-gray-50 text-sm"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}

export default function Campanhas() {
  const [aba, setAba] = useState("dashboard");

  // Campanhas
  const [campanhas, setCampanhas] = useState([]);
  const [loadingCampanhas, setLoadingCampanhas] = useState(true);
  const [toggling, setToggling] = useState(null);
  const [campanhaEditando, setCampanhaEditando] = useState(null);
  const [paramsEditando, setParamsEditando] = useState({});
  const [salvandoParams, setSalvandoParams] = useState(false);

  // Dashboard
  const [dashboard, setDashboard] = useState(null);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  // Envio escalonado de inativos
  const [modalEnvioInativos, setModalEnvioInativos] = useState(null); // null | 30 | 60 | 90
  const [envioInativosForm, setEnvioInativosForm] = useState({
    assunto: "Sentimos sua falta! 🐾",
    mensagem: "",
  });
  const [enviandoInativos, setEnviandoInativos] = useState(false);
  const [resultadoEnvioInativos, setResultadoEnvioInativos] = useState(null);

  // Retenção Dinâmica
  const [retencaoRegras, setRetencaoRegras] = useState([]);
  const [loadingRetencao, setLoadingRetencao] = useState(false);
  const [retencaoEditando, setRetencaoEditando] = useState(null); // null | {} (nova) | {id,...} (existente)
  const [salvandoRetencao, setSalvandoRetencao] = useState(false);
  const [deletandoRetencao, setDeletandoRetencao] = useState(null);

  // Ranking
  const [ranking, setRanking] = useState(null);
  const [loadingRanking, setLoadingRanking] = useState(false);
  const [filtroNivel, setFiltroNivel] = useState("todos");

  // Cupons
  const [cupons, setCupons] = useState([]);
  const [loadingCupons, setLoadingCupons] = useState(true);
  const [filtroCupomStatus, setFiltroCupomStatus] = useState("active");
  const [filtroCupomBusca, setFiltroCupomBusca] = useState("");
  const [filtroCupomDataInicio, setFiltroCupomDataInicio] = useState("");
  const [filtroCupomDataFim, setFiltroCupomDataFim] = useState("");
  const [cupomDetalhes, setCupomDetalhes] = useState(null);
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
  const [destaque, setDestaque] = useState(null);
  const [loadingDestaque, setLoadingDestaque] = useState(false);
  const [enviandoDestaque, setEnviandoDestaque] = useState(false);
  const [destaqueResultado, setDestaqueResultado] = useState(null);
  const [premiosPorVencedor, setPremiosPorVencedor] = useState({});
  const [vencedoresSelecionados, setVencedoresSelecionados] = useState({});
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
  const [sorteios, setSorteios] = useState([]);
  const [loadingSorteios, setLoadingSorteios] = useState(false);
  const [modalSorteio, setModalSorteio] = useState(false);
  const [novoSorteio, setNovoSorteio] = useState({
    name: "",
    description: "",
    prize_description: "",
    rank_filter: "",
    draw_date: "",
  });
  const [criandoSorteio, setCriandoSorteio] = useState(false);
  const [erroCriarSorteio, setErroCriarSorteio] = useState("");
  const [executandoSorteio, setExecutandoSorteio] = useState(null);
  const [inscrevendo, setInscrevendo] = useState(null);
  const [sorteioResultado, setSorteioResultado] = useState(null);

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
  const [sugestoes, setSugestoes] = useState([]);
  const [loadingSugestoes, setLoadingSugestoes] = useState(false);
  const [confirmandoMerge, setConfirmandoMerge] = useState(null);
  const [resultadoMerge, setResultadoMerge] = useState(null);

  // Relatórios
  const [relatorio, setRelatorio] = useState(null);
  const [loadingRelatorio, setLoadingRelatorio] = useState(false);
  const [relDataInicio, setRelDataInicio] = useState(primeiroDiaMes);
  const [relDataFim, setRelDataFim] = useState(hoje);
  const [relTipo, setRelTipo] = useState("todos");

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
  const [rankingConfig, setRankingConfig] = useState(null);
  const [rankingConfigLoading, setRankingConfigLoading] = useState(false);
  const [rankingConfigSalvando, setRankingConfigSalvando] = useState(false);

  const carregarDashboard = useCallback(async () => {
    setLoadingDashboard(true);
    try {
      const res = await api.get("/campanhas/dashboard");
      setDashboard(res.data);
    } catch (e) {
      console.error("Erro ao carregar dashboard:", e);
    } finally {
      setLoadingDashboard(false);
    }
  }, []);

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

  const carregarCampanhas = useCallback(async () => {
    setLoadingCampanhas(true);
    try {
      const res = await api.get("/campanhas");
      // Se não há nenhuma campanha, inicializa automaticamente as campanhas padrão
      if (res.data.length === 0) {
        try {
          await api.post("/campanhas/seed");
          const res2 = await api.get("/campanhas");
          setCampanhas(res2.data);
        } catch {
          setCampanhas([]);
        }
      } else {
        setCampanhas(res.data);
      }
    } catch (e) {
      console.error("Erro ao carregar campanhas:", e);
    } finally {
      setLoadingCampanhas(false);
    }
  }, []);

  const carregarRanking = useCallback(async () => {
    setLoadingRanking(true);
    try {
      const params = filtroNivel !== "todos" ? `?nivel=${filtroNivel}` : "";
      const res = await api.get(`/campanhas/ranking${params}`);
      setRanking(res.data);
    } catch (e) {
      console.error("Erro ao carregar ranking:", e);
    } finally {
      setLoadingRanking(false);
    }
  }, [filtroNivel]);

  const carregarCupons = useCallback(async () => {
    setLoadingCupons(true);
    try {
      const params = new URLSearchParams();
      if (filtroCupomStatus !== "todos")
        params.set("status", filtroCupomStatus);
      if (filtroCupomBusca.trim()) params.set("busca", filtroCupomBusca.trim());
      if (filtroCupomDataInicio)
        params.set("data_inicio", filtroCupomDataInicio);
      if (filtroCupomDataFim) params.set("data_fim", filtroCupomDataFim);
      const qs = params.toString() ? `?${params.toString()}` : "";
      const res = await api.get(`/campanhas/cupons${qs}`);
      setCupons(res.data);
    } catch (e) {
      console.error("Erro ao carregar cupons:", e);
    } finally {
      setLoadingCupons(false);
    }
  }, [
    filtroCupomStatus,
    filtroCupomBusca,
    filtroCupomDataInicio,
    filtroCupomDataFim,
  ]);

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

  const carregarRelatorio = useCallback(async () => {
    setLoadingRelatorio(true);
    try {
      const params = new URLSearchParams();
      if (relDataInicio) params.set("data_inicio", relDataInicio);
      if (relDataFim) params.set("data_fim", relDataFim);
      if (relTipo !== "todos") params.set("tipo", relTipo);
      const res = await api.get(`/campanhas/relatorio?${params}`);
      setRelatorio(res.data);
    } catch (e) {
      console.error("Erro ao carregar relatório:", e);
    } finally {
      setLoadingRelatorio(false);
    }
  }, [relDataInicio, relDataFim, relTipo]);

  const carregarDestaque = useCallback(async () => {
    setLoadingDestaque(true);
    try {
      const res = await api.get("/campanhas/destaque-mensal");
      setDestaque(res.data);
      // Inicializa config de prêmio individual para cada vencedor
      const inicial = {};
      const selecionados = {};
      for (const cat of Object.keys(res.data.vencedores || {})) {
        inicial[cat] = _defaultPremio();
        selecionados[cat] = true;
      }
      setPremiosPorVencedor(inicial);
      setVencedoresSelecionados(selecionados);
    } catch (e) {
      console.error("Erro ao carregar destaque:", e);
    } finally {
      setLoadingDestaque(false);
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
      alert("Erro ao arquivar: " + (e?.response?.data?.detail || e.message));
    } finally {
      setArquivando(null);
    }
  };

  const carregarSorteios = useCallback(async () => {
    setLoadingSorteios(true);
    try {
      const res = await api.get("/campanhas/sorteios");
      setSorteios(res.data);
    } catch (e) {
      console.error("Erro ao carregar sorteios:", e);
    } finally {
      setLoadingSorteios(false);
    }
  }, []);

  const carregarSugestoes = useCallback(async () => {
    setLoadingSugestoes(true);
    setResultadoMerge(null);
    try {
      const res = await api.get("/campanhas/unificacao/sugestoes");
      setSugestoes(res.data);
    } catch (e) {
      console.error("Erro ao carregar sugestões:", e);
    } finally {
      setLoadingSugestoes(false);
    }
  }, []);

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

  const carregarRankingConfig = useCallback(async () => {
    setRankingConfigLoading(true);
    try {
      const res = await api.get("/campanhas/ranking/config");
      setRankingConfig(res.data);
    } catch (e) {
      console.error("Erro ao carregar config de ranking:", e);
    } finally {
      setRankingConfigLoading(false);
    }
  }, []);

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

  useEffect(() => {
    carregarDashboard();
  }, [carregarDashboard]);
  useEffect(() => {
    carregarCampanhas();
  }, [carregarCampanhas]);
  useEffect(() => {
    if (aba === "ranking") {
      carregarRanking();
      carregarRankingConfig();
    }
  }, [aba, carregarRanking, carregarRankingConfig]);
  useEffect(() => {
    if (aba === "destaque") carregarDestaque();
  }, [aba, carregarDestaque]);
  useEffect(() => {
    if (aba === "sorteios") carregarSorteios();
  }, [aba, carregarSorteios]);
  useEffect(() => {
    if (aba === "unificacao") carregarSugestoes();
  }, [aba, carregarSugestoes]);
  useEffect(() => {
    carregarCupons();
  }, [carregarCupons]);
  useEffect(() => {
    if (aba === "relatorios") carregarRelatorio();
  }, [aba, carregarRelatorio]);

  // Retenção — carrega ao entrar na aba
  const carregarRetencao = useCallback(async () => {
    setLoadingRetencao(true);
    try {
      const res = await api.get("/campanhas/retencao");
      setRetencaoRegras(res.data);
    } catch (e) {
      console.error("Erro ao carregar regras de retenção", e);
    } finally {
      setLoadingRetencao(false);
    }
  }, []);
  useEffect(() => {
    if (aba === "retencao") carregarRetencao();
  }, [aba, carregarRetencao]);

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
    setParamsEditando({ ...c.params });
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
      return params.coupon_type === "percent"
        ? `${params.coupon_value || "?"}% de desconto • ${params.coupon_valid_days || "?"} dias`
        : `R$ ${formatBRL(params.coupon_value || 0)} de desconto • ${params.coupon_valid_days || "?"} dias`;
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
        </div>
      );
    }

    if (["birthday", "birthday_customer", "birthday_pet"].includes(tipo))
      return (
        <div className="grid grid-cols-2 gap-3">
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
              str("coupon_type") === "percent" ? "Percentual (%)" : "Valor (R$)"
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
              set("coupon_valid_days", Number.parseInt(e.target.value, 10) || 3)
            }
          />
          <div className="col-span-2">
            <label
              htmlFor="p-bday-msg"
              className="block text-xs font-medium text-gray-600 mb-1"
            >
              Mensagem personalizada
            </label>
            <input
              id="p-bday-msg"
              type="text"
              value={str("notification_message")}
              onChange={(e) => set("notification_message", e.target.value)}
              placeholder="Ex: Feliz aniversário! Use seu cupom especial."
              className="w-full border rounded-lg px-3 py-1.5 text-sm"
            />
          </div>
        </div>
      );

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
        diamond: "� Platina",
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
        <button
          onClick={() => setModalCupomAberto(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + Criar Cupom Manual
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b overflow-x-auto">
        {[
          { id: "dashboard", label: "📊 Dashboard" },
          { id: "campanhas", label: "📋 Campanhas" },
          { id: "retencao", label: "🔄 Retenção" },
          { id: "destaque", label: "🌟 Destaque Mensal" },
          { id: "sorteios", label: "🎲 Sorteios" },
          { id: "ranking", label: "🏆 Ranking" },
          { id: "cupons", label: "🎟️ Cupons" },
          { id: "unificacao", label: "🔗 Unificação" },
          { id: "relatorios", label: "📈 Relatórios" },
          { id: "gestor", label: "🛠️ Gestor" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setAba(t.id)}
            className={`px-5 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors whitespace-nowrap ${
              aba === t.id
                ? "border-blue-600 text-blue-700 bg-blue-50"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── ABA: DASHBOARD ── */}
      {aba === "dashboard" && (
        <div className="space-y-6">
          {loadingDashboard ? (
            <div className="p-8 text-center text-gray-400">
              Carregando dashboard...
            </div>
          ) : !dashboard ? (
            <div className="p-8 text-center text-gray-400">
              Erro ao carregar dashboard.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
                  <p className="text-3xl font-bold text-blue-700">
                    {dashboard.campanhas_ativas?.total ??
                      dashboard.campanhas_ativas}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    📢 Campanhas ativas
                  </p>
                  {dashboard.campanhas_ativas?.nomes?.length > 0 && (
                    <div className="mt-2 text-left space-y-0.5">
                      {dashboard.campanhas_ativas.nomes.map((nome, i) => (
                        <p key={i} className="text-xs text-gray-600 truncate">
                          • {nome}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
                <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
                  <p className="text-3xl font-bold text-green-700">
                    {dashboard.cupons_emitidos_hoje}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    🎟️ Cupons emitidos hoje
                  </p>
                </div>
                <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
                  <p className="text-3xl font-bold text-orange-700">
                    {dashboard.cupons_usados_hoje}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    ✅ Cupons usados hoje
                  </p>
                </div>
                <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
                  <p className="text-2xl font-bold text-purple-700">
                    R$ {formatBRL(dashboard.saldo_passivo_cashback || 0)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    💰 Saldo passivo (cashback)
                  </p>
                </div>
                <div
                  className={`rounded-xl border shadow-sm p-4 text-center ${dashboard.proximos_eventos?.dias_ate_fim_mes <= 3 ? "bg-yellow-50 border-yellow-300" : "bg-white"}`}
                >
                  <p
                    className={`text-3xl font-bold ${dashboard.proximos_eventos?.dias_ate_fim_mes <= 3 ? "text-yellow-700" : "text-indigo-700"}`}
                  >
                    {dashboard.proximos_eventos?.dias_ate_fim_mes ?? "—"}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    🌟{" "}
                    {dashboard.proximos_eventos?.dias_ate_fim_mes === 0
                      ? "Último dia — calcule o destaque!"
                      : "dia(s) p/ Destaque Mensal"}
                  </p>
                </div>
                {(dashboard.cupons_expirados_hoje ?? 0) > 0 && (
                  <div className="bg-red-50 rounded-xl border border-red-200 shadow-sm p-4 text-center">
                    <p className="text-3xl font-bold text-red-700">
                      {dashboard.cupons_expirados_hoje}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      ⏰ Cupons expiram hoje
                    </p>
                  </div>
                )}
              </div>

              <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b bg-pink-50 flex items-center justify-between">
                  <h2 className="font-semibold text-gray-800">
                    🎂 Aniversários de Hoje
                  </h2>
                  <span className="text-sm text-pink-600 font-medium">
                    {dashboard.total_aniversarios} aniversário(s)
                  </span>
                </div>
                {dashboard.aniversarios_hoje.length === 0 ? (
                  <div className="p-6 text-center text-gray-400 text-sm">
                    Nenhum aniversário hoje.
                  </div>
                ) : (
                  <div className="divide-y">
                    {dashboard.aniversarios_hoje.map((a, i) => (
                      <div
                        key={i}
                        className="px-6 py-3 flex items-center gap-3"
                      >
                        <span className="text-xl">
                          {a.tipo === "pet" ? "🐕" : "👤"}
                        </span>
                        <div className="flex-1">
                          <p className="font-medium text-gray-900">{a.nome}</p>
                          <p className="text-xs text-gray-500">
                            {a.tipo === "pet" ? "Pet" : "Cliente"}
                            {a.idade ? ` • ${a.idade} ano(s)` : ""}
                          </p>
                        </div>
                        <span className="text-xs bg-pink-100 text-pink-700 px-2 py-0.5 rounded-full">
                          🎂 Hoje!
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* ── Alertas do dia ── */}
              {dashboard.alertas && (
                <div className="space-y-3">
                  <h2 className="font-semibold text-gray-800">
                    ⚠️ Alertas do Dia
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                      {
                        dias: 30,
                        count: dashboard.alertas.inativos_30d,
                        label: "😴 Clientes sem compra há +30 dias",
                        colors: "bg-orange-50 border-orange-200",
                        textColor: "text-orange-700",
                      },
                      {
                        dias: 60,
                        count: dashboard.alertas.inativos_60d,
                        label: "🚨 Clientes sem compra há +60 dias",
                        colors: "bg-red-50 border-red-200",
                        textColor: "text-red-700",
                      },
                    ].map(({ dias, count, label, colors, textColor }) => (
                      <div
                        key={dias}
                        className={`rounded-xl border p-4 ${count > 0 ? colors : "bg-gray-50 border-gray-200"}`}
                      >
                        <p
                          className={`text-3xl font-bold ${count > 0 ? textColor : "text-gray-400"}`}
                        >
                          {count}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">{label}</p>
                        {count > 0 && (
                          <button
                            onClick={() => {
                              setModalEnvioInativos(dias);
                              setResultadoEnvioInativos(null);
                            }}
                            className="mt-2 text-xs font-medium text-white bg-orange-500 hover:bg-orange-600 px-3 py-1 rounded-lg transition-colors"
                          >
                            ✉️ Enviar e-mail de reativação
                          </button>
                        )}
                      </div>
                    ))}
                    <div
                      className={`rounded-xl border p-4 ${dashboard.alertas.total_sorteios_pendentes > 0 ? "bg-yellow-50 border-yellow-200" : "bg-gray-50 border-gray-200"}`}
                    >
                      <p
                        className={`text-3xl font-bold ${dashboard.alertas.total_sorteios_pendentes > 0 ? "text-yellow-700" : "text-gray-400"}`}
                      >
                        {dashboard.alertas.total_sorteios_pendentes}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        🎲 Sorteio(s) não executado(s)
                      </p>
                    </div>
                  </div>
                  {dashboard.alertas.sorteios_pendentes?.length > 0 && (
                    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                      <div className="px-4 py-3 border-b bg-yellow-50">
                        <p className="text-sm font-medium text-yellow-800">
                          🎲 Sorteios Pendentes
                        </p>
                      </div>
                      <div className="divide-y">
                        {dashboard.alertas.sorteios_pendentes.map((s) => (
                          <div
                            key={s.id}
                            className="px-4 py-3 flex items-center justify-between"
                          >
                            <div>
                              <p className="text-sm font-medium text-gray-900">
                                {s.name}
                              </p>
                              <p className="text-xs text-gray-500">
                                Status: {s.status}
                                {s.draw_date
                                  ? ` • Data: ${new Date(s.draw_date).toLocaleDateString("pt-BR")}`
                                  : ""}
                              </p>
                            </div>
                            <button
                              onClick={() => setAba("sorteios")}
                              className="text-xs text-blue-600 hover:underline"
                            >
                              Ver sorteio →
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Brindes pendentes de retirada */}
                  {dashboard.alertas?.total_brindes_pendentes > 0 && (
                    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                      <div className="px-4 py-3 border-b bg-amber-50 flex items-center justify-between">
                        <p className="text-sm font-medium text-amber-800">
                          🎁 Brindes Pendentes de Retirada (
                          {dashboard.alertas.total_brindes_pendentes})
                        </p>
                        <button
                          onClick={() => setAba("cupons")}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Ver cupons →
                        </button>
                      </div>
                      <div className="divide-y">
                        {dashboard.alertas.brindes_pendentes
                          .slice(0, 5)
                          .map((b, i) => (
                            <div
                              key={i}
                              className="px-4 py-3 flex items-start justify-between gap-3"
                            >
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {b.nome_cliente}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {b.categoria === "maior_gasto"
                                    ? "💰 Maior Gasto"
                                    : b.categoria === "mais_compras"
                                      ? "🛒 Mais Compras"
                                      : b.categoria}
                                  {b.periodo ? ` • ${b.periodo}` : ""}
                                </p>
                                {b.mensagem && (
                                  <p className="text-xs text-amber-700 mt-0.5 truncate">
                                    {b.mensagem}
                                  </p>
                                )}
                              </div>
                              {b.retirar_ate && (
                                <span className="text-xs text-gray-400 shrink-0">
                                  até{" "}
                                  {new Date(b.retirar_ate).toLocaleDateString(
                                    "pt-BR",
                                  )}
                                </span>
                              )}
                            </div>
                          ))}
                        {dashboard.alertas.total_brindes_pendentes > 5 && (
                          <div className="px-4 py-2 text-xs text-gray-400 text-center">
                            +{dashboard.alertas.total_brindes_pendentes - 5}{" "}
                            mais
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Próximos Eventos ── */}
              {dashboard.proximos_eventos && (
                <div className="space-y-3">
                  <h2 className="font-semibold text-gray-800">
                    📅 Próximos Eventos
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Aniversários amanhã */}
                    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                      <div className="px-4 py-3 border-b bg-pink-50 flex items-center justify-between">
                        <p className="text-sm font-semibold text-gray-800">
                          🎂 Aniversários Amanhã
                        </p>
                        <span className="text-xs text-pink-600 font-medium">
                          {dashboard.proximos_eventos.total_aniversarios_amanha}{" "}
                          pessoa(s)
                        </span>
                      </div>
                      {dashboard.proximos_eventos.aniversarios_amanha.length ===
                      0 ? (
                        <div className="px-4 py-4 text-xs text-gray-400 text-center">
                          Nenhum aniversário amanhã.
                        </div>
                      ) : (
                        <div className="divide-y">
                          {dashboard.proximos_eventos.aniversarios_amanha.map(
                            (a, i) => (
                              <div
                                key={i}
                                className="px-4 py-2.5 flex items-center gap-2"
                              >
                                <span>{a.tipo === "pet" ? "🐕" : "👤"}</span>
                                <span className="text-sm text-gray-800">
                                  {a.nome}
                                </span>
                                <span className="ml-auto text-xs text-gray-400">
                                  {a.tipo === "pet" ? "Pet" : "Cliente"}
                                </span>
                              </div>
                            ),
                          )}
                        </div>
                      )}
                    </div>

                    {/* Destaque mensal + sorteios da semana */}
                    <div className="space-y-3">
                      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-4">
                        <span className="text-3xl">🌟</span>
                        <div>
                          <p className="font-semibold text-amber-900">
                            Destaque Mensal
                          </p>
                          <p className="text-sm text-amber-700">
                            {dashboard.proximos_eventos.dias_ate_fim_mes === 0
                              ? "Hoje é o último dia do mês!"
                              : `Faltam ${dashboard.proximos_eventos.dias_ate_fim_mes} dia(s) para o fim do mês`}
                          </p>
                        </div>
                      </div>
                      {dashboard.proximos_eventos.sorteios_esta_semana?.length >
                        0 && (
                        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                          <div className="px-4 py-3 border-b bg-yellow-50">
                            <p className="text-sm font-medium text-gray-800">
                              🎲 Sorteios Esta Semana
                            </p>
                          </div>
                          <div className="divide-y">
                            {dashboard.proximos_eventos.sorteios_esta_semana.map(
                              (s) => (
                                <div
                                  key={s.id}
                                  className="px-4 py-2.5 flex items-center justify-between"
                                >
                                  <span className="text-sm text-gray-800">
                                    {s.name}
                                  </span>
                                  <span className="text-xs text-gray-500">
                                    {s.draw_date
                                      ? new Date(
                                          s.draw_date,
                                        ).toLocaleDateString("pt-BR")
                                      : "—"}
                                  </span>
                                </div>
                              ),
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Modal: Envio para Inativos ── */}
      {modalEnvioInativos && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900">
                  ✉️ Enviar e-mail de reativação
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Clientes sem compra há mais de {modalEnvioInativos} dias · Os
                  e-mails são enfileirados e enviados em lotes
                </p>
              </div>
              <button
                onClick={() => {
                  setModalEnvioInativos(null);
                  setResultadoEnvioInativos(null);
                }}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="p-6 space-y-4">
              {resultadoEnvioInativos ? (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-1">
                  <p className="font-semibold text-green-800">
                    ✅ E-mails enfileirados com sucesso!
                  </p>
                  <p className="text-sm text-green-700">
                    {resultadoEnvioInativos.enfileirados} e-mail(s)
                    adicionado(s) à fila.
                  </p>
                  {resultadoEnvioInativos.sem_email > 0 && (
                    <p className="text-xs text-gray-500">
                      {resultadoEnvioInativos.sem_email} cliente(s) não têm
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
                      placeholder="Ex: Sentimos sua falta! 🐾"
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
                        : "✉️ Enfileirar e-mails"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── ABA: CAMPANHAS ── */}
      {aba === "campanhas" && (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">
              Campanhas Cadastradas
            </h2>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">
                {campanhas.length} campanha(s)
              </span>
              <button
                onClick={() => {
                  setErroCriarCampanha("");
                  setModalCriarCampanha(true);
                }}
                className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
              >
                + Nova Campanha
              </button>
            </div>
          </div>
          {loadingCampanhas ? (
            <div className="p-8 text-center text-gray-400">
              Carregando campanhas...
            </div>
          ) : campanhas.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              <p className="text-2xl mb-2">🎪</p>
              <p>Nenhuma campanha cadastrada ainda.</p>
            </div>
          ) : (
            <div className="divide-y">
              {campanhas.map((c) => {
                const tipo = TIPO_LABELS[c.campaign_type] || {
                  label: c.campaign_type,
                  color: "bg-gray-100 text-gray-700",
                  emoji: "📋",
                };
                const ativa = c.status === "active";
                const editando = campanhaEditando === c.id;
                return (
                  <div key={c.id} className="px-6 py-4">
                    <div className="flex items-center gap-4">
                      <div className="text-2xl">{tipo.emoji}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-gray-900">
                            {c.name}
                          </span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${tipo.color}`}
                          >
                            {tipo.label}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 mt-0.5 truncate">
                          {formatarParams(c.campaign_type, c.params)}
                        </p>
                      </div>
                      <button
                        onClick={() =>
                          editando ? fecharEdicao() : abrirEdicao(c)
                        }
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                      >
                        {editando ? "Cancelar" : "⚙️ Configurar"}
                      </button>
                      {USER_CREATABLE_TYPES.has(c.campaign_type) && (
                        <button
                          onClick={() => arquivarCampanha(c)}
                          disabled={arquivando === c.id}
                          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors disabled:opacity-50"
                          title="Arquivar campanha"
                        >
                          {arquivando === c.id ? "..." : "🗑️"}
                        </button>
                      )}
                      <button
                        onClick={() => toggleCampanha(c)}
                        disabled={toggling === c.id}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors min-w-[100px] disabled:opacity-50 ${
                          ativa
                            ? "bg-green-100 text-green-700 hover:bg-green-200"
                            : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                        }`}
                      >
                        {toggling === c.id
                          ? "..."
                          : ativa
                            ? "✅ Ativa"
                            : "⏸️ Pausada"}
                      </button>
                    </div>
                    {editando && (
                      <div className="mt-4 bg-blue-50 rounded-xl p-4 border border-blue-200">
                        <p className="text-xs font-semibold text-blue-700 mb-3">
                          ⚙️ Parâmetros —{" "}
                          {TIPO_LABELS[c.campaign_type]?.label ||
                            c.campaign_type}
                        </p>
                        {renderFormCampaign(c)}
                        <button
                          onClick={() => salvarParametros(c)}
                          disabled={salvandoParams}
                          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {salvandoParams
                            ? "Salvando..."
                            : "💾 Salvar Parâmetros"}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── ABA: RETENÇÃO DINÂMICA ── */}
      {aba === "retencao" && (
        <div className="space-y-4">
          <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 flex items-start gap-3">
            <span className="text-2xl">🔄</span>
            <div>
              <p className="font-semibold text-orange-800">Retenção Dinâmica</p>
              <p className="text-sm text-orange-700 mt-0.5">
                Cada regra detecta clientes que não compraram há X dias e envia
                automaticamente um cupom de incentivo. Você pode ter múltiplas
                réguas: 30 dias, 60 dias, 90 dias — cada uma com desconto e
                mensagem diferentes.
              </p>
            </div>
          </div>

          {/* Formulário de criação / edição */}
          {retencaoEditando !== null && (
            <RetencaoForm
              inicial={retencaoEditando}
              salvando={salvandoRetencao}
              onSalvar={salvarRetencao}
              onCancelar={() => setRetencaoEditando(null)}
            />
          )}

          {/* Botão nova regra */}
          {retencaoEditando === null && (
            <button
              onClick={() =>
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
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm font-medium"
            >
              <span>➕</span> Nova Regra de Retenção
            </button>
          )}

          {/* Lista de regras */}
          {loadingRetencao ? (
            <p className="text-gray-500 text-sm">Carregando...</p>
          ) : retencaoRegras.length === 0 ? (
            <div className="bg-white border rounded-xl p-8 text-center text-gray-500">
              <p className="text-3xl mb-2">😴</p>
              <p className="font-medium">
                Nenhuma regra de retenção cadastrada ainda.
              </p>
              <p className="text-sm mt-1">
                Crie sua primeira regra para começar a recuperar clientes
                inativos.
              </p>
            </div>
          ) : (
            <div className="grid gap-3">
              {retencaoRegras.map((r) => (
                <div
                  key={r.id}
                  className="bg-white border border-orange-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center gap-3"
                >
                  <div className="flex-1">
                    <p className="font-semibold text-gray-800">
                      {r.name || "(sem nome)"}
                    </p>
                    <div className="flex flex-wrap gap-3 mt-1 text-sm text-gray-600">
                      <span>
                        ⏱️{" "}
                        <strong>{r.params?.inactivity_days ?? "?"} dias</strong>{" "}
                        sem compra
                      </span>
                      <span>
                        🎟️ Cupom:{" "}
                        <strong>
                          {r.params?.coupon_type === "percent"
                            ? `${r.params.coupon_value}%`
                            : `R$ ${r.params?.coupon_value}`}
                        </strong>
                      </span>
                      <span>
                        📅 Validade:{" "}
                        <strong>
                          {r.params?.coupon_valid_days ?? "?"} dias
                        </strong>
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${r.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                      >
                        {r.status === "active" ? "✅ Ativa" : "⏸️ Pausada"}
                      </span>
                    </div>
                    {r.params?.notification_message && (
                      <p className="text-xs text-gray-400 mt-1 italic">
                        "{r.params.notification_message}"
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      onClick={() =>
                        setRetencaoEditando({
                          id: r.id,
                          name: r.name,
                          priority: r.priority,
                          ...r.params,
                        })
                      }
                      className="px-3 py-1.5 text-sm border border-orange-300 text-orange-700 rounded-lg hover:bg-orange-50"
                    >
                      ✏️ Editar
                    </button>
                    <button
                      onClick={() => deletarRetencao(r.id)}
                      disabled={deletandoRetencao === r.id}
                      className="px-3 py-1.5 text-sm border border-red-200 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                    >
                      {deletandoRetencao === r.id ? "..." : "🗑️"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── ABA: DESTAQUE MENSAL ── */}
      {aba === "destaque" && (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
            <span className="text-2xl">🌟</span>
            <div>
              <p className="font-semibold text-amber-800">Destaque Mensal</p>
              <p className="text-sm text-amber-700 mt-0.5">
                O sistema identifica os clientes que mais gastaram e mais
                compraram no mês anterior. Você pode premiar cada vencedor com
                um cupom de recompensa.
              </p>
            </div>
          </div>

          {loadingDestaque ? (
            <div className="p-8 text-center text-gray-400">
              Carregando destaque...
            </div>
          ) : !destaque ? (
            <div className="p-8 text-center">
              <button
                onClick={carregarDestaque}
                className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600"
              >
                Calcular Vencedores
              </button>
            </div>
          ) : (
            <>
              <div className="bg-white rounded-xl border shadow-sm p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      Vencedores — {destaque.periodo}
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {destaque.total_clientes_ativos} clientes ativos no
                      período
                    </p>
                  </div>
                  <button
                    onClick={carregarDestaque}
                    className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200"
                  >
                    🔄 Recalcular
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
                  {Object.entries(destaque.vencedores).map(([cat, info]) => {
                    const premio = premiosPorVencedor[cat] || _defaultPremio();
                    const setPremio = (upd) =>
                      setPremiosPorVencedor((p) => ({
                        ...p,
                        [cat]: { ...(p[cat] || _defaultPremio()), ...upd },
                      }));
                    const selecionado = vencedoresSelecionados[cat] !== false;
                    return (
                      <div
                        key={cat}
                        className={`bg-gradient-to-br from-amber-50 to-yellow-50 border rounded-xl p-4 space-y-3 transition-opacity ${selecionado ? "border-amber-200 opacity-100" : "border-gray-200 opacity-50"}`}
                      >
                        {/* Cabeçalho: checkbox + título + toggle de tipo de prêmio */}
                        <div className="flex items-center justify-between">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={selecionado}
                              onChange={(e) =>
                                setVencedoresSelecionados((s) => ({
                                  ...s,
                                  [cat]: e.target.checked,
                                }))
                              }
                              className="w-4 h-4 accent-amber-500"
                            />
                            <p className="text-xs font-semibold text-amber-600 uppercase">
                              {cat === "maior_gasto"
                                ? "💰 Maior Gasto"
                                : "🛒 Mais Compras"}
                            </p>
                          </label>
                          <div className="flex gap-1">
                            <button
                              onClick={() =>
                                setPremio({ tipo_premio: "cupom" })
                              }
                              className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${premio.tipo_premio !== "mensagem" ? "bg-amber-500 text-white border-amber-500" : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"}`}
                            >
                              🎟️ Cupom
                            </button>
                            <button
                              onClick={() =>
                                setPremio({ tipo_premio: "mensagem" })
                              }
                              className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${premio.tipo_premio === "mensagem" ? "bg-amber-500 text-white border-amber-500" : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"}`}
                            >
                              🎁 Brinde
                            </button>
                          </div>
                        </div>

                        {/* Info do vencedor */}
                        <div>
                          <p className="font-bold text-gray-900">{info.nome}</p>
                          <p className="text-sm text-gray-600">
                            {cat === "maior_gasto"
                              ? `R$ ${formatBRL(info.total_spent)} gastos`
                              : `${info.total_purchases} compra(s)`}
                          </p>
                        </div>

                        {/* Campos para cupom */}
                        {premio.tipo_premio !== "mensagem" ? (
                          <div className="space-y-2">
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <label className="text-xs text-gray-500 block mb-1">
                                  Valor do cupom (R$)
                                </label>
                                <input
                                  type="number"
                                  min="1"
                                  step="0.01"
                                  value={premio.coupon_value ?? 50}
                                  onChange={(e) =>
                                    setPremio({
                                      coupon_value:
                                        Number.parseFloat(e.target.value) || 0,
                                    })
                                  }
                                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500 block mb-1">
                                  Validade (dias)
                                </label>
                                <input
                                  type="number"
                                  min="1"
                                  value={premio.coupon_valid_days ?? 10}
                                  onChange={(e) =>
                                    setPremio({
                                      coupon_valid_days:
                                        Number.parseInt(e.target.value, 10) ||
                                        1,
                                    })
                                  }
                                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                                />
                              </div>
                            </div>
                            <div>
                              <label className="text-xs text-gray-500 block mb-1">
                                Mensagem ao cliente
                              </label>
                              <input
                                type="text"
                                value={premio.mensagem ?? ""}
                                onChange={(e) =>
                                  setPremio({ mensagem: e.target.value })
                                }
                                placeholder="Ex: Parabéns! Use este cupom em sua próxima visita 🏆"
                                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                              />
                            </div>
                          </div>
                        ) : (
                          /* Campos para brinde */
                          <div className="space-y-2">
                            <div>
                              <label className="text-xs text-gray-500 block mb-1">
                                Mensagem ao cliente
                              </label>
                              <textarea
                                rows={3}
                                value={premio.mensagem_brinde ?? ""}
                                onChange={(e) =>
                                  setPremio({ mensagem_brinde: e.target.value })
                                }
                                className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300 resize-none"
                              />
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <label className="text-xs text-gray-500 block mb-1">
                                  Retirada a partir de
                                </label>
                                <input
                                  type="date"
                                  value={premio.retirar_de ?? ""}
                                  onChange={(e) =>
                                    setPremio({ retirar_de: e.target.value })
                                  }
                                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500 block mb-1">
                                  Retirada até
                                </label>
                                <input
                                  type="date"
                                  value={premio.retirar_ate ?? ""}
                                  onChange={(e) =>
                                    setPremio({ retirar_ate: e.target.value })
                                  }
                                  className="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-amber-300"
                                />
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                  {Object.keys(destaque.vencedores).length === 0 && (
                    <div className="col-span-2 p-6 text-center text-gray-400">
                      Nenhum vencedor identificado para o período.
                    </div>
                  )}
                </div>

                {/* Aviso de desempate — exibe quando o 2º colocado substituiu o 1º */}
                {(destaque.desempate_info || []).length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-4 space-y-2">
                    <p className="font-semibold text-yellow-800 text-sm flex items-center gap-2">
                      ⚖️ Desempate aplicado
                    </p>
                    {destaque.desempate_info.map((d, i) => (
                      <div
                        key={i}
                        className="text-sm text-yellow-700 leading-relaxed"
                      >
                        <span className="font-medium">
                          {d.categoria === "maior_gasto"
                            ? "💰 Maior Gasto"
                            : "🛒 Mais Compras"}
                          :
                        </span>{" "}
                        <span className="line-through text-yellow-500">
                          {d.pulado?.nome}
                        </span>{" "}
                        (1º lugar) já ganhou em outra categoria — o{" "}
                        <span className="font-medium">
                          {d.posicao_eleito}º colocado
                        </span>{" "}
                        <span className="font-semibold text-yellow-800">
                          {d.eleito?.nome}
                        </span>{" "}
                        foi selecionado no lugar.
                      </div>
                    ))}
                  </div>
                )}

                {destaqueResultado ? (
                  <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-semibold text-green-800">
                        ✅ Prêmios enviados! ({destaqueResultado.enviados}{" "}
                        vencedor(es))
                      </p>
                      <button
                        onClick={() => setDestaqueResultado(null)}
                        className="text-xs text-gray-400 hover:text-gray-600 underline"
                      >
                        Enviar novamente
                      </button>
                    </div>
                    <ul className="space-y-1.5">
                      {(destaqueResultado.resultados || []).map((r, i) => (
                        <li
                          key={i}
                          className="flex items-center gap-2 text-sm text-gray-700"
                        >
                          <span>
                            {r.categoria === "maior_gasto"
                              ? "💰 Maior Gasto"
                              : "🛒 Mais Compras"}
                            :
                          </span>
                          {r.tipo_premio === "cupom" ? (
                            <>
                              <span className="font-mono font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded">
                                {r.coupon_code}
                              </span>
                              {r.ja_existia && (
                                <span className="text-xs text-gray-400">
                                  (já existia)
                                </span>
                              )}
                            </>
                          ) : (
                            <span className="text-amber-700">
                              🎁 Brinde registrado
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  Object.keys(destaque.vencedores).length > 0 && (
                    <button
                      onClick={enviarDestaque}
                      disabled={
                        enviandoDestaque ||
                        Object.values(vencedoresSelecionados).every((v) => !v)
                      }
                      className="w-full py-3 bg-amber-500 text-white rounded-xl font-semibold hover:bg-amber-600 disabled:opacity-50 transition-colors"
                    >
                      {enviandoDestaque
                        ? "Enviando prêmios..."
                        : "🏆 Enviar Prêmios aos Vencedores"}
                    </button>
                  )
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  ["maior_gasto", "top5_maior_gasto", "💰 Top 5 — Maior Gasto"],
                  [
                    "mais_compras",
                    "top5_mais_compras",
                    "🛒 Top 5 — Mais Compras",
                  ],
                ].map(([cat, key, title]) => (
                  <div
                    key={cat}
                    className="bg-white rounded-xl border shadow-sm overflow-hidden"
                  >
                    <div className="px-4 py-3 border-b bg-gray-50">
                      <p className="font-semibold text-gray-800 text-sm">
                        {title}
                      </p>
                    </div>
                    <ul className="divide-y">
                      {(destaque[key] || []).map((cl, i) => (
                        <li
                          key={i}
                          className="px-4 py-3 flex items-center gap-3"
                        >
                          <span className="text-lg font-bold text-gray-300 w-6 text-center">
                            {i + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900 truncate">
                              {cl.nome}
                            </p>
                            <p className="text-xs text-gray-500">
                              {cat === "maior_gasto"
                                ? `R$ ${formatBRL(cl.total_spent)}`
                                : `${cl.total_purchases} compra(s)`}
                            </p>
                          </div>
                          {destaque.vencedores[cat]?.customer_id ===
                            cl.customer_id && (
                            <span className="text-yellow-500 text-lg">🏆</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── ABA: SORTEIOS ── */}
      {aba === "sorteios" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                🎲 Sorteios
              </h2>
              <p className="text-sm text-gray-500">
                Crie sorteios exclusivos por nível de ranking. O resultado é
                auditável via seed UUID.
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
                🎉 Sorteio executado!
              </p>
              <p className="text-purple-700">
                Ganhador: <strong>{sorteioResultado.winner_name}</strong>
              </p>
              <p className="text-sm text-purple-600 mt-1">
                {sorteioResultado.total_participantes} participante(s) · Seed:{" "}
                <span className="font-mono text-xs">
                  {sorteioResultado.seed_uuid?.slice(0, 16)}…
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
              <p className="text-3xl mb-2">🎲</p>
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
                  draft: "📝 Rascunho",
                  open: "✅ Inscrito",
                  drawn: "🏆 Realizado",
                  cancelled: "❌ Cancelado",
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
                            🎁 {s.prize_description}
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
                            ` · Sorteio: ${new Date(s.draw_date).toLocaleDateString("pt-BR")}`}
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
                              : "📋 Inscrever Elegíveis"}
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
                              : "🎲 Executar Sorteio"}
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
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── ABA: RANKING ── */}
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
                    "✅ Recálculo de ranking enfileirado! O worker processará em até 10 segundos.",
                  );
                  setTimeout(() => carregarRanking(), 3000);
                } catch (e) {
                  alert("Erro: " + (e?.response?.data?.detail || e.message));
                }
              }}
              className="ml-auto px-4 py-2 bg-gray-700 text-white rounded-full text-sm font-medium hover:bg-gray-800 transition-colors"
            >
              🔄 Recalcular Agora
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
                    Período: {ranking.periodo}
                  </p>
                </div>
                {ranking.clientes.length === 0 ? (
                  <div className="p-8 text-center text-gray-400">
                    Nenhum cliente neste nível.
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
                            Nível
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

          {/* Botão Envio em Lote */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-blue-800">📧 Envio em Lote</p>
              <p className="text-sm text-blue-600">
                Envie um e-mail personalizado para todos os clientes de um
                nível.
              </p>
            </div>
            <button
              onClick={() => {
                setResultadoLote(null);
                setModalLote(true);
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Enviar para Nível
            </button>
          </div>

          {/* Config de critérios de ranking */}
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
                ⚙️ Configurar Critérios de Ranking
              </span>
              <span className="text-gray-400 text-sm">
                {rankingConfig?._aberto ? "▲ Fechar" : "▼ Expandir"}
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
                    Não foi possível carregar.
                  </div>
                ) : (
                  <>
                    <p className="text-xs text-gray-500">
                      O cliente precisa atingir <strong>todos</strong> os
                      critérios de um nível para alcançá-lo (gasto, compras e
                      meses ativos nos últimos 12 meses). Quem não atingir o
                      mínimo de Prata fica como Bronze.
                    </p>
                    {[
                      { key: "silver", label: "🥈 Prata" },
                      { key: "gold", label: "🥇 Ouro" },
                      { key: "diamond", label: "👑 Platina" },
                      { key: "platinum", label: "💸 Diamante" },
                    ].map(({ key, label }) => (
                      <div
                        key={key}
                        className="border rounded-xl p-4 space-y-2"
                      >
                        <p className="font-medium text-gray-700">{label}</p>
                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">
                              Gasto mínimo (R$)
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
                              Compras mínimas
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
                              Meses ativos mínimos
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
                          : "Salvar Critérios"}
                      </button>
                    </div>
                  </>
                )}
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
                Busca (código ou cliente)
              </label>
              <input
                type="text"
                value={filtroCupomBusca}
                onChange={(e) => setFiltroCupomBusca(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && carregarCupons()}
                placeholder="Ex: ANIV ou João Silva"
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
                Criado até
              </label>
              <input
                type="date"
                value={filtroCupomDataFim}
                onChange={(e) => setFiltroCupomDataFim(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={carregarCupons}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              🔍 Filtrar
            </button>
            {(filtroCupomBusca ||
              filtroCupomDataInicio ||
              filtroCupomDataFim) && (
              <button
                onClick={() => {
                  setFiltroCupomBusca("");
                  setFiltroCupomDataInicio("");
                  setFiltroCupomDataFim("");
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
                <p className="text-2xl mb-2">🎟️</p>
                <p>Nenhum cupom encontrado.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        Código
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
                        Ação
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
                        <>
                          <tr
                            key={c.id}
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
                                    ? "🎁 Brinde"
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
                                <span className="text-gray-300">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-gray-500 text-xs">
                              {c.created_at
                                ? new Date(c.created_at).toLocaleDateString(
                                    "pt-BR",
                                  )
                                : "—"}
                            </td>
                            <td className="px-4 py-3 text-gray-500">
                              {c.valid_until
                                ? new Date(c.valid_until).toLocaleDateString(
                                    "pt-BR",
                                  )
                                : "—"}
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
                                    : "🚫 Anular"}
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
                                      Código
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
                                        : "—"}
                                    </p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-gray-500 font-medium mb-0.5">
                                      Válido até
                                    </p>
                                    <p className="text-gray-700">
                                      {c.valid_until
                                        ? new Date(
                                            c.valid_until,
                                          ).toLocaleDateString("pt-BR")
                                        : "Sem validade"}
                                    </p>
                                  </div>
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
                                        Retirada até
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
                                          ? "💰 Maior Gasto"
                                          : c.meta.categoria === "mais_compras"
                                            ? "🛒 Mais Compras"
                                            : c.meta.categoria}
                                      </p>
                                    </div>
                                  )}
                                  {c.meta?.periodo && (
                                    <div>
                                      <p className="text-xs text-gray-500 font-medium mb-0.5">
                                        Período
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
                        </>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── ABA: RELATÓRIOS ── */}
      {aba === "relatorios" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border shadow-sm p-4 flex flex-wrap gap-4 items-end">
            <div>
              <label
                htmlFor="rel-data-inicio"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Data início
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
                <option value="credito">Só créditos</option>
                <option value="resgate">Só resgates</option>
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
                Histórico de Movimentações
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Créditos = cashback gerado ao cliente. Resgates = cashback usado
                como pagamento numa venda.
              </p>
            </div>
            {loadingRelatorio ? (
              <div className="p-8 text-center text-gray-400">
                Carregando relatório...
              </div>
            ) : !relatorio || relatorio.transacoes.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <p className="text-2xl mb-2">📭</p>
                <p>Nenhuma movimentação no período.</p>
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
                        Descrição
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
                            {t.tipo === "credito" ? "⬆️ Crédito" : "⬇️ Resgate"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-500">
                          {t.venda_id || "—"}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold">
                          R$ {formatBRL(t.valor)}
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs max-w-[200px] truncate">
                          {t.descricao || "—"}
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

      {/* ── ABA: UNIFICAÇÃO CROSS-CANAL ── */}
      {aba === "unificacao" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="font-semibold text-gray-800">
                  🔗 Unificação Cross-Canal por CPF/Telefone
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Clientes que parecem ser a mesma pessoa (mesmo CPF ou mesmo
                  telefone) aparecem aqui para unificação manual.
                </p>
              </div>
              <button
                onClick={carregarSugestoes}
                disabled={loadingSugestoes}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {loadingSugestoes ? "Buscando..." : "🔍 Buscar Duplicatas"}
              </button>
            </div>

            {resultadoMerge && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 text-sm flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-green-800">
                    ✅ Clientes unificados! (Merge #{resultadoMerge.merge_id})
                  </p>
                  <p className="text-green-600">
                    Transferidos: {resultadoMerge.transferencias?.cashback ?? 0}{" "}
                    cashbacks, {resultadoMerge.transferencias?.carimbos ?? 0}{" "}
                    carimbos, {resultadoMerge.transferencias?.cupons ?? 0}{" "}
                    cupons, {resultadoMerge.transferencias?.ranking ?? 0}{" "}
                    posições de ranking.
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
                <p className="text-3xl mb-2">✅</p>
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
                        Ação
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
                              ? "🪪 Mesmo CPF"
                              : "📞 Mesmo Telefone"}
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
                              Unir A ← B
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
                              Unir B ← A
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

      {/* ── MODAL: CRIAR SORTEIO ── */}
      {modalSorteio && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">🎲 Novo Sorteio</h3>
              <button
                onClick={() => setModalSorteio(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ×
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
                  placeholder="Ex: Sorteio de Março"
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
                  Prêmio
                </label>
                <input
                  id="s-premio"
                  type="text"
                  placeholder="Ex: Kit banho + tosa grátis"
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
                  Nível mínimo elegantível (opcional)
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
                  <option value="bronze">🥉 Bronze+</option>
                  <option value="silver">🥈 Prata+</option>
                  <option value="gold">🥇 Ouro+</option>
                  <option value="platinum">💎 Diamante+</option>
                  <option value="diamond">👑 Platina</option>
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
                  Descrição (opcional)
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

      {/* ── MODAL: LANÇAR CARIMBO MANUAL ── */}
      {fidModalManual && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                🏷️ Lançar Carimbo Manual
              </h3>
              <button
                onClick={() => setFidModalManual(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ×
              </button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <p className="text-sm text-gray-500">
                Cliente <strong>#{fidClienteId}</strong> — Esse carimbo será
                registrado como manual (sem vínculo com uma venda).
              </p>
              <div>
                <label
                  htmlFor="fid-nota"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Observação (opcional)
                </label>
                <input
                  id="fid-nota"
                  type="text"
                  value={fidManualNota}
                  onChange={(e) => setFidManualNota(e.target.value)}
                  placeholder="Ex: Conversão de cartão físico"
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
                {fidLancandoManual ? "Lançando..." : "Confirmar Carimbo"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: ENVIO EM LOTE ── */}
      {modalLote && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">📧 Envio em Lote</h3>
              <button
                onClick={() => setModalLote(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ×
              </button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <div>
                <label
                  htmlFor="lote-nivel"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  Nível de ranking
                </label>
                <select
                  id="lote-nivel"
                  value={loteForm.nivel}
                  onChange={(e) =>
                    setLoteForm((p) => ({ ...p, nivel: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="todos">Todos os níveis</option>
                  <option value="platinum">💎 Diamante</option>
                  <option value="diamond">👑 Platina</option>
                  <option value="gold">🥇 Ouro</option>
                  <option value="silver">🥈 Prata</option>
                  <option value="bronze">🥉 Bronze</option>
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
                  placeholder="Ex: Promoção exclusiva para clientes Ouro!"
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
                  placeholder="Escreva a mensagem que será enviada para os clientes..."
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
                    ✅ {resultadoLote.enfileirados} e-mail(s) enfileirado(s)!
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

      {/* ── MODAL: NOVA CAMPANHA ── */}
      {modalCriarCampanha && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">➕ Nova Campanha</h3>
              <button
                onClick={() => setModalCriarCampanha(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ×
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
                  placeholder="Ex: Recompra Rápida Verão"
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
                  <option value="inactivity">😴 Clientes Inativos</option>
                  <option value="quick_repurchase">🔁 Recompra Rápida</option>
                </select>
              </div>
              <p className="text-xs text-gray-500">
                Os parâmetros poderão ser configurados depois de criar a
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

      {/* ── MODAL: CRIAR CUPOM MANUAL ── */}
      {modalCupomAberto && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                🎟️ Criar Cupom Manual
              </h3>
              <button
                onClick={() => {
                  setModalCupomAberto(false);
                  setErroCupom("");
                }}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ×
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
                  Válido até (opcional)
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
                  Compra mínima (R$, opcional)
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
                  placeholder="Deixe vazio para cupom genérico"
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
                  Descrição (opcional)
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
                  🛠️ Gestor de Benefícios
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {gestorModo === "cliente"
                    ? "Busque um cliente para gerenciar seus benefícios."
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
                  🔍 Por Cliente
                </button>
                <button
                  onClick={() => setGestorModo("campanha")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    gestorModo === "campanha"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  🏷️ Por Campanha
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
                          {c.cpf && c.telefone ? " · " : ""}
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
                  <option value="carimbos">🏷️ Cartão Fidelidade</option>
                  <option value="cashback">💰 Cashback (saldo positivo)</option>
                  <option value="cupons">🎟️ Cupons Ativos</option>
                  <option value="ranking">🏆 Ranking (mês atual)</option>
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
                    Clique em “Ver detalhes” para gerenciar
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
                            {c.cpf && c.telefone ? " · " : ""}
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
                          Ver detalhes →
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
                      ID #{gestorCliente.id} ·{" "}
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

                {/* ── Seção: Carimbos ── */}
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
                      <span className="text-xl">🏷️</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">
                          Cartão Fidelidade
                        </p>
                        <p className="text-xs text-gray-500">
                          {gestorSaldo.total_carimbos} carimbo(s) ativo(s)
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "carimbos" ? "▲" : "▼"}
                    </span>
                  </button>
                  {gestorSecao === "carimbos" && (
                    <div className="border-t p-6 space-y-4">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <p className="text-sm font-medium text-green-800 mb-3">
                          ➕ Lançar Carimbo Manual
                        </p>
                        <div className="flex gap-3 flex-wrap items-end">
                          <div className="flex-1 min-w-[200px]">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              Observação (opcional)
                            </label>
                            <input
                              type="text"
                              value={gestorCarimboNota}
                              onChange={(e) =>
                                setGestorCarimboNota(e.target.value)
                              }
                              placeholder="Ex: Conversão de cartão físico"
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            />
                          </div>
                          <button
                            onClick={lancarCarimboGestor}
                            disabled={gestorLancandoCarimbo}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                          >
                            {gestorLancandoCarimbo
                              ? "Lançando..."
                              : "✅ Lançar Carimbo"}
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
                                  Ação
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
                                          Automático
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-4 py-2 text-gray-500 text-xs max-w-[180px] truncate">
                                      {s.notes || "—"}
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
                                            : "❌ Remover"}
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

                {/* ── Seção: Cashback ── */}
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
                      <span className="text-xl">💰</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Cashback</p>
                        <p className="text-xs text-gray-500">
                          Saldo: R$ {formatBRL(gestorSaldo.saldo_cashback)}
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "cashback" ? "▲" : "▼"}
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
                          ✏️ Ajuste Manual
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
                                ➕ Crédito (adicionar)
                              </option>
                              <option value="debito">
                                ➖ Débito (remover)
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
                              placeholder="Ex: Correção de campanha"
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
                              ? "➖ Confirmar Débito"
                              : "➕ Confirmar Crédito"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* ── Seção: Cupons ── */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(gestorSecao === "cupons" ? null : "cupons")
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">🎟️</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Cupons</p>
                        <p className="text-xs text-gray-500">
                          {gestorCupons?.filter((c) => c.status === "active")
                            .length || 0}{" "}
                          ativo(s) · {gestorCupons?.length || 0} no total
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "cupons" ? "▲" : "▼"}
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
                                  Código
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
                                  Ação
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
                                      ? "🎁 Brinde"
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
                                          : "🚫 Anular"}
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

                {/* ── Seção: Ranking ── */}
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
                      <span className="text-xl">🏆</span>
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
                            ? ` · ${gestorSaldo.rank_period}`
                            : ""}
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "ranking" ? "▲" : "▼"}
                    </span>
                  </button>
                  {gestorSecao === "ranking" && (
                    <div className="border-t p-6">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                          {
                            label: "Nível",
                            value: (() => {
                              const r =
                                RANK_LABELS[gestorSaldo.rank_level] ||
                                RANK_LABELS.bronze;
                              return `${r.emoji} ${r.label}`;
                            })(),
                          },
                          {
                            label: "Período",
                            value: gestorSaldo.rank_period || "—",
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
                        O nível de ranking é recalculado automaticamente no dia
                        1 de cada mês.
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}
        </div>
      )}
    </div>
  );
}
