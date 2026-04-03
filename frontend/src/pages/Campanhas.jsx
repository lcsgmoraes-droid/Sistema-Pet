import { Fragment, useCallback, useState } from "react";
import api from "../api";
import CanalDescontos from "./CanalDescontos";
import { formatBRL } from "../utils/formatters";
import { useCampanhasConsultas } from "../hooks/useCampanhasConsultas";
import CampanhasTabsBar from "../components/campanhas/CampanhasTabsBar";
import CampanhasDashboardTab from "../components/campanhas/CampanhasDashboardTab";
import CampanhasListTab from "../components/campanhas/CampanhasListTab";

const TIPO_LABELS = {
  loyalty_stamp: {
    label: "CartÃ£o Fidelidade",
    color: "bg-purple-100 text-purple-800",
    emoji: "ðŸ·ï¸",
  },
  cashback: {
    label: "Cashback",
    color: "bg-green-100 text-green-800",
    emoji: "ðŸ’°",
  },
  birthday: {
    label: "AniversÃ¡rio",
    color: "bg-pink-100 text-pink-800",
    emoji: "ðŸŽ‚",
  },
  birthday_customer: {
    label: "AniversÃ¡rio Cliente",
    color: "bg-pink-100 text-pink-800",
    emoji: "ðŸŽ‚",
  },
  birthday_pet: {
    label: "AniversÃ¡rio Pet",
    color: "bg-orange-100 text-orange-800",
    emoji: "ðŸ¾",
  },
  welcome: {
    label: "Boas-vindas",
    color: "bg-blue-100 text-blue-800",
    emoji: "ðŸ‘‹",
  },
  welcome_app: {
    label: "Boas-vindas App",
    color: "bg-blue-100 text-blue-800",
    emoji: "ðŸ‘‹",
  },
  inactivity: {
    label: "Clientes Inativos",
    color: "bg-red-100 text-red-800",
    emoji: "ðŸ˜´",
  },
  ranking_monthly: {
    label: "Ranking Mensal",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "ðŸ†",
  },
  quick_repurchase: {
    label: "Recompra RÃ¡pida",
    color: "bg-teal-100 text-teal-800",
    emoji: "ðŸ”",
  },
  monthly_highlight: {
    label: "Destaque Mensal",
    color: "bg-amber-100 text-amber-800",
    emoji: "ðŸŒŸ",
  },
  win_back: {
    label: "ReativaÃ§Ã£o",
    color: "bg-red-100 text-red-800",
    emoji: "ðŸ”„",
  },
  raffle: {
    label: "Sorteio",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "ðŸŽ²",
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
    emoji: "ðŸ¥‰",
  },
  silver: {
    label: "Prata",
    color: "bg-gray-100 text-gray-700",
    border: "border-gray-400",
    emoji: "ðŸ¥ˆ",
  },
  gold: {
    label: "Ouro",
    color: "bg-yellow-100 text-yellow-800",
    border: "border-yellow-400",
    emoji: "ðŸ¥‡",
  },
  diamond: {
    label: "Platina",
    color: "bg-purple-100 text-purple-800",
    border: "border-purple-400",
    emoji: "ðŸ‘‘",
  },
  platinum: {
    label: "Diamante",
    color: "bg-cyan-100 text-cyan-800",
    border: "border-cyan-400",
    emoji: "ðŸ’Ž",
  },
};

