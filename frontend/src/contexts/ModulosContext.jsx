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
import { useAuth } from "./AuthContext";

const ModulosContext = createContext();
const DEV_MODULOS_STORAGE_KEY = "dev_modulos_config";

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
  const devControlesAtivos = import.meta.env.DEV;
  const [devModulosConfig, setDevModulosConfig] = useState(() => {
    if (!devControlesAtivos) {
      return { modo: "normal", overrides: {} };
    }

    try {
      const raw = localStorage.getItem(DEV_MODULOS_STORAGE_KEY);
      if (!raw) return { modo: "normal", overrides: {} };
      const parsed = JSON.parse(raw);
      return {
        modo:
          parsed?.modo === "all_unlocked" || parsed?.modo === "all_locked"
            ? parsed.modo
            : "normal",
        overrides:
          parsed?.overrides && typeof parsed.overrides === "object"
            ? parsed.overrides
            : {},
      };
    } catch {
      return { modo: "normal", overrides: {} };
    }
  });

  const carregarModulos = useCallback(async () => {
    if (!user) {
      // Sem usuário logado: libera tudo para não bloquear tela de loading
      setModulosAtivos(MODULOS_PREMIUM);
      return;
    }
    const token = localStorage.getItem("access_token") || localStorage.getItem("token");
    const selectedTenant = localStorage.getItem("selectedTenant");
    if (!token || !selectedTenant) {
      setModulosAtivos(MODULOS_PREMIUM);
      return;
    }

    try {
      const response = await api.get("/modulos/status");
      const modulosApi = response.data?.modulos_ativos;
      setModulosAtivos(Array.isArray(modulosApi) ? modulosApi : MODULOS_PREMIUM);
    } catch {
      // Se o endpoint não existir ainda (deploy incremental), libera tudo
      setModulosAtivos(MODULOS_PREMIUM); // todos ativos = sem bloqueio
    }
  }, [user]);

  useEffect(() => {
    carregarModulos();
  }, [carregarModulos]);

  useEffect(() => {
    if (!devControlesAtivos) return;
    localStorage.setItem(
      DEV_MODULOS_STORAGE_KEY,
      JSON.stringify(devModulosConfig),
    );
  }, [devModulosConfig, devControlesAtivos]);

  const moduloAtivoBase = useCallback(
    (modulo) => {
      if (modulosAtivos === null) return true;
      if (!MODULOS_PREMIUM.includes(modulo)) return true;
      return modulosAtivos.includes(modulo);
    },
    [modulosAtivos],
  );

  const moduloAtivo = useCallback(
    (modulo) => {
      if (!MODULOS_PREMIUM.includes(modulo)) return true;

      if (devControlesAtivos) {
        if (devModulosConfig.modo === "all_unlocked") return true;
        if (devModulosConfig.modo === "all_locked") return false;

        if (
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

  const definirModoDevModulos = useCallback(
    (modo) => {
      if (!devControlesAtivos) return;
      if (!["normal", "all_unlocked", "all_locked"].includes(modo)) return;
      setDevModulosConfig((prev) => ({ ...prev, modo }));
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
          modo: "normal",
          overrides,
        };
      });
    },
    [devControlesAtivos, moduloAtivoBase],
  );

  const value = useMemo(
    () => ({
      modulosAtivos,
      moduloAtivo,
      carregarModulos,
      devControlesAtivos,
      devModoModulos: devModulosConfig.modo,
      definirModoDevModulos,
      alternarModuloDev,
    }),
    [
      modulosAtivos,
      moduloAtivo,
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
