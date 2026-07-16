import { PawPrint, Scissors, Stethoscope } from "lucide-react";
import {
  FiBell,
  FiBox,
  FiBriefcase,
  FiCpu,
  FiDollarSign,
  FiFileText,
  FiGift,
  FiGlobe,
  FiHome,
  FiPackage,
  FiSettings,
  FiShield,
  FiShoppingBag,
  FiShoppingCart,
  FiTarget,
  FiTrendingUp,
  FiTruck,
  FiUsers,
} from "react-icons/fi";
import { applyLayoutMenuStructure } from "./menuStructure.js";

export function createLayoutMenuItems({ lembretesCount = 0 } = {}) {
  const items = [
    {
      path: "/dashboard",
      icon: FiHome,
      iconKey: "home",
      label: "Dashboard",
      permission: "relatorios.gerencial",
    }, // Precisa de permissão
    {
      path: "/clientes",
      icon: FiUsers,
      iconKey: "users",
      label: "Pessoas",
      permission: "clientes.visualizar",
    },
    {
      path: "/pets",
      icon: PawPrint,
      iconKey: "paw-print",
      label: "Pets",
      highlight: true,
      permission: "clientes.visualizar",
    }, // Vinculado a clientes
    {
      path: "/veterinario",
      icon: Stethoscope,
      iconKey: "stethoscope",
      label: "Veterinário",
      highlight: true,
      modulo: "veterinario",
      permission: null,
      submenu: [
        {
          path: "/veterinario",
          label: "Dashboard",
          permission: null,
        },
        {
          path: "/veterinario/agenda",
          label: "Agenda",
          permission: null,
        },
        {
          path: "/veterinario/consultas",
          label: "Consultas / Prontuário",
          permission: null,
        },
        {
          path: "/veterinario/exames",
          label: "Exames Anexados",
          permission: null,
        },
        {
          path: "/veterinario/ia",
          label: "Assistente IA Vet",
          permission: null,
        },
        {
          path: "/veterinario/calculadora-doses",
          label: "Calculadora de Doses",
          permission: null,
        },
        {
          path: "/veterinario/vacinas",
          label: "Vacinas",
          permission: null,
        },
        {
          path: "/veterinario/internacoes",
          label: "Internações",
          permission: null,
        },
        {
          path: "/veterinario/catalogo",
          label: "Catálogos",
          permission: null,
        },
        {
          path: "/veterinario/repasse",
          label: "Repasse Parceiro",
          permission: null,
        },
        {
          path: "/veterinario/configuracoes",
          label: "Configurações Vet",
          permission: null,
        },
      ],
    },
    {
      path: "/banho-tosa",
      icon: Scissors,
      iconKey: "scissors",
      label: "Banho & Tosa",
      highlight: true,
      modulo: "banho_tosa",
      permission: null,
      submenu: [
        {
          path: "/banho-tosa",
          label: "Dashboard",
          permission: null,
        },
        {
          path: "/banho-tosa/servicos",
          label: "Servicos",
          permission: null,
        },
        {
          path: "/banho-tosa/parametros",
          label: "Parametros",
          permission: null,
        },
        {
          path: "/banho-tosa/recursos",
          label: "Recursos",
          permission: null,
        },
        {
          path: "/banho-tosa/agenda",
          label: "Agenda",
          permission: null,
        },
        {
          path: "/banho-tosa/fila",
          label: "Fila do dia",
          permission: null,
        },
        {
          path: "/banho-tosa/pacotes",
          label: "Pacotes",
          permission: null,
        },
        {
          path: "/banho-tosa/retornos",
          label: "Reagendar",
          permission: null,
        },
        {
          path: "/banho-tosa/taxi-dog",
          label: "Taxi dog",
          permission: null,
        },
        {
          path: "/banho-tosa/relatorios",
          label: "Relatorios",
          permission: null,
        },
      ],
    },
    {
      path: "/produtos",
      icon: FiPackage,
      iconKey: "package",
      label: "Produtos / Estoque",
      permission: "produtos.visualizar",
      submenu: [
        {
          path: "/produtos",
          label: "Listar Produtos",
          permission: "produtos.visualizar",
        },
        {
          path: "/produtos/relatorio",
          label: "Relatório de Movimentações",
          permission: "produtos.visualizar",
        },
        {
          path: "/produtos/valorizacao-estoque",
          label: "Valorizacao de Estoque",
          permission: "produtos.visualizar",
        },
        {
          path: "/produtos/balanco",
          label: "Balanço",
          permission: "produtos.editar",
        },
        {
          path: "/estoque/alertas",
          label: "Alertas de Estoque",
          permission: "produtos.visualizar",
        },
        {
          path: "/estoque/full-nf",
          label: "Movimentacao Full por NF",
          permission: "produtos.editar",
        },
        {
          path: "/estoque/transferencia-parceiro",
          label: "Transferencia Parceiro",
          permission: "produtos.editar",
        },
        {
          path: "/produtos/sinc-bling",
          label: "Sinc. Bling",
          modulo: "bling",
          permission: "compras.sincronizacao_bling",
        },
      ],
    },
    {
      path: "/lembretes",
      icon: FiBell,
      iconKey: "bell",
      label: "Lembretes",
      badge: lembretesCount > 0,
      permission: null,
    }, // Sempre visível
    {
      path: "/calculadora-racao",
      icon: FiTarget,
      iconKey: "target",
      label: "Calculadora de Ração",
      permission: "produtos.visualizar",
    },
    {
      path: "/pdv",
      icon: FiShoppingCart,
      iconKey: "shopping-cart",
      label: "PDV (Vendas)",
      permission: "vendas.criar",
    },
    {
      path: "/campanhas",
      icon: FiGift,
      iconKey: "gift",
      label: "Campanhas",
      modulo: "campanhas",
      permission: "vendas.criar",
    },
    {
      path: "/ecommerce",
      icon: FiGlobe,
      iconKey: "globe",
      label: "E-commerce",
      modulo: "ecommerce",
      permission: "vendas.visualizar",
      submenu: [
        {
          path: "/ecommerce",
          label: "🏪 Prévia da Loja",
          permission: "vendas.visualizar",
        },
        {
          path: "/ecommerce/aparencia",
          label: "🖼️ Aparência da Loja",
          permission: "vendas.visualizar",
        },
        {
          path: "/ecommerce/configuracoes",
          label: "⚙️ Configurações",
          permission: "vendas.visualizar",
        },
        {
          path: "/ecommerce/analytics",
          label: "📊 Analytics",
          permission: "vendas.visualizar",
        },
      ],
    },
    {
      path: "/vendas/bling",
      icon: FiShoppingBag,
      iconKey: "shopping-bag",
      label: "Bling",
      modulo: "bling",
      permission: "compras.sincronizacao_bling",
      submenu: [
        {
          path: "/vendas/bling-pedidos",
          label: "Pedidos Bling",
          permission: "compras.sincronizacao_bling",
        },
        {
          path: "/vendas/bling-monitor",
          label: "Monitor da Integração",
          permission: "compras.sincronizacao_bling",
        },
      ],
    },
    {
      path: "/notas-fiscais/saida",
      icon: FiFileText,
      iconKey: "file-text",
      label: "NF de Saída",
      modulo: "fiscal",
      permission: "vendas.visualizar",
    },
    {
      path: "/compras",
      icon: FiBox,
      iconKey: "box",
      label: "Compras",
      modulo: "compras",
      permission: "compras.gerenciar",
      submenu: [
        {
          path: "/compras/pedidos",
          label: "Pedidos de Compra",
          permission: "compras.pedidos",
        },
        {
          path: "/compras/entrada-xml",
          label: "Central NF-e Entradas",
          permission: "compras.entrada_xml",
        },
        {
          path: "/compras/pendencias",
          label: "Pendencias",
          permission: "compras.gerenciar",
        },
      ],
    },
    {
      path: "/financeiro",
      icon: FiTrendingUp,
      iconKey: "trending-up",
      label: "Financeiro",
      permission: "relatorios.financeiro",
      anyOfPermissions: [
        "relatorios.financeiro",
        "financeiro.vendas",
        "clientes.visualizar",
        "vendas.criar",
      ],
      submenu: [
        {
          path: "/financeiro",
          label: "Dashboard",
          modulo: "financeiro_erp",
          permission: "financeiro.dashboard",
        },
        {
          path: "/financeiro/vendas",
          label: "Vendas",
          permission: "financeiro.vendas",
          anyOfPermissions: [
            "relatorios.financeiro",
            "financeiro.vendas",
            "clientes.visualizar",
            "vendas.criar",
          ],
        },
        {
          path: "/financeiro/fluxo-caixa",
          label: "Fluxo de Caixa",
          modulo: "financeiro_erp",
          permission: "financeiro.fluxo_caixa",
        },
        {
          path: "/financeiro/bancos",
          label: "Bancos",
          modulo: "financeiro_erp",
          permission: "financeiro.fluxo_caixa",
        },
        {
          path: "/financeiro/dre",
          label: "DRE",
          modulo: "financeiro_erp",
          permission: "financeiro.dre",
        },
        {
          path: "/financeiro/ponto-equilibrio",
          label: "Ponto de Equilibrio",
          modulo: "financeiro_erp",
          permission: "relatorios.financeiro",
        },
        {
          path: "/financeiro/imobilizado",
          label: "Imobilizado",
          modulo: "financeiro_erp",
          permission: "relatorios.financeiro",
        },
        {
          path: "/financeiro/valor-empresa",
          label: "Valor da Empresa",
          modulo: "financeiro_erp",
          permission: "relatorios.financeiro",
        },
        {
          path: "/financeiro/contas-pagar",
          label: "Contas a Pagar",
          modulo: "financeiro_erp",
          permission: "financeiro.contas_pagar",
        },
        {
          path: "/financeiro/contas-receber",
          label: "Contas a Receber",
          modulo: "financeiro_erp",
          permission: "financeiro.contas_receber",
        },
        {
          path: "/financeiro/conciliacao-bancaria",
          label: "Conciliação Bancária",
          modulo: "financeiro_erp",
          permission: "financeiro.conciliacao_bancaria",
        },
        {
          path: "/financeiro/conciliacao-3abas",
          label: "Conciliação 3 Abas",
          highlight: true,
          modulo: "financeiro_erp",
          permission: "financeiro.conciliacao_cartao",
        },
      ],
    },
    {
      path: "/comissoes",
      icon: FiDollarSign,
      iconKey: "dollar-sign",
      label: "Comissões",
      modulo: "comissoes",
      permission: "relatorios.financeiro", // Vinculado a relatórios financeiros
      submenu: [
        {
          path: "/comissoes",
          label: "Configuração",
          permission: "comissoes.configurar",
        },
        {
          path: "/comissoes/demonstrativo",
          label: "Demonstrativo",
          permission: "comissoes.demonstrativo",
        },
        {
          path: "/comissoes/abertas",
          label: "Comissões em Aberto",
          permission: "comissoes.abertas",
        },
        {
          path: "/comissoes/fechamentos",
          label: "Histórico de Fechamentos",
          permission: "comissoes.fechamentos",
        },
        {
          path: "/comissoes/relatorios",
          label: "📊 Relatórios Analíticos",
          permission: "comissoes.relatorios",
        },
      ],
    },
    {
      path: "/entregas",
      icon: FiTruck,
      iconKey: "truck",
      label: "Entregas",
      modulo: "entregas",
      permission: "vendas.visualizar", // Vinculado a vendas
      submenu: [
        {
          path: "/entregas/abertas",
          label: "Entregas em Aberto",
          permission: "entregas.abertas",
        },
        {
          path: "/entregas/rotas",
          label: "Rotas de Entrega",
          permission: "entregas.rotas",
        },
        {
          path: "/entregas/historico",
          label: "📜 Histórico",
          permission: "entregas.historico",
        },
        {
          path: "/entregas/financeiro",
          label: "📊 Dashboard Financeiro",
          permission: "entregas.dashboard",
        },
      ],
    },
    {
      path: "/cadastros",
      icon: FiSettings,
      iconKey: "settings",
      label: "Cadastros",
      permission: "configuracoes.editar", // Vinculado a configurações
      submenu: [
        {
          path: "/cadastros/cargos",
          label: "Cargos",
          modulo: "rh",
          permission: "cadastros.cargos",
        },
        {
          path: "/cadastros/departamentos",
          label: "Departamentos",
          permission: "cadastros.categorias_produtos",
        },
        {
          path: "/cadastros/marcas",
          label: "Marcas",
          permission: "cadastros.categorias_produtos",
        },
        {
          path: "/cadastros/categorias",
          label: "Categorias de Produtos",
          permission: "cadastros.categorias_produtos",
        },
        {
          path: "/cadastros/categorias-financeiras",
          label: "Categorias Financeiras",
          modulo: "financeiro_erp",
          permission: "cadastros.categorias_financeiras",
        },
        {
          path: "/cadastros/despesas-rapidas",
          label: "Despesas Rápidas (PDV)",
          permission: "cadastros.categorias_financeiras",
        },
        {
          path: "/cadastros/especies-racas",
          label: "Espécies e Raças",
          permission: "cadastros.especies_racas",
        },
        {
          path: "/cadastros/opcoes-racao",
          label: "Opções de Ração",
          permission: "produtos.editar",
        },
        {
          path: "/cadastros/financeiro/bancos",
          label: "Bancos",
          modulo: "financeiro_erp",
          permission: "cadastros.bancos",
        },
        {
          path: "/cadastros/financeiro/formas-pagamento",
          label: "Formas de Pagamento",
          permission: "cadastros.formas_pagamento",
        },
        {
          path: "/cadastros/financeiro/operadoras",
          label: "Operadoras de Cartão",
          permission: "cadastros.operadoras",
        },
      ],
    },
    {
      path: "/rh",
      icon: FiBriefcase,
      iconKey: "briefcase",
      label: "Recursos Humanos",
      modulo: "rh",
      permission: "usuarios.manage", // Vinculado a gerenciar usuários
      submenu: [
        {
          path: "/rh/funcionarios",
          label: "Funcionários",
          permission: "rh.funcionarios",
        },
      ],
    },
    {
      path: "/ia",
      icon: FiCpu,
      iconKey: "cpu",
      label: "Inteligência Artificial",
      permission: null, // Menu principal sempre visível
      submenu: [
        { path: "/ia/chat", label: "Chat IA", modulo: "financeiro_erp", permission: null },
        {
          path: "/ia/fluxo-caixa",
          label: "Fluxo de Caixa Preditivo",
          modulo: "financeiro_erp",
          permission: "ia.fluxo_caixa",
        },
        {
          path: "/ia/whatsapp",
          label: "Bot WhatsApp",
          modulo: "whatsapp",
          permission: "ia.whatsapp",
        },
        {
          path: "/ia/alertas-racao",
          label: "Comparador de Racoes",
          permission: "produtos.editar",
        },
      ],
    },
    {
      path: "/admin",
      icon: FiShield,
      iconKey: "shield",
      label: "Administração",
      permission: "usuarios.manage",
      submenu: [
        {
          path: "/admin/usuarios",
          label: "Usuários",
          permission: "usuarios.manage",
        },
        {
          path: "/admin/roles",
          label: "Roles & Permissões",
          permission: "usuarios.manage",
        },
        {
          path: "/admin/lgpd",
          label: "LGPD e Privacidade",
          permission: "usuarios.manage",
        },
      ],
    },
    {
      path: "/configuracoes",
      icon: FiSettings,
      iconKey: "settings",
      label: "Configurações",
      permission: "configuracoes.editar",
      submenu: [
        {
          path: "/configuracoes/fiscal",
          label: "Configuração da Empresa",
          permission: "configuracoes.empresa",
        },
        {
          path: "/configuracoes/geral",
          label: "Parâmetros Gerais",
          permission: "configuracoes.editar",
        },
        {
          path: "/configuracoes/entregas",
          label: "Entregas",
          modulo: "entregas",
          permission: "configuracoes.entregas",
        },
        {
          path: "/configuracoes/custos-moto",
          label: "Custos da Moto",
          modulo: "entregas",
          permission: "configuracoes.custos_moto",
        },
        { path: "/configuracoes/estoque", label: "Estoque" },
        { path: "/configuracoes/integracoes", label: "Integrações", modulo: "integracoes" },
      ],
    },
  ];

  return applyLayoutMenuStructure(items);
}