// Frases sugeridas para campanhas de aniversÃ¡rio (por tipo de campanha e tipo de presente)
const FRASES_ANIVERSARIO = {
  birthday_customer: {
    brinde:
      "ðŸŽ‚ Feliz aniversÃ¡rio, {nome}! Seu carinho merece uma celebraÃ§Ã£o especial! ApareÃ§a na nossa loja para retirar seu presente surpresa. SerÃ¡ um prazer ver vocÃª! ðŸŽ",
    cupom:
      "ðŸŽ‰ Feliz aniversÃ¡rio, {nome}! Neste dia tÃ£o especial preparamos um cupom de {desconto} de desconto pra vocÃª celebrar com muito mimo pro seu pet! Use o cÃ³digo {code}. ðŸ¾",
  },
  birthday_pet: {
    brinde:
      "ðŸ¾ðŸŽ‚ Que dia mais fofo! {nome_pet} estÃ¡ fazendo aniversÃ¡rio e a gente nÃ£o podia deixar passar em branco! Venha buscar o mimo especial que separamos pro seu melhor amigo â€” tem muito carinho esperando por vocÃªs! Um beijo nas patinhas! ðŸ¥³",
    cupom:
      "ðŸŽˆ O {nome_pet} tÃ¡ de parabÃ©ns hoje, {nome}! Para comemorar esse dia tÃ£o especial, preparamos um cupom de {desconto} de desconto pra mimar o(a) aniversariante! Use o cÃ³digo {code} e vai fundo nos mimos! ðŸ•ðŸŽ",
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
        {isNew ? "âž• Nova Regra" : "âœï¸ Editar Regra"}
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
            placeholder="Ex: RetenÃ§Ã£o 30 dias"
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
            Mensagem de notificaÃ§Ã£o
          </label>
          <input
            id="ret-msg"
            type="text"
            value={form.notification_message}
            onChange={(e) => set("notification_message", e.target.value)}
            placeholder="OlÃ¡, {nome}! Sentimos sua falta. Cupom: {code}"
            className="w-full border rounded-lg px-3 py-1.5 text-sm"
          />
          <p className="text-xs text-gray-400 mt-0.5">
            VariÃ¡veis: {"{nome}"}, {"{code}"}, {"{value}"}
          </p>
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onSalvar(form)}
          disabled={salvando || !form.name.trim()}
          className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm font-medium disabled:opacity-50"
        >
          {salvando ? "Salvando..." : "ðŸ’¾ Salvar"}
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

  // Campanhas
  const [toggling, setToggling] = useState(null);
  const [campanhaEditando, setCampanhaEditando] = useState(null);
  const [paramsEditando, setParamsEditando] = useState({});
  const [salvandoParams, setSalvandoParams] = useState(false);

  // Envio escalonado de inativos
  const [modalEnvioInativos, setModalEnvioInativos] = useState(null); // null | 30 | 60 | 90
  const [envioInativosForm, setEnvioInativosForm] = useState({
    assunto: "Sentimos sua falta! ðŸ¾",
    mensagem: "",
  });
  const [enviandoInativos, setEnviandoInativos] = useState(false);
  const [resultadoEnvioInativos, setResultadoEnvioInativos] = useState(null);

  // RetenÃ§Ã£o DinÃ¢mica
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
    mensagem: "ParabÃ©ns! VocÃª foi um dos nossos melhores clientes do mÃªs! ðŸ†",
    mensagem_brinde:
      "ParabÃ©ns! VocÃª foi um dos nossos melhores clientes do mÃªs. Passe em nossa loja e retire seu brinde especial â€” serÃ¡ um prazer recebÃª-lo! ðŸŽ",
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

  // UnificaÃ§Ã£o cross-canal
  const [confirmandoMerge, setConfirmandoMerge] = useState(null);
  const [resultadoMerge, setResultadoMerge] = useState(null);

  // RelatÃ³rios

  // Fidelidade â€” carimbos por cliente (legado â€” mantido para modal existente)
  const [fidClienteId, setFidClienteId] = useState("");
  const [fidCarimbos, setFidCarimbos] = useState(null);
  const [fidLoadingCarimbos, setFidLoadingCarimbos] = useState(false);
  const [fidRemovendo, setFidRemovendo] = useState(null);
  const [fidIncluirEstornados, setFidIncluirEstornados] = useState(false);
  const [fidModalManual, setFidModalManual] = useState(false);
  const [fidLancandoManual, setFidLancandoManual] = useState(false);
  const [fidManualNota, setFidManualNota] = useState("");

  // Gestor de BenefÃ­cios
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
  // Gestor â€” modo Por Campanha
  const [gestorModo, setGestorModo] = useState("cliente"); // 'cliente' | 'campanha'
  const [gestorCampanhaTipo, setGestorCampanhaTipo] = useState("carimbos");
  const [gestorCampanhaLista, setGestorCampanhaLista] = useState(null);
  const [gestorCampanhaCarregando, setGestorCampanhaCarregando] =
    useState(false);

  // Config de ranking
  const [rankingConfigSalvando, setRankingConfigSalvando] = useState(false);

  // Config de horÃ¡rios do scheduler
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
        `Anular o cupÃ£o ${code}? Esta aÃ§Ã£o nÃ£o pode ser desfeita.`,
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
      alert(e?.response?.data?.detail || "Erro ao anular cupÃ£o.");
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
      // Monta vencedores com config individual de prÃªmio (sÃ³ os selecionados)
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
        "Erro ao enviar prÃªmios: " + (e?.response?.data?.detail || e.message),
      );
    } finally {
      setEnviandoDestaque(false);
    }
  };

  const criarCampanha = async () => {
    setErroCriarCampanha("");
    if (!novaCampanha.name.trim()) {
      setErroCriarCampanha("Nome obrigatÃ³rio.");
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
        `Arquivar a campanha "${c.name}"? Ela ficarÃ¡ inativa e nÃ£o poderÃ¡ ser reativada pela interface.`,
      )
    )
      return;
    setArquivando(c.id);
    try {
      await api.delete(`/campanhas/${c.id}`);
      setCampanhas((prev) => prev.filter((x) => x.id !== c.id));
    } catch (e) {
      if (e?.response?.status === 404) {
        // Campanha jÃ¡ nÃ£o existe no servidor â€” remove da lista localmente
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
        `Unificar clientes? O cliente #${removeId} serÃ¡ mesclado no #${keepId}. Os dados de campanhas serÃ£o transferidos.`,
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
        "Desfazer esta unificaÃ§Ã£o? Os dados de campanhas serÃ£o restaurados.",
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
      setErroCriarSorteio("Nome obrigatÃ³rio.");
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
    if (!window.confirm("Executar o sorteio agora? Esta aÃ§Ã£o Ã© irreversÃ­vel."))
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
        "Erro ao carregar cÃ³digos: " + (e?.response?.data?.detail || e.message),
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
        nota: fidManualNota || "Carimbo lanÃ§ado manualmente pelo operador",
      });
      setFidModalManual(false);
      setFidManualNota("");
      await carregarCarimbosCliente();
      alert("âœ… Carimbo lanÃ§ado com sucesso!");
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

  // â”€â”€ Gestor de BenefÃ­cios â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        nota: gestorCarimboNota || "Carimbo lanÃ§ado manualmente pelo operador",
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
            ? "DÃ©bito manual de cashback"
            : "CrÃ©dito manual de cashback"),
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
      alert("CritÃ©rios de ranking salvos!");
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
    if (!window.confirm("Remover esta regra de retenÃ§Ã£o?")) return;
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
    // Para campanhas de aniversÃ¡rio, prÃ©-preenche a mensagem sugerida se ainda nÃ£o foi configurada
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
      console.error("Erro ao salvar parÃ¢metros:", e);
      alert("Erro ao salvar os parÃ¢metros.");
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
    if (!params) return "â€”";
    if (tipo === "loyalty_stamp")
      return `${params.stamps_to_complete || "?"} carimbos â†’ R$ ${formatBRL(params.reward_value || 0)} de recompensa`;
    if (tipo === "cashback")
      return `Bronze ${params.bronze_percent || 0}% / Prata ${params.silver_percent || 0}% / Ouro ${params.gold_percent || 0}%`;
    if (["birthday", "birthday_customer", "birthday_pet"].includes(tipo)) {
      const tipoPresente = params.tipo_presente || "cupom";
      if (tipoPresente === "brinde") return "ðŸŽ Brinde na loja";
      return params.coupon_type === "percent"
        ? `ðŸŽ« Cupom ${params.coupon_value || "?"}% de desconto Â· ${params.coupon_valid_days || "?"} dias`
        : `ðŸŽ« Cupom R$ ${formatBRL(params.coupon_value || 0)} de desconto Â· ${params.coupon_valid_days || "?"} dias`;
    }
    if (tipo === "inactivity") {
      const valInact =
        params.coupon_type === "fixed"
          ? `R$ ${formatBRL(params.coupon_value || 0)}`
          : `${params.coupon_value || "?"}%`;
      return `Inativo ${params.inactivity_days || "?"} dias â†’ ${valInact} desconto`;
    }
    if (tipo === "welcome" || tipo === "welcome_app")
      return `Boas-vindas: R$ ${formatBRL(params.coupon_value || 0)} de bÃ´nus`;
    if (tipo === "ranking_monthly")
      return `${Object.keys(params).length} nÃ­veis configurados`;
    if (tipo === "quick_repurchase") {
      const val =
        params.coupon_type === "fixed"
          ? `R$ ${formatBRL(params.coupon_value || 0)}`
          : `${params.coupon_value || "?"}%`;
      return `PÃ³s-compra: ${val} desconto â€¢ ${params.coupon_valid_days || "?"} dias`;
    }
    return JSON.stringify(params).slice(0, 60) + "...";
  };

  const formatarValorCupom = (cupom) => {
    if (cupom.coupon_type === "percent" && cupom.discount_percent)
      return `${cupom.discount_percent}% off`;
    if (cupom.coupon_type === "fixed" && cupom.discount_value)
      return `R$ ${formatBRL(cupom.discount_value)} off`;
    return "â€”";
  };

  const formatarData = (iso) => {
    if (!iso) return "â€”";
    const d = iso.split("T")[0].split("-");
    return `${d[2]}/${d[1]}/${d[0]}`;
  };

  // â”€â”€ FormulÃ¡rios de parÃ¢metros por tipo de campanha â”€â”€
  const renderFormCampaign = (c) => {
    const tipo = c.campaign_type;
    const set = (key, val) => setParamsEditando((p) => ({ ...p, [key]: val }));
    const num = (key) => paramsEditando[key] ?? "";
    const str = (key) => paramsEditando[key] ?? "";

    if (tipo === "loyalty_stamp")
      return (
        <div className="grid grid-cols-2 gap-3">
          <CampanhaField
            label="Compra mÃ­nima (R$)"
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
            <option value="credit">CrÃ©dito cashback</option>
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
            label="Carimbo intermediÃ¡rio (0 = sem)"
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
            label="Recompensa intermediÃ¡ria (R$)"
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
              <option value="sem_rank">Sem classificaÃ§Ã£o</option>
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
        { key: "bronze_percent", label: "ðŸ¥‰ Bronze" },
        { key: "silver_percent", label: "ðŸ¥ˆ Prata" },
        { key: "gold_percent", label: "ðŸ¥‡ Ouro" },
        { key: "diamond_percent", label: "ðŸ‘‘ Platina" },
        { key: "platinum_percent", label: "ðŸ’Ž Diamante" },
      ];
      const canais = [
        { key: "pdv_bonus_percent", label: "ðŸ–¥ï¸ PDV (bÃ´nus %)" },
        { key: "app_bonus_percent", label: "ðŸ“± App (bÃ´nus %)" },
        { key: "ecommerce_bonus_percent", label: "ðŸ›’ Ecommerce (bÃ´nus %)" },
      ];
      return (
        <div className="space-y-4">
          <div>
            <p className="text-xs text-gray-500 mb-2">
              % base por nÃ­vel de ranking (crÃ©dito automÃ¡tico em toda compra).
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
              BÃ´nus adicional por canal (somado ao % do nÃ­vel). Ex: App +1%
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
              â° Validade e Alertas
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
              ðŸŽ O que o cliente recebe no aniversÃ¡rio?
            </p>
            <div className="flex gap-4">
              {[
                { value: "cupom", label: "ðŸŽ« Cupom de desconto" },
                { value: "brinde", label: "ðŸŽ Brinde na loja" },
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

          {/* Campos do cupom (visÃ­vel apenas se tipo_presente = cupom) */}
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
                âœ‰ï¸ Mensagem enviada ao cliente
              </label>
              <button
                type="button"
                onClick={() => set("notification_message", fraseSugerida)}
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                ðŸ”„ Usar frase sugerida
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
              VariÃ¡veis disponÃ­veis:{" "}
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
            label="Compra mÃ­nima (R$)"
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
              placeholder="Ex: Obrigado pela compra! Use o cupom {code} na prÃ³xima visita."
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
        bronze: "ðŸ¥‰ Bronze",
        silver: "ðŸ¥ˆ Prata",
        gold: "ðŸ¥‡ Ouro",
        diamond: "ï¿½ Platina",
        platinum: "ðŸ’Ž Diamante",
      };
      const getLv = (lv) => paramsEditando[lv] || {};
      const setLv = (lv, key, val) =>
        setParamsEditando((p) => ({ ...p, [lv]: { ...p[lv], [key]: val } }));
      return (
        <div>
          <p className="text-xs text-gray-500 mb-2">
            CritÃ©rios mÃ­nimos para cada nÃ­vel. Recalculado mensalmente.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    NÃ­vel
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Gasto mÃ­n. (R$)
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Compras mÃ­n.
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">
                    Meses ativos mÃ­n.
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

    // fallback: editor genÃ©rico
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
            ðŸŽ¯ Campanhas de Fidelidade
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Gerencie campanhas automÃ¡ticas, ranking de clientes e cupons.
          </p>
        </div>

      </div>

      <CampanhasTabsBar aba={aba} onChange={setAba} />

      {/* â”€â”€ ABA: DASHBOARD â”€â”€ */}
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

      {/* â”€â”€ Modal: Envio para Inativos â”€â”€ */}
      {modalEnvioInativos && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900">
                  âœ‰ï¸ Enviar e-mail de reativaÃ§Ã£o
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Clientes sem compra hÃ¡ mais de {modalEnvioInativos} dias Â· Os
                  e-mails sÃ£o enfileirados e enviados em lotes
                </p>
              </div>
              <button
                onClick={() => {
                  setModalEnvioInativos(null);
                  setResultadoEnvioInativos(null);
                }}
                className="text-gray-400 hover:text-gray-600 text-xl font-bold"
              >
                Ã—
              </button>
            </div>
            <div className="p-6 space-y-4">
              {resultadoEnvioInativos ? (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-1">
                  <p className="font-semibold text-green-800">
                    âœ… E-mails enfileirados com sucesso!
                  </p>
                  <p className="text-sm text-green-700">
                    {resultadoEnvioInativos.enfileirados} e-mail(s)
                    adicionado(s) Ã  fila.
                  </p>
                  {resultadoEnvioInativos.sem_email > 0 && (
                    <p className="text-xs text-gray-500">
                      {resultadoEnvioInativos.sem_email} cliente(s) nÃ£o tÃªm
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
                      placeholder="Ex: Sentimos sua falta! ðŸ¾"
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
                        : "âœ‰ï¸ Enfileirar e-mails"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* â”€â”€ ABA: CAMPANHAS â”€â”€ */}
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


      {/* â”€â”€ ABA: RETENÃ‡ÃƒO DINÃ‚MICA â”€â”€ */}
      {aba === "retencao" && (
        <div className="space-y-4">
          <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 flex items-start gap-3">
            <span className="text-2xl">ðŸ”„</span>
            <div>
              <p className="font-semibold text-orange-800">RetenÃ§Ã£o DinÃ¢mica</p>
              <p className="text-sm text-orange-700 mt-0.5">
                Cada regra detecta clientes que nÃ£o compraram hÃ¡ X dias e envia
                automaticamente um cupom de incentivo. VocÃª pode ter mÃºltiplas
                rÃ©guas: 30 dias, 60 dias, 90 dias â€” cada uma com desconto e
                mensagem diferentes.
              </p>
            </div>
          </div>

          {/* FormulÃ¡rio de criaÃ§Ã£o / ediÃ§Ã£o */}
          {retencaoEditando !== null && (
            <RetencaoForm
              inicial={retencaoEditando}
              salvando={salvandoRetencao}
              onSalvar={salvarRetencao}
              onCancelar={() => setRetencaoEditando(null)}
            />
          )}

          {/* BotÃ£o nova regra */}
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
                    "OlÃ¡, {nome}! Sentimos sua falta. Use o cupom {code} e ganhe {value}% de desconto.",
                  priority: 50,
                })
              }
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm font-medium"
            >
              <span>âž•</span> Nova Regra de RetenÃ§Ã£o
            </button>
          )}

          {/* Lista de regras */}
          {loadingRetencao ? (
            <p className="text-gray-500 text-sm">Carregando...</p>
          ) : retencaoRegras.length === 0 ? (
            <div className="bg-white border rounded-xl p-8 text-center text-gray-500">
              <p className="text-3xl mb-2">ðŸ˜´</p>
              <p className="font-medium">
                Nenhuma regra de retenÃ§Ã£o cadastrada ainda.
              </p>
              <p className="text-sm mt-1">
                Crie sua primeira regra para comeÃ§ar a recuperar clientes
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
                        â±ï¸{" "}
                        <strong>{r.params?.inactivity_days ?? "?"} dias</strong>{" "}
                        sem compra
                      </span>
                      <span>
                        ðŸŽŸï¸ Cupom:{" "}
                        <strong>
                          {r.params?.coupon_type === "percent"
                            ? `${r.params.coupon_value}%`
                            : `R$ ${r.params?.coupon_value}`}
                        </strong>
                      </span>
                      <span>
                        ðŸ“… Validade:{" "}
                        <strong>
                          {r.params?.coupon_valid_days ?? "?"} dias
                        </strong>
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${r.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                      >
                        {r.status === "active" ? "âœ… Ativa" : "â¸ï¸ Pausada"}
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
                      âœï¸ Editar
                    </button>
                    <button
                      onClick={() => deletarRetencao(r.id)}
                      disabled={deletandoRetencao === r.id}
                      className="px-3 py-1.5 text-sm border border-red-200 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                    >
                      {deletandoRetencao === r.id ? "..." : "ðŸ—‘ï¸"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* â”€â”€ ABA: DESTAQUE MENSAL â”€â”€ */}
      {aba === "destaque" && (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
            <span className="text-2xl">ðŸŒŸ</span>
            <div>
              <p className="font-semibold text-amber-800">Destaque Mensal</p>
              <p className="text-sm text-amber-700 mt-0.5">
                O sistema identifica os clientes que mais gastaram e mais
                compraram no mÃªs anterior. VocÃª pode premiar cada vencedor com
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
                      Vencedores â€” {destaque.periodo}
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {destaque.total_clientes_ativos} clientes ativos no
                      perÃ­odo
                    </p>
                  </div>
                  <button
                    onClick={carregarDestaque}
                    className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200"
                  >
                    ðŸ”„ Recalcular
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
                        {/* CabeÃ§alho: checkbox + tÃ­tulo + toggle de tipo de prÃªmio */}
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
                                ? "ðŸ’° Maior Gasto"
                                : "ðŸ›’ Mais Compras"}
                            </p>
                          </label>
                          <div className="flex gap-1">
                            <button
                              onClick={() =>
                                setPremio({ tipo_premio: "cupom" })
                              }
                              className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${premio.tipo_premio !== "mensagem" ? "bg-amber-500 text-white border-amber-500" : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"}`}
                            >
                              ðŸŽŸï¸ Cupom
                            </button>
                            <button
                              onClick={() =>
                                setPremio({ tipo_premio: "mensagem" })
                              }
                              className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${premio.tipo_premio === "mensagem" ? "bg-amber-500 text-white border-amber-500" : "bg-white text-gray-600 border-gray-200 hover:border-amber-300"}`}
                            >
                              ðŸŽ Brinde
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
                                placeholder="Ex: ParabÃ©ns! Use este cupom em sua prÃ³xima visita ðŸ†"
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
                                  Retirada atÃ©
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
                      Nenhum vencedor identificado para o perÃ­odo.
                    </div>
                  )}
                </div>

                {/* Aviso de desempate â€” exibe quando o 2Âº colocado substituiu o 1Âº */}
                {(destaque.desempate_info || []).length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-300 rounded-xl p-4 space-y-2">
                    <p className="font-semibold text-yellow-800 text-sm flex items-center gap-2">
                      âš–ï¸ Desempate aplicado
                    </p>
                    {destaque.desempate_info.map((d, i) => (
                      <div
                        key={i}
                        className="text-sm text-yellow-700 leading-relaxed"
                      >
                        <span className="font-medium">
                          {d.categoria === "maior_gasto"
                            ? "ðŸ’° Maior Gasto"
                            : "ðŸ›’ Mais Compras"}
                          :
                        </span>{" "}
                        <span className="line-through text-yellow-500">
                          {d.pulado?.nome}
                        </span>{" "}
                        (1Âº lugar) jÃ¡ ganhou em outra categoria â€” o{" "}
                        <span className="font-medium">
                          {d.posicao_eleito}Âº colocado
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
                        âœ… PrÃªmios enviados! ({destaqueResultado.enviados}{" "}
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
                              ? "ðŸ’° Maior Gasto"
                              : "ðŸ›’ Mais Compras"}
                            :
                          </span>
                          {r.tipo_premio === "cupom" ? (
                            <>
                              <span className="font-mono font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded">
                                {r.coupon_code}
                              </span>
                              {r.ja_existia && (
                                <span className="text-xs text-gray-400">
                                  (jÃ¡ existia)
                                </span>
                              )}
                            </>
                          ) : (
                            <span className="text-amber-700">
                              ðŸŽ Brinde registrado
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
                        ? "Enviando prÃªmios..."
                        : "ðŸ† Enviar PrÃªmios aos Vencedores"}
                    </button>
                  )
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  ["maior_gasto", "top5_maior_gasto", "ðŸ’° Top 5 â€” Maior Gasto"],
                  [
                    "mais_compras",
                    "top5_mais_compras",
                    "ðŸ›’ Top 5 â€” Mais Compras",
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
                            <span className="text-yellow-500 text-lg">ðŸ†</span>
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

      {/* â”€â”€ ABA: SORTEIOS â”€â”€ */}
      {aba === "sorteios" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                ðŸŽ² Sorteios
              </h2>
              <p className="text-sm text-gray-500">
                Crie sorteios exclusivos por nÃ­vel de ranking. O resultado Ã©
                auditÃ¡vel via seed UUID.
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
                ðŸŽ‰ Sorteio executado!
              </p>
              <p className="text-purple-700">
                Ganhador: <strong>{sorteioResultado.winner_name}</strong>
              </p>
              <p className="text-sm text-purple-600 mt-1">
                {sorteioResultado.total_participantes} participante(s) Â· Seed:{" "}
                <span className="font-mono text-xs">
                  {sorteioResultado.seed_uuid?.slice(0, 16)}â€¦
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
              <p className="text-3xl mb-2">ðŸŽ²</p>
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
                  draft: "ðŸ“ Rascunho",
                  open: "âœ… Inscrito",
                  drawn: "ðŸ† Realizado",
                  cancelled: "âŒ Cancelado",
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
                            ðŸŽ {s.prize_description}
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
                            ` Â· Sorteio: ${new Date(s.draw_date).toLocaleDateString("pt-BR")}`}
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
                              : "ðŸ“‹ Inscrever ElegÃ­veis"}
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
                              : "ðŸŽ² Executar Sorteio"}
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
                            ðŸ“‹ CÃ³digos Offline
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

      {/* â”€â”€ ABA: RANKING â”€â”€ */}
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
                    "âœ… RecÃ¡lculo de ranking enfileirado! O worker processarÃ¡ em atÃ© 10 segundos.",
                  );
                  setTimeout(() => carregarRanking(), 3000);
                } catch (e) {
                  alert("Erro: " + (e?.response?.data?.detail || e.message));
                }
              }}
              className="ml-auto px-4 py-2 bg-gray-700 text-white rounded-full text-sm font-medium hover:bg-gray-800 transition-colors"
            >
              ðŸ”„ Recalcular Agora
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
                    PerÃ­odo: {ranking.periodo}
                  </p>
                </div>
                {ranking.clientes.length === 0 ? (
                  <div className="p-8 text-center text-gray-400">
                    Nenhum cliente neste nÃ­vel.
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
                            NÃ­vel
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

          {/* BotÃ£o Envio em Lote */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-blue-800">ðŸ“§ Envio em Lote</p>
              <p className="text-sm text-blue-600">
                Envie um e-mail personalizado para todos os clientes de um
                nÃ­vel.
              </p>
            </div>
            <button
              onClick={() => {
                setResultadoLote(null);
                setModalLote(true);
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Enviar para NÃ­vel
            </button>
          </div>

          {/* Config de critÃ©rios de ranking */}
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
                âš™ï¸ Configurar CritÃ©rios de Ranking
              </span>
              <span className="text-gray-400 text-sm">
                {rankingConfig?._aberto ? "â–² Fechar" : "â–¼ Expandir"}
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
                    NÃ£o foi possÃ­vel carregar.
                  </div>
                ) : (
                  <>
                    <p className="text-xs text-gray-500">
                      O cliente precisa atingir <strong>todos</strong> os
                      critÃ©rios de um nÃ­vel para alcanÃ§Ã¡-lo (gasto, compras e
                      meses ativos nos Ãºltimos 12 meses). Quem nÃ£o atingir o
                      mÃ­nimo de Prata fica como Bronze.
                    </p>
                    {[
                      { key: "silver", label: "ðŸ¥ˆ Prata" },
                      { key: "gold", label: "ðŸ¥‡ Ouro" },
                      { key: "diamond", label: "ðŸ‘‘ Platina" },
                      { key: "platinum", label: "ðŸ’¸ Diamante" },
                    ].map(({ key, label }) => (
                      <div
                        key={key}
                        className="border rounded-xl p-4 space-y-2"
                      >
                        <p className="font-medium text-gray-700">{label}</p>
                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">
                              Gasto mÃ­nimo (R$)
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
                              Compras mÃ­nimas
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
                              Meses ativos mÃ­nimos
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
                          : "Salvar CritÃ©rios"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* BenefÃ­cios por NÃ­vel */}
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
                ðŸ“Š BenefÃ­cios por NÃ­vel
              </span>
              <span className="text-gray-400 text-sm">
                {rankingConfig?._beneficios_aberto ? "â–² Fechar" : "â–¼ Expandir"}
              </span>
            </button>
            {rankingConfig?._beneficios_aberto && (
              <div className="px-6 pb-6 space-y-4">
                <p className="text-xs text-gray-500">
                  VisÃ£o geral dos critÃ©rios de cada nÃ­vel. Para configurar
                  benefÃ­cios especÃ­ficos (cashback %, carimbos, sorteios
                  exclusivos), acesse a campanha correspondente.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="bg-gray-50 text-gray-600 text-xs uppercase">
                        <th className="text-left p-3 border-b">NÃ­vel</th>
                        <th className="text-center p-3 border-b">
                          Gasto mÃ­n. (R$)
                        </th>
                        <th className="text-center p-3 border-b">
                          Compras mÃ­n.
                        </th>
                        <th className="text-center p-3 border-b">
                          Meses ativos mÃ­n.
                        </th>
                        <th className="text-center p-3 border-b">
                          Cashback
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { key: "bronze", label: "ðŸ¥‰ Bronze", base: true },
                        { key: "silver", label: "ðŸ¥ˆ Prata" },
                        { key: "gold", label: "ðŸ¥‡ Ouro" },
                        { key: "diamond", label: "ðŸ‘‘ Platina" },
                        { key: "platinum", label: "ðŸ’¸ Diamante" },
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
                              ? "â€”"
                              : rankingConfig
                                ? `R$ ${formatBRL(rankingConfig[`${key}_min_spent`] ?? 0)}`
                                : "â€¦"}
                          </td>
                          <td className="p-3 text-center text-gray-600">
                            {base
                              ? "â€”"
                              : (rankingConfig?.[`${key}_min_purchases`] ??
                                "â€¦")}
                          </td>
                          <td className="p-3 text-center text-gray-600">
                            {base
                              ? "â€”"
                              : (rankingConfig?.[`${key}_min_months`] ?? "â€¦")}
                          </td>
                          <td className="p-3 text-center text-gray-600">
                            {(() => {
                              const cashPct = campanhas.find(c => c.campaign_type === 'cashback')?.params?.[`${key}_percent`];
                              return cashPct != null ? `${cashPct}%` : 'â€”';
                            })()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="bg-blue-50 rounded-lg p-4 text-xs text-blue-700 space-y-1.5">
                  <p className="font-semibold">
                    â„¹ï¸ Como configurar os benefÃ­cios por nÃ­vel:
                  </p>
                  <p>
                    â€¢ <strong>Cashback % por nÃ­vel:</strong> acesse a campanha
                    de Cashback e configure os campos Bronze / Prata / Ouro /
                    Platina / Diamante.
                  </p>
                  <p>
                    â€¢ <strong>Carimbos exclusivos:</strong> crie uma campanha de
                    Carimbo com o campo "NÃ­vel mÃ­nimo" definido para restringir
                    a um grupo.
                  </p>
                  <p>
                    â€¢ <strong>Sorteios exclusivos:</strong> na aba Sorteios,
                    defina o campo "RestriÃ§Ã£o de nÃ­vel" ao criar o sorteio.
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
                Busca (cÃ³digo ou cliente)
              </label>
              <input
                type="text"
                value={filtroCupomBusca}
                onChange={(e) => setFiltroCupomBusca(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && carregarCupons()}
                placeholder="Ex: ANIV ou JoÃ£o Silva"
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
                Criado atÃ©
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
              ðŸ” Filtrar
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
                <p className="text-2xl mb-2">ðŸŽŸï¸</p>
                <p>Nenhum cupom encontrado.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">
                        CÃ³digo
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
                        AÃ§Ã£o
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
                                    ? "ðŸŽ Brinde"
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
                                <span className="text-gray-300">â€”</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-gray-500 text-xs">
                              {c.created_at
                                ? new Date(c.created_at).toLocaleDateString(
                                    "pt-BR",
                                  )
                                : "â€”"}
                            </td>
                            <td className="px-4 py-3 text-gray-500">
                              {c.valid_until
                                ? new Date(c.valid_until).toLocaleDateString(
                                    "pt-BR",
                                  )
                                : "â€”"}
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
                                    : "ðŸš« Anular"}
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
                                      CÃ³digo
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
                                        : "â€”"}
                                    </p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-gray-500 font-medium mb-0.5">
                                      VÃ¡lido atÃ©
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
                                        Retirada atÃ©
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
                                          ? "ðŸ’° Maior Gasto"
                                          : c.meta.categoria === "mais_compras"
                                            ? "ðŸ›’ Mais Compras"
                                            : c.meta.categoria}
                                      </p>
                                    </div>
                                  )}
                                  {c.meta?.periodo && (
                                    <div>
                                      <p className="text-xs text-gray-500 font-medium mb-0.5">
                                        PerÃ­odo
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

      {/* â”€â”€ ABA: RELATÃ“RIOS â”€â”€ */}
      {aba === "relatorios" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border shadow-sm p-4 flex flex-wrap gap-4 items-end">
            <div>
              <label
                htmlFor="rel-data-inicio"
                className="block text-xs font-medium text-gray-600 mb-1"
              >
                Data inÃ­cio
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
                <option value="credito">SÃ³ crÃ©ditos</option>
                <option value="resgate">SÃ³ resgates</option>
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
                HistÃ³rico de MovimentaÃ§Ãµes
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                CrÃ©ditos = cashback gerado ao cliente. Resgates = cashback usado
                como pagamento numa venda.
              </p>
            </div>
            {loadingRelatorio ? (
              <div className="p-8 text-center text-gray-400">
                Carregando relatÃ³rio...
              </div>
            ) : !relatorio || relatorio.transacoes.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <p className="text-2xl mb-2">ðŸ“­</p>
                <p>Nenhuma movimentaÃ§Ã£o no perÃ­odo.</p>
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
                        DescriÃ§Ã£o
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
                            {t.tipo === "credito" ? "â¬†ï¸ CrÃ©dito" : "â¬‡ï¸ Resgate"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-500">
                          {t.venda_id || "â€”"}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold">
                          R$ {formatBRL(t.valor)}
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs max-w-[200px] truncate">
                          {t.descricao || "â€”"}
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

      {/* â”€â”€ ABA: UNIFICAÃ‡ÃƒO CROSS-CANAL â”€â”€ */}
      {aba === "unificacao" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border shadow-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="font-semibold text-gray-800">
                  ðŸ”— UnificaÃ§Ã£o Cross-Canal por CPF/Telefone
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Clientes que parecem ser a mesma pessoa (mesmo CPF ou mesmo
                  telefone) aparecem aqui para unificaÃ§Ã£o manual.
                </p>
              </div>
              <button
                onClick={carregarSugestoes}
                disabled={loadingSugestoes}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {loadingSugestoes ? "Buscando..." : "ðŸ” Buscar Duplicatas"}
              </button>
            </div>

            {resultadoMerge && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 text-sm flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-green-800">
                    âœ… Clientes unificados! (Merge #{resultadoMerge.merge_id})
                  </p>
                  <p className="text-green-600">
                    Transferidos: {resultadoMerge.transferencias?.cashback ?? 0}{" "}
                    cashbacks, {resultadoMerge.transferencias?.carimbos ?? 0}{" "}
                    carimbos, {resultadoMerge.transferencias?.cupons ?? 0}{" "}
                    cupons, {resultadoMerge.transferencias?.ranking ?? 0}{" "}
                    posiÃ§Ãµes de ranking,{" "}
                    {resultadoMerge.transferencias?.vendas ?? 0} vendas,{" "}
                    {resultadoMerge.transferencias?.execucoes_campanhas ?? 0}{" "}
                    execuÃ§Ãµes de campanha.
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
                <p className="text-3xl mb-2">âœ…</p>
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
                        AÃ§Ã£o
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
                              ? "ðŸªª Mesmo CPF"
                              : "ðŸ“ž Mesmo Telefone"}
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
                              Unir A â† B
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
                              Unir B â† A
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

      {/* â”€â”€ MODAL: CRIAR SORTEIO â”€â”€ */}
      {modalSorteio && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">ðŸŽ² Novo Sorteio</h3>
              <button
                onClick={() => setModalSorteio(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ã—
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
                  placeholder="Ex: Sorteio de MarÃ§o"
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
                  PrÃªmio
                </label>
                <input
                  id="s-premio"
                  type="text"
                  placeholder="Ex: Kit banho + tosa grÃ¡tis"
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
                  NÃ­vel mÃ­nimo elegantÃ­vel (opcional)
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
                  <option value="bronze">ðŸ¥‰ Bronze+</option>
                  <option value="silver">ðŸ¥ˆ Prata+</option>
                  <option value="gold">ðŸ¥‡ Ouro+</option>
                  <option value="platinum">ðŸ’Ž Diamante+</option>
                  <option value="diamond">ðŸ‘‘ Platina</option>
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
                  DescriÃ§Ã£o (opcional)
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
                  ðŸ¤– Executar automaticamente na data do sorteio
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

      {/* â”€â”€ MODAL: CÃ“DIGOS OFFLINE (SORTEIO) â”€â”€ */}
      {modalCodigosOffline && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900">
                  ðŸ“‹ CÃ³digos Offline â€” {modalCodigosOffline.name}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Lista de participantes para sorteio fÃ­sico
                </p>
              </div>
              <div className="flex gap-2 items-center">
                <button
                  onClick={() => window.print()}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200"
                >
                  ðŸ–¨ï¸ Imprimir
                </button>
                <button
                  onClick={() => setModalCodigosOffline(null)}
                  className="text-gray-400 hover:text-gray-600 text-xl ml-2"
                >
                  Ã—
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
                      <th className="text-center p-2 border-b w-16">NÂº</th>
                      <th className="text-left p-2 border-b">Cliente</th>
                      <th className="text-center p-2 border-b">NÃ­vel</th>
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
                            : "â€”"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="px-6 py-3 border-t text-xs text-gray-400">
              {codigosOffline.length} participante(s) Â· Sorteio:{" "}
              {modalCodigosOffline.name}
            </div>
          </div>
        </div>
      )}

      {/* â”€â”€ MODAL: LANÃ‡AR CARIMBO MANUAL â”€â”€ */}
      {fidModalManual && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                ðŸ·ï¸ LanÃ§ar Carimbo Manual
              </h3>
              <button
                onClick={() => setFidModalManual(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ã—
              </button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <p className="text-sm text-gray-500">
                Cliente <strong>#{fidClienteId}</strong> â€” Esse carimbo serÃ¡
                registrado como manual (sem vÃ­nculo com uma venda).
              </p>
              <div>
                <label
                  htmlFor="fid-nota"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  ObservaÃ§Ã£o (opcional)
                </label>
                <input
                  id="fid-nota"
                  type="text"
                  value={fidManualNota}
                  onChange={(e) => setFidManualNota(e.target.value)}
                  placeholder="Ex: ConversÃ£o de cartÃ£o fÃ­sico"
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
                {fidLancandoManual ? "LanÃ§ando..." : "Confirmar Carimbo"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* â”€â”€ MODAL: ENVIO EM LOTE â”€â”€ */}
      {modalLote && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">ðŸ“§ Envio em Lote</h3>
              <button
                onClick={() => setModalLote(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ã—
              </button>
            </div>
            <div className="px-6 py-4 space-y-3">
              <div>
                <label
                  htmlFor="lote-nivel"
                  className="block text-xs font-medium text-gray-600 mb-1"
                >
                  NÃ­vel de ranking
                </label>
                <select
                  id="lote-nivel"
                  value={loteForm.nivel}
                  onChange={(e) =>
                    setLoteForm((p) => ({ ...p, nivel: e.target.value }))
                  }
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="todos">Todos os nÃ­veis</option>
                  <option value="platinum">ðŸ’Ž Diamante</option>
                  <option value="diamond">ðŸ‘‘ Platina</option>
                  <option value="gold">ðŸ¥‡ Ouro</option>
                  <option value="silver">ðŸ¥ˆ Prata</option>
                  <option value="bronze">ðŸ¥‰ Bronze</option>
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
                  placeholder="Ex: PromoÃ§Ã£o exclusiva para clientes Ouro!"
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
                  placeholder="Escreva a mensagem que serÃ¡ enviada para os clientes..."
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
                    âœ… {resultadoLote.enfileirados} e-mail(s) enfileirado(s)!
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

      {/* â”€â”€ MODAL: NOVA CAMPANHA â”€â”€ */}
      {modalCriarCampanha && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">âž• Nova Campanha</h3>
              <button
                onClick={() => setModalCriarCampanha(false)}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ã—
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
                  placeholder="Ex: Recompra RÃ¡pida VerÃ£o"
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
                  <option value="inactivity">ðŸ˜´ Clientes Inativos</option>
                  <option value="quick_repurchase">ðŸ” Recompra RÃ¡pida</option>
                </select>
              </div>
              <p className="text-xs text-gray-500">
                Os parÃ¢metros poderÃ£o ser configurados depois de criar a
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

      {/* â”€â”€ MODAL: CRIAR CUPOM MANUAL â”€â”€ */}
      {modalCupomAberto && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">
                ðŸŽŸï¸ Criar Cupom Manual
              </h3>
              <button
                onClick={() => {
                  setModalCupomAberto(false);
                  setErroCupom("");
                }}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                Ã—
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
                  VÃ¡lido atÃ© (opcional)
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
                  Compra mÃ­nima (R$, opcional)
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
                  placeholder="Deixe vazio para cupom genÃ©rico"
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
                  DescriÃ§Ã£o (opcional)
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
                  ðŸ› ï¸ Gestor de BenefÃ­cios
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {gestorModo === "cliente"
                    ? "Busque um cliente para gerenciar seus benefÃ­cios."
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
                  ðŸ” Por Cliente
                </button>
                <button
                  onClick={() => setGestorModo("campanha")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    gestorModo === "campanha"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  ðŸ·ï¸ Por Campanha
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
                          {c.cpf && c.telefone ? " Â· " : ""}
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
                  <option value="carimbos">ðŸ·ï¸ CartÃ£o Fidelidade</option>
                  <option value="cashback">ðŸ’° Cashback (saldo positivo)</option>
                  <option value="cupons">ðŸŽŸï¸ Cupons Ativos</option>
                  <option value="ranking">ðŸ† Ranking (mÃªs atual)</option>
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
                    Clique em â€œVer detalhesâ€ para gerenciar
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
                            {c.cpf && c.telefone ? " Â· " : ""}
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
                          Ver detalhes â†’
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
                      ID #{gestorCliente.id} Â·{" "}
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

                {/* â”€â”€ SeÃ§Ã£o: Carimbos â”€â”€ */}
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
                      <span className="text-xl">ðŸ·ï¸</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">
                          CartÃ£o Fidelidade
                        </p>
                        <p className="text-xs text-gray-500">
                          {gestorSaldo.total_carimbos} carimbo(s) ativo(s)
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "carimbos" ? "â–²" : "â–¼"}
                    </span>
                  </button>
                  {gestorSecao === "carimbos" && (
                    <div className="border-t p-6 space-y-4">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <p className="text-sm font-medium text-green-800 mb-3">
                          âž• LanÃ§ar Carimbo Manual
                        </p>
                        <div className="flex gap-3 flex-wrap items-end">
                          <div className="flex-1 min-w-[200px]">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              ObservaÃ§Ã£o (opcional)
                            </label>
                            <input
                              type="text"
                              value={gestorCarimboNota}
                              onChange={(e) =>
                                setGestorCarimboNota(e.target.value)
                              }
                              placeholder="Ex: ConversÃ£o de cartÃ£o fÃ­sico"
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            />
                          </div>
                          <button
                            onClick={lancarCarimboGestor}
                            disabled={gestorLancandoCarimbo}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                          >
                            {gestorLancandoCarimbo
                              ? "LanÃ§ando..."
                              : "âœ… LanÃ§ar Carimbo"}
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
                                  AÃ§Ã£o
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
                                          AutomÃ¡tico
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-4 py-2 text-gray-500 text-xs max-w-[180px] truncate">
                                      {s.notes || "â€”"}
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
                                            : "âŒ Remover"}
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

                {/* â”€â”€ SeÃ§Ã£o: Cashback â”€â”€ */}
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
                      <span className="text-xl">ðŸ’°</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Cashback</p>
                        <p className="text-xs text-gray-500">
                          Saldo: R$ {formatBRL(gestorSaldo.saldo_cashback)}
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "cashback" ? "â–²" : "â–¼"}
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
                          âœï¸ Ajuste Manual
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
                                âž• CrÃ©dito (adicionar)
                              </option>
                              <option value="debito">
                                âž– DÃ©bito (remover)
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
                              placeholder="Ex: CorreÃ§Ã£o de campanha"
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
                              ? "âž– Confirmar DÃ©bito"
                              : "âž• Confirmar CrÃ©dito"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* â”€â”€ SeÃ§Ã£o: Cupons â”€â”€ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(gestorSecao === "cupons" ? null : "cupons")
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">ðŸŽŸï¸</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Cupons</p>
                        <p className="text-xs text-gray-500">
                          {gestorCupons?.filter((c) => c.status === "active")
                            .length || 0}{" "}
                          ativo(s) Â· {gestorCupons?.length || 0} no total
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "cupons" ? "â–²" : "â–¼"}
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
                                  CÃ³digo
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
                                  AÃ§Ã£o
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
                                      ? "ðŸŽ Brinde"
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
                                          : "ðŸš« Anular"}
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

                {/* â”€â”€ SeÃ§Ã£o: Ranking â”€â”€ */}
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
                      <span className="text-xl">ðŸ†</span>
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
                            ? ` Â· ${gestorSaldo.rank_period}`
                            : ""}
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "ranking" ? "â–²" : "â–¼"}
                    </span>
                  </button>
                  {gestorSecao === "ranking" && (
                    <div className="border-t p-6">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                          {
                            label: "NÃ­vel",
                            value: (() => {
                              const r =
                                RANK_LABELS[gestorSaldo.rank_level] ||
                                RANK_LABELS.bronze;
                              return `${r.emoji} ${r.label}`;
                            })(),
                          },
                          {
                            label: "PerÃ­odo",
                            value: gestorSaldo.rank_period || "â€”",
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
                        O nÃ­vel de ranking Ã© recalculado automaticamente no dia
                        1 de cada mÃªs.
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}
        </div>
      )}

      {/* â”€â”€ ABA: CONFIGURAÃ‡Ã•ES â”€â”€ */}
      {aba === "config" && (
        <div className="space-y-6">
          {/* Header */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="font-semibold text-gray-800 mb-1">
              âš™ï¸ ConfiguraÃ§Ãµes de Envio
            </h2>
            <p className="text-xs text-gray-500">
              Defina os horÃ¡rios em que o sistema envia as mensagens automÃ¡ticas
              de cada campanha.
            </p>
          </div>

          {/* Loading */}
          {schedulerConfigLoading && (
            <div className="text-center py-12 text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-sm">Carregando configuraÃ§Ãµes...</p>
            </div>
          )}

          {/* FormulÃ¡rio */}
          {schedulerConfig && !schedulerConfigLoading && (
            <div className="space-y-4">
              {/* Card: AniversÃ¡rios */}
              <div className="bg-white rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-3 mb-5">
                  <span className="text-2xl">ðŸŽ‚</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Mensagens de AniversÃ¡rio
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
                  <span className="text-2xl">ðŸ˜´</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Mensagens de ReativaÃ§Ã£o (Clientes Inativos)
                    </h3>
                    <p className="text-xs text-gray-500">
                      Enviadas uma vez por semana para clientes sem compras hÃ¡
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
                      <option value="tue">TerÃ§a-feira</option>
                      <option value="wed">Quarta-feira</option>
                      <option value="thu">Quinta-feira</option>
                      <option value="fri">Sexta-feira</option>
                      <option value="sat">SÃ¡bado</option>
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
                  <span className="text-2xl">ðŸ…</span>
                  <div>
                    <h3 className="font-medium text-gray-800">
                      Auto-envio do Destaque Mensal
                    </h3>
                    <p className="text-xs text-gray-500">
                      Calcula e envia automaticamente o cupom ao vencedor do mÃªs
                      no dia 1 Ã s 08:00
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
                      Ativar envio automÃ¡tico do Destaque Mensal
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

              {/* BotÃ£o salvar */}
              <div className="flex justify-end">
                <button
                  onClick={salvarSchedulerConfig}
                  disabled={schedulerConfigSalvando}
                  className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {schedulerConfigSalvando
                    ? "Salvando..."
                    : "ðŸ’¾ Salvar ConfiguraÃ§Ãµes"}
                </button>
              </div>

              {/* Nota informativa */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <p className="text-xs text-amber-700">
                  âš ï¸ <strong>AtenÃ§Ã£o:</strong> Os horÃ¡rios aqui salvos sÃ£o
                  registrados no sistema. O scheduler usarÃ¡ os novos valores a
                  partir do prÃ³ximo reinÃ­cio do servidor. Para aplicar
                  imediatamente em produÃ§Ã£o, avise o suporte tÃ©cnico.
                </p>
              </div>
            </div>
          )}

          {/* Estado vazio */}
          {!schedulerConfig && !schedulerConfigLoading && (
            <div className="bg-white rounded-xl border shadow-sm p-6 text-center">
              <p className="text-sm text-gray-500 mb-2">
                NÃ£o foi possÃ­vel carregar as configuraÃ§Ãµes.
              </p>
              <p className="text-xs text-gray-400">
                Certifique-se de que as campanhas padrÃ£o foram inicializadas
                (botÃ£o &quot;Inicializar Campanhas&quot; na aba Campanhas).
              </p>
            </div>
          )}
        </div>
      )}

      {/* â”€â”€ ABA: DESCONTOS POR CANAL â”€â”€ */}
      {aba === "canais" && <CanalDescontos />}
    </div>
  );
}

