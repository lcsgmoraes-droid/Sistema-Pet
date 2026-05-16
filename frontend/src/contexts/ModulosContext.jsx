/**
 * ModulosContext - Gerenciamento de módulos premium do sistema
 *
 * Módulos controlados por plano/assinatura:
 *   compras, financeiro_erp, veterinario, banho_tosa, fiscal, campanhas etc.
 *
 * Plano basico (sempre ativo):
 *   pessoas, pets, produtos, estoque, PDV, vendas/financeiro de vendas,
 *   usuarios, configuracoes essenciais e cadastros essenciais.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api } from "../services/api";
import { getAccessToken } from "../auth/tokenStorage";
import { useAuth } from "./AuthContext";

const ModulosContext = createContext();
const DEV_MODULOS_STORAGE_KEY = "dev_modulos_config";
const DEV_MODULOS_MODOS_VALIDOS = [
  "normal",
  "custom",
  "all_unlocked",
  "all_locked",
];

export const MODULOS_PREMIUM = [
  "compras",
  "financeiro_erp",
  "comissoes",
  "veterinario",
  "banho_tosa",
  "fiscal",
  "bling",
  "integracoes",
  "rh",
  "ia_avancada",
  "entregas",
  "campanhas",
  "whatsapp",
  "ecommerce",
  "app_mobile",
  "marketplaces",
];

export const MODULOS_FORA_DA_OFERTA_PUBLICA = ["bling"];
export const MODULOS_BETA_PUBLICOS = MODULOS_PREMIUM.filter(
  (modulo) => !MODULOS_FORA_DA_OFERTA_PUBLICA.includes(modulo),
);

export const MODULOS_INFO = {
  compras: {
    nome: "Compras e Entrada XML",
    descricao:
      "Pedidos de compra, entrada por XML, pendencias de compra e conferencias avancadas de estoque.",
    preco: 79,
    recursos: [
      "Pedidos de compra por fornecedor",
      "Entrada de produtos via XML",
      "Conferencia de pendencias",
      "Sugestao de compras integrada ao estoque",
    ],
  },
  financeiro_erp: {
    nome: "Financeiro ERP",
    descricao:
      "Contas a pagar, contas a receber, fluxo de caixa, DRE e conciliacoes financeiras.",
    preco: 99,
    recursos: [
      "Contas a pagar e receber",
      "Fluxo de caixa",
      "DRE operacional",
      "Conciliacao bancaria e de cartoes",
    ],
  },
  comissoes: {
    nome: "Comissoes",
    descricao:
      "Configuracao, demonstrativos, provisoes e fechamento de comissoes por funcionario.",
    preco: 49,
    recursos: [
      "Regras de comissao",
      "Demonstrativo por funcionario",
      "Fechamentos e historico",
      "Integracao com vendas e financeiro",
    ],
  },
  veterinario: {
    nome: "Modulo Veterinario",
    descricao:
      "Agenda, consultas, prontuario, vacinas, exames, internacoes e catalogos clinicos.",
    preco: 119,
    recursos: [
      "Prontuario e consultas",
      "Agenda veterinaria",
      "Vacinas e exames",
      "Internacoes e repasses",
    ],
  },
  banho_tosa: {
    nome: "Banho & Tosa",
    descricao:
      "Agenda, fila do dia, servicos, pacotes, retornos, taxi dog e relatorios do banho e tosa.",
    preco: 89,
    recursos: [
      "Agenda e fila operacional",
      "Servicos e recursos",
      "Pacotes e retornos",
      "Fechamento integrado ao PDV",
    ],
  },
  fiscal: {
    nome: "Fiscal / NF",
    descricao:
      "Emissao e acompanhamento fiscal para notas de saida, preparado para integracao fiscal dedicada.",
    preco: 0,
    recursos: [
      "Central de notas de saida",
      "Configuracao fiscal",
      "Historico fiscal por venda",
      "Preparado para API fiscal",
    ],
  },
  bling: {
    nome: "Integracao Bling",
    descricao:
      "Sincronizacao e monitoramento de pedidos, produtos, estoque e notas via Bling.",
    preco: 69,
    recursos: [
      "Pedidos Bling",
      "Monitor de sincronizacao",
      "Sincronizacao de produtos",
      "Auditoria de integracao",
    ],
  },
  integracoes: {
    nome: "Integracoes",
    descricao:
      "Configuracoes e conectores externos para automacoes, canais e plataformas integradas.",
    preco: 0,
    recursos: [
      "Configurar conectores",
      "Monitorar integracoes",
      "Preparar automacoes externas",
    ],
  },
  rh: {
    nome: "Recursos Humanos",
    descricao:
      "Cadastro operacional de funcionarios e estruturas internas alem dos usuarios do sistema.",
    preco: 49,
    recursos: [
      "Funcionarios",
      "Cargos e departamentos",
      "Apoio a comissoes",
    ],
  },
  ia_avancada: {
    nome: "IA Avancada",
    descricao:
      "Recursos de IA alem do chat basico, como previsoes financeiras e assistentes especializados.",
    preco: 79,
    recursos: [
      "Fluxo de caixa preditivo",
      "Alertas inteligentes",
      "Assistentes por modulo",
    ],
  },
  entregas: {
    nome: "Entregas",
    descricao:
      "Gerencie rotas de entrega, rastreamento em tempo real e app para entregadores.",
    preco: 79,
    recursos: [
      "Rotas de entrega otimizadas",
      "Rastreamento em tempo real para o cliente",
      "App mobile para entregadores",
      "Dashboard financeiro de entregas",
      "Histórico completo de entregas",
    ],
  },
  campanhas: {
    nome: "Campanhas",
    descricao:
      "Crie campanhas de marketing, promoções e fidelize seus clientes.",
    preco: 49,
    recursos: [
      "Campanhas de desconto personalizadas",
      "Segmentação de clientes",
      "Relatórios de engajamento",
      "Envio automático por WhatsApp",
    ],
  },
  whatsapp: {
    nome: "WhatsApp Bot",
    descricao:
      "Automatize o atendimento via WhatsApp com inteligência artificial.",
    preco: 119,
    recursos: [
      "Bot de atendimento 24/7",
      "Respostas automáticas com IA",
      "Integração com o catálogo de produtos",
      "Notificações de pedidos e entregas",
      "Painel de conversa ao vivo",
    ],
  },
  ecommerce: {
    nome: "E-commerce",
    descricao:
      "Venda online com sua própria loja virtual integrada ao sistema.",
    preco: 99,
    recursos: [
      "Loja virtual com seu domínio",
      "Catálogo de produtos online",
      "Pagamento online integrado",
      "Gestão de pedidos online",
      "Analytics de vendas online",
    ],
  },
  app_mobile: {
    nome: "App para Clientes",
    descricao:
      "Ofereça um app mobile próprio para seus clientes comprarem e acompanharem pedidos.",
    preco: 69,
    recursos: [
      "App iOS e Android com sua marca",
      "Catálogo de produtos",
      "Carrinho de compras",
      "Acompanhamento de pedidos",
      "Notificações push",
    ],
  },
  marketplaces: {
    nome: "Marketplaces",
    descricao:
      "Venda no Mercado Livre, Shopee, Amazon e outros de forma integrada.",
    preco: 99,
    recursos: [
      "Integração com Mercado Livre",
      "Integração com Shopee",
      "Gestão de estoque unificada",
      "Sincronização automática de preços",
      "Relatórios por canal de venda",
    ],
  },
};

export const ModulosProvider = ({ children }) => {
  const { user } = useAuth();
  const [modulosAtivos, setModulosAtivos] = useState(null); // null = carregando
  const [modulosBetaPublicos, setModulosBetaPublicos] = useState(MODULOS_BETA_PUBLICOS);
  const [modulosForaOfertaPublica, setModulosForaOfertaPublica] = useState(
    MODULOS_FORA_DA_OFERTA_PUBLICA,
  );
  const [planoAtual, setPlanoAtual] = useState(null);
  const [assinaturaAtual, setAssinaturaAtual] = useState(null);
  const [trialPadrao, setTrialPadrao] = useState(null);
  const devControlesAtivos = import.meta.env.DEV;
  const [devModulosConfig, setDevModulosConfig] = useState(() => {
    if (!devControlesAtivos) {
      return { modo: "normal", overrides: {} };
    }

    try {
      const raw = localStorage.getItem(DEV_MODULOS_STORAGE_KEY);
      if (!raw) return { modo: "normal", overrides: {} };
      const parsed = JSON.parse(raw);
      const modo = DEV_MODULOS_MODOS_VALIDOS.includes(parsed?.modo)
        ? parsed.modo
        : "normal";
      const overrides =
        parsed?.overrides && typeof parsed.overrides === "object"
          ? parsed.overrides
          : {};

      return {
        modo,
        overrides: modo === "custom" ? overrides : {},
      };
    } catch {
      return { modo: "normal", overrides: {} };
    }
  });

  const carregarModulos = useCallback(async () => {
    if (!user) {
      // Sem usuario logado: mantem estado de carregamento para evitar
      // liberar modulos premium durante a hidratacao da sessao.
      setModulosAtivos(null);
      setModulosBetaPublicos(MODULOS_BETA_PUBLICOS);
      setModulosForaOfertaPublica(MODULOS_FORA_DA_OFERTA_PUBLICA);
      setPlanoAtual(null);
      setAssinaturaAtual(null);
      setTrialPadrao(null);
      return;
    }
    const token = getAccessToken();
    const selectedTenant = localStorage.getItem("selectedTenant");
    if (!token || !selectedTenant) {
      setModulosAtivos([]);
      setModulosBetaPublicos(MODULOS_BETA_PUBLICOS);
      setModulosForaOfertaPublica(MODULOS_FORA_DA_OFERTA_PUBLICA);
      setPlanoAtual(null);
      setAssinaturaAtual(null);
      setTrialPadrao(null);
      return;
    }

    try {
      const response = await api.get("/modulos/status");
      const modulosApi = response.data?.modulos_ativos;
      const modulosBetaApi = response.data?.modulos_beta;
      const modulosForaOfertaApi = response.data?.modulos_fora_oferta_publica;

      setModulosAtivos(Array.isArray(modulosApi) ? modulosApi : []);
      setPlanoAtual(response.data?.plano || "basico");
      setAssinaturaAtual(response.data?.assinatura || null);
      setTrialPadrao(response.data?.trial_padrao || null);
      setModulosBetaPublicos(
        Array.isArray(modulosBetaApi) ? modulosBetaApi : MODULOS_BETA_PUBLICOS,
      );
      setModulosForaOfertaPublica(
        Array.isArray(modulosForaOfertaApi)
          ? modulosForaOfertaApi
          : MODULOS_FORA_DA_OFERTA_PUBLICA,
      );
    } catch {
      // Fail-closed: se não conseguir confirmar o plano, não libera premium.
      setModulosAtivos([]);
      setModulosBetaPublicos(MODULOS_BETA_PUBLICOS);
      setModulosForaOfertaPublica(MODULOS_FORA_DA_OFERTA_PUBLICA);
      setPlanoAtual(null);
      setAssinaturaAtual(null);
      setTrialPadrao(null);
    }
  }, [user]);

  useEffect(() => {
    carregarModulos();
  }, [carregarModulos]);

  useEffect(() => {
    if (!devControlesAtivos) return;
    if (devModulosConfig.modo !== "normal") return;
    if (Object.keys(devModulosConfig.overrides || {}).length === 0) return;
    setDevModulosConfig({ modo: "normal", overrides: {} });
  }, [devControlesAtivos, devModulosConfig]);

  useEffect(() => {
    if (!devControlesAtivos) return;
    localStorage.setItem(
      DEV_MODULOS_STORAGE_KEY,
      JSON.stringify(devModulosConfig),
    );
  }, [devModulosConfig, devControlesAtivos]);

  const moduloAtivoBase = useCallback(
    (modulo) => {
      if (modulosAtivos === null) return !user;
      if (!MODULOS_PREMIUM.includes(modulo)) return true;
      return modulosAtivos.includes(modulo);
    },
    [modulosAtivos, user],
  );

  const moduloAtivo = useCallback(
    (modulo) => {
      if (!MODULOS_PREMIUM.includes(modulo)) return true;

      if (devControlesAtivos) {
        if (devModulosConfig.modo === "all_unlocked") return true;
        if (devModulosConfig.modo === "all_locked") return false;

        if (
          devModulosConfig.modo === "custom" &&
          Object.prototype.hasOwnProperty.call(
            devModulosConfig.overrides,
            modulo,
          )
        ) {
          return Boolean(devModulosConfig.overrides[modulo]);
        }
      }

      return moduloAtivoBase(modulo);
    },
    [devControlesAtivos, devModulosConfig, moduloAtivoBase],
  );

  const moduloBetaPublico = useCallback(
    (modulo) => modulosBetaPublicos.includes(modulo),
    [modulosBetaPublicos],
  );

  const moduloForaOfertaPublica = useCallback(
    (modulo) => modulosForaOfertaPublica.includes(modulo),
    [modulosForaOfertaPublica],
  );

  const definirModoDevModulos = useCallback(
    (modo) => {
      if (!devControlesAtivos) return;
      if (!["normal", "all_unlocked", "all_locked"].includes(modo)) return;
      setDevModulosConfig({ modo, overrides: {} });
    },
    [devControlesAtivos],
  );

  const alternarModuloDev = useCallback(
    (modulo) => {
      if (!devControlesAtivos || !MODULOS_PREMIUM.includes(modulo)) return;

      setDevModulosConfig((prev) => {
        const baseAtivo = moduloAtivoBase(modulo);
        const overrides = { ...prev.overrides };

        const atualModoNormal = Object.prototype.hasOwnProperty.call(
          overrides,
          modulo,
        )
          ? Boolean(overrides[modulo])
          : baseAtivo;
        const proximo = !atualModoNormal;

        if (proximo === baseAtivo) {
          delete overrides[modulo];
        } else {
          overrides[modulo] = proximo;
        }

        return {
          modo: Object.keys(overrides).length > 0 ? "custom" : "normal",
          overrides,
        };
      });
    },
    [devControlesAtivos, moduloAtivoBase],
  );

  const value = useMemo(
    () => ({
      modulosAtivos,
      planoAtual,
      assinaturaAtual,
      trialPadrao,
      modulosBetaPublicos,
      modulosForaOfertaPublica,
      moduloAtivo,
      moduloBetaPublico,
      moduloForaOfertaPublica,
      carregarModulos,
      devControlesAtivos,
      devModoModulos: devModulosConfig.modo,
      definirModoDevModulos,
      alternarModuloDev,
    }),
    [
      modulosAtivos,
      planoAtual,
      assinaturaAtual,
      trialPadrao,
      modulosBetaPublicos,
      modulosForaOfertaPublica,
      moduloAtivo,
      moduloBetaPublico,
      moduloForaOfertaPublica,
      carregarModulos,
      devControlesAtivos,
      devModulosConfig.modo,
      definirModoDevModulos,
      alternarModuloDev,
    ],
  );

  return (
    <ModulosContext.Provider value={value}>{children}</ModulosContext.Provider>
  );
};

export const useModulos = () => {
  const context = useContext(ModulosContext);
  if (!context) {
    throw new Error("useModulos deve ser usado dentro de ModulosProvider");
  }
  return context;
};
