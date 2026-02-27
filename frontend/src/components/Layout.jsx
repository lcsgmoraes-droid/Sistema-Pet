import { useState, useEffect, useRef } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  FiHome, FiUsers, FiPackage, FiShoppingCart, FiDollarSign,
  FiBarChart2, FiSettings, FiLogOut, FiMenu, FiX,
  FiBox, FiTrendingUp, FiFileText, FiChevronDown, FiChevronRight,
  FiCpu, FiBell, FiTarget, FiBriefcase, FiTruck, FiShield, FiAlertTriangle
} from 'react-icons/fi';
import { PawPrint } from 'lucide-react';
import FloatingCalculatorButton from './FloatingCalculatorButton';
import ModalCalculadoraUniversal from './ModalCalculadoraUniversal';

const Layout = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  
  // Estado para detectar mobile
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  
  // Detectar mudanças no tamanho da tela
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  // Função para verificar se o usuário tem permissão
  const hasPermission = (permission) => {
    if (!user) return false;
    
    // Admins têm acesso a tudo (qualquer variação do nome do role admin)
    const adminRoles = ['admin', 'Admin', 'Administrador', 'administrador', 'ADMIN'];
    if (adminRoles.includes(user.role?.name)) {
      return true;
    }
    
    // Se não tem array de permissões, nega acesso
    if (!user.permissions || !Array.isArray(user.permissions)) {
      return false;
    }
    
    // Verifica se a permissão específica existe
    const hasAccess = user.permissions.includes(permission);
    return hasAccess;
  };
  
  // Estado da sidebar com persistência e fechada por padrão no PDV
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    // Em mobile, sempre começa fechada
    if (window.innerWidth < 768) return false;
    
    const saved = localStorage.getItem('sidebar_open');
    if (saved !== null) {
      return JSON.parse(saved);
    }
    // Se não tem preferência salva, fecha no PDV por padrão
    return location.pathname !== '/pdv';
  });
  
  const [submenusOpen, setSubmenusOpen] = useState({});

  // Estado para esconder completamente a sidebar
  const [sidebarVisible, setSidebarVisible] = useState(() => {
    const saved = localStorage.getItem('sidebar_visible');
    return saved !== null ? JSON.parse(saved) : true;
  });

  // Estado da calculadora universal
  const [calculadoraAberta, setCalculadoraAberta] = useState(false);
  const [telaBloqueadaSuspeita, setTelaBloqueadaSuspeita] = useState(false);
  const overlaySuspeitoDesdeRef = useRef(new Map());

  const neutralizarOverlay = (elementoOverlay) => {
    if (!elementoOverlay) return;

    elementoOverlay.style.pointerEvents = 'none';
    elementoOverlay.style.backgroundColor = 'transparent';
    elementoOverlay.style.opacity = '0';
    elementoOverlay.style.transition = 'opacity 120ms ease';

    window.setTimeout(() => {
      if (elementoOverlay.parentNode) {
        elementoOverlay.remove();
      }
    }, 140);
  };

  const ehOverlayTelaCheia = (elementoOverlay) => {
    const estilo = window.getComputedStyle(elementoOverlay);
    const larguraTelaCheia = elementoOverlay.offsetWidth >= (window.innerWidth - 8);
    const alturaTelaCheia = elementoOverlay.offsetHeight >= (window.innerHeight - 8);
    const zIndex = Number.parseInt(estilo.zIndex || '0', 10);

    return (
      estilo.position === 'fixed' &&
      larguraTelaCheia &&
      alturaTelaCheia &&
      zIndex >= 40
    );
  };

  const encontrarOverlaysOrfaos = () => {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return [];
    }

    const overlays = Array.from(document.querySelectorAll('div.fixed.inset-0'));

    return overlays.filter((elementoOverlay) => {
      if (!ehOverlayTelaCheia(elementoOverlay)) {
        return false;
      }

      const classes = elementoOverlay.className || '';
      if (typeof classes === 'string' && classes.includes('bg-transparent')) {
        return false;
      }

      const estilo = window.getComputedStyle(elementoOverlay);
      const visivel = estilo.display !== 'none' && estilo.visibility !== 'hidden';
      const bloqueiaClique = estilo.pointerEvents !== 'none';
      const fundoAtivo = estilo.backgroundColor && estilo.backgroundColor !== 'rgba(0, 0, 0, 0)' && estilo.backgroundColor !== 'transparent';
      const possuiSpinner = Boolean(elementoOverlay.querySelector('.animate-spin'));
      const overlayCalculadora = elementoOverlay.getAttribute('data-overlay-type') === 'calculadora-universal';
      const overlaySemConteudo = (elementoOverlay.textContent || '').trim().length === 0;

      if (!visivel || !bloqueiaClique) {
        return false;
      }

      const possuiConteudoModal = Boolean(
        elementoOverlay.querySelector('[role="dialog"], .bg-white, .rounded-lg, .rounded-xl, .shadow-2xl, .shadow-xl')
      );

      if (overlayCalculadora && !calculadoraAberta) {
        return true;
      }

      return !possuiConteudoModal && (fundoAtivo || possuiSpinner || overlaySemConteudo);
    });
  };

  const destravarTela = (silencioso = false) => {
    setSidebarOpen(false);
    setCalculadoraAberta(false);

    const eventoEscape = new KeyboardEvent('keydown', { key: 'Escape' });
    window.dispatchEvent(eventoEscape);

    const overlaysOrfaos = encontrarOverlaysOrfaos();
    overlaysOrfaos.forEach((elementoOverlay) => neutralizarOverlay(elementoOverlay));

    overlaySuspeitoDesdeRef.current.clear();
    if (!silencioso) {
      setTelaBloqueadaSuspeita(false);
    }
  };

  // Fechar sidebar em mobile ao clicar em um link
  const handleMenuClick = () => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  };
  
  // Persistir estado da sidebar no localStorage (apenas desktop)
  useEffect(() => {
    if (!isMobile) {
      localStorage.setItem('sidebar_open', JSON.stringify(sidebarOpen));
    }
  }, [sidebarOpen, isMobile]);

  useEffect(() => {
    if (!isMobile) {
      localStorage.setItem('sidebar_visible', JSON.stringify(sidebarVisible));
    }
  }, [sidebarVisible, isMobile]);
  
  // Fechar menu mobile ao mudar de rota
  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [location.pathname, isMobile]);

  useEffect(() => {
    if (isMobile && sidebarOpen) {
      setSidebarOpen(false);
    }
  }, [isMobile, sidebarOpen]);

  useEffect(() => {
    setCalculadoraAberta(false);
  }, [location.pathname]);

  useEffect(() => {
    const verificarTelaBloqueada = () => {
      const overlaysOrfaos = encontrarOverlaysOrfaos();
      const agora = Date.now();

      const mapeamentoAtual = overlaySuspeitoDesdeRef.current;
      let precisaDestravarAutomaticamente = false;

      const overlaysSet = new Set(overlaysOrfaos);
      for (const elemento of Array.from(mapeamentoAtual.keys())) {
        if (!overlaysSet.has(elemento)) {
          mapeamentoAtual.delete(elemento);
        }
      }

      overlaysOrfaos.forEach((elementoOverlay) => {
        const vistoDesde = mapeamentoAtual.get(elementoOverlay) || agora;
        mapeamentoAtual.set(elementoOverlay, vistoDesde);

        const overlayCalculadora = elementoOverlay.getAttribute('data-overlay-type') === 'calculadora-universal';
        const limiteMs = overlayCalculadora ? 900 : 1800;

        if (agora - vistoDesde >= limiteMs) {
          precisaDestravarAutomaticamente = true;
          neutralizarOverlay(elementoOverlay);
        }
      });

      setTelaBloqueadaSuspeita(overlaysOrfaos.length > 0);

      if (precisaDestravarAutomaticamente) {
        destravarTela(true);
      }
    };

    verificarTelaBloqueada();
    const intervalId = window.setInterval(verificarTelaBloqueada, 1000);
    const observer = new MutationObserver(() => verificarTelaBloqueada());
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      window.clearInterval(intervalId);
      observer.disconnect();
    };
  }, [calculadoraAberta]);

  const allMenuItems = [
    { path: '/dashboard', icon: FiHome, label: 'Dashboard', permission: 'relatorios.gerencial' }, // Precisa de permissão
    { path: '/dashboard-gerencial', icon: FiBarChart2, label: '📊 Dashboard Gerencial', highlight: true, permission: 'relatorios.gerencial' },
    { path: '/clientes', icon: FiUsers, label: 'Pessoas', permission: 'clientes.visualizar' },
    { path: '/pets', icon: PawPrint, label: '🐾 Pets', highlight: true, permission: 'clientes.visualizar' }, // Vinculado a clientes
    { 
      path: '/produtos', 
      icon: FiPackage, 
      label: 'Produtos', 
      permission: 'produtos.visualizar',
      submenu: [
        { path: '/produtos', label: 'Listar Produtos', permission: 'produtos.visualizar' },
        { path: '/produtos/relatorio', label: 'Relatório de Movimentações', permission: 'produtos.visualizar' },
        { path: '/estoque/alertas', label: 'Alertas de Estoque', permission: 'produtos.visualizar' },
      ]
    },
    { path: '/lembretes', icon: FiBell, label: 'Lembretes', badge: true, permission: null }, // Sempre visível
    { path: '/calculadora-racao', icon: FiTarget, label: 'Calculadora de Ração', permission: null }, // Sempre visível
    { path: '/pdv', icon: FiShoppingCart, label: 'PDV (Vendas)', permission: 'vendas.criar' },
    {
      path: '/ecommerce',
      icon: FiShoppingCart,
      label: 'E-commerce',
      permission: 'vendas.visualizar',
      submenu: [
        { path: '/ecommerce', label: '🏪 Prévia da Loja', permission: 'vendas.visualizar' },
        { path: '/ecommerce/aparencia', label: '🖼️ Aparência da Loja', permission: 'vendas.visualizar' },
      ],
    },
    { path: '/notas-fiscais', icon: FiFileText, label: 'Notas Fiscais', permission: 'vendas.visualizar' }, // Vinculado a vendas
    { 
      path: '/compras', 
      icon: FiBox, 
      label: 'Compras',
      permission: 'compras.gerenciar',
      submenu: [
        { path: '/compras/pedidos', label: 'Pedidos de Compra', permission: 'compras.pedidos' },
        { path: '/compras/entrada-xml', label: 'Entrada por XML', permission: 'compras.entrada_xml' },
        { path: '/compras/bling', label: 'Sinc. Bling', permission: 'compras.sincronizacao_bling' },
      ]
    },
    { 
      path: '/financeiro', 
      icon: FiTrendingUp, 
      label: 'Financeiro/Contábil',
      permission: 'relatorios.financeiro',
      submenu: [
        { path: '/financeiro', label: 'Dashboard', permission: 'financeiro.dashboard' },
        { path: '/financeiro/vendas', label: 'Vendas', permission: 'financeiro.vendas' },
        { path: '/financeiro/fluxo-caixa', label: 'Fluxo de Caixa', permission: 'financeiro.fluxo_caixa' },
        { path: '/financeiro/dre', label: 'DRE', permission: 'financeiro.dre' },
        { path: '/financeiro/contas-pagar', label: 'Contas a Pagar', permission: 'financeiro.contas_pagar' },
        { path: '/financeiro/contas-receber', label: 'Contas a Receber', permission: 'financeiro.contas_receber' },
        { path: '/financeiro/conciliacao-bancaria', label: 'Conciliação Bancária', permission: 'financeiro.conciliacao_bancaria' },
        { path: '/financeiro/conciliacao-3abas', label: 'Conciliação 3 Abas', highlight: true, permission: 'financeiro.conciliacao_cartao' },
      ]
    },
    { 
      path: '/comissoes', 
      icon: FiDollarSign, 
      label: 'Comissões',
      permission: 'relatorios.financeiro', // Vinculado a relatórios financeiros
      submenu: [
        { path: '/comissoes', label: 'Configuração', permission: 'comissoes.configurar' },
        { path: '/comissoes/demonstrativo', label: 'Demonstrativo', permission: 'comissoes.demonstrativo' },
        { path: '/comissoes/abertas', label: 'Comissões em Aberto', permission: 'comissoes.abertas' },
        { path: '/comissoes/fechamentos', label: 'Histórico de Fechamentos', permission: 'comissoes.fechamentos' },
        { path: '/comissoes/relatorios', label: '📊 Relatórios Analíticos', permission: 'comissoes.relatorios' },
      ]
    },
    { 
      path: '/entregas', 
      icon: FiTruck, 
      label: 'Entregas',
      permission: 'vendas.visualizar', // Vinculado a vendas
      submenu: [
        { path: '/entregas/abertas', label: 'Entregas em Aberto', permission: 'entregas.abertas' },
        { path: '/entregas/rotas', label: 'Rotas de Entrega', permission: 'entregas.rotas' },
        { path: '/entregas/historico', label: '📜 Histórico', permission: 'entregas.historico' },
        { path: '/entregas/financeiro', label: '📊 Dashboard Financeiro', permission: 'entregas.dashboard' },
      ]
    },
    { 
      path: '/cadastros', 
      icon: FiSettings, 
      label: 'Cadastros',
      permission: 'configuracoes.editar', // Vinculado a configurações
      submenu: [
        { path: '/cadastros/cargos', label: 'Cargos', permission: 'cadastros.cargos' },
        { path: '/cadastros/categorias', label: 'Categorias de Produtos', permission: 'cadastros.categorias_produtos' },
        { path: '/cadastros/categorias-financeiras', label: 'Categorias Financeiras', permission: 'cadastros.categorias_financeiras' },
        { path: '/cadastros/especies-racas', label: 'Espécies e Raças', permission: 'cadastros.especies_racas' },
        { path: '/cadastros/opcoes-racao', label: 'Opções de Ração', permission: 'produtos.editar' },
        { path: '/cadastros/financeiro/bancos', label: 'Bancos', permission: 'cadastros.bancos' },
        { path: '/cadastros/financeiro/formas-pagamento', label: 'Formas de Pagamento', permission: 'cadastros.formas_pagamento' },
        { path: '/cadastros/financeiro/operadoras', label: 'Operadoras de Cartão', permission: 'cadastros.operadoras' },
      ]
    },
    { 
      path: '/rh', 
      icon: FiBriefcase, 
      label: 'Recursos Humanos',
      permission: 'usuarios.manage', // Vinculado a gerenciar usuários
      submenu: [
        { path: '/rh/funcionarios', label: 'Funcionários', permission: 'rh.funcionarios' },
      ]
    },
    { 
      path: '/ia', 
      icon: FiCpu, 
      label: 'Inteligência Artificial',
      permission: null, // Menu principal sempre visível
      submenu: [
        { path: '/ia/chat', label: 'Chat IA', permission: null }, // Sempre disponível
        { path: '/ia/fluxo-caixa', label: 'Fluxo de Caixa Preditivo', permission: 'ia.fluxo_caixa' },
        { path: '/ia/whatsapp', label: 'Bot WhatsApp', permission: 'ia.whatsapp' },
        { path: '/ia/alertas-racao', label: '⚠ Alertas Rações', permission: 'produtos.editar' },
      ]
    },
    { 
      path: '/admin', 
      icon: FiShield, 
      label: 'Administração',
      permission: 'usuarios.manage',
      submenu: [
        { path: '/admin/usuarios', label: 'Usuários', permission: 'usuarios.manage' },
        { path: '/admin/roles', label: 'Roles & Permissões', permission: 'usuarios.manage' },
      ]
    },
    { 
      path: '/configuracoes', 
      icon: FiSettings, 
      label: 'Configurações',
      permission: 'configuracoes.editar',
      submenu: [
        { path: '/configuracoes/fiscal', label: 'Configuração da Empresa', permission: 'configuracoes.empresa' },
        { path: '/configuracoes/entregas', label: 'Entregas', permission: 'configuracoes.entregas' },
        { path: '/configuracoes/custos-moto', label: 'Custos da Moto', permission: 'configuracoes.custos_moto' },
        { path: '/configuracoes/estoque', label: 'Estoque' },
        { path: '/configuracoes/simples/fechamento', label: 'Fechamento Mensal', permission: 'configuracoes.fechamento_mensal' },
      ]
    },
  ];

  // Filtrar menus baseado nas permissões do usuário
  const menuItems = allMenuItems.filter(item => {
    // Se tem submenu, filtrar os itens do submenu por permissão PRIMEIRO
    if (item.submenu && Array.isArray(item.submenu)) {
      const submenuFiltrado = item.submenu.filter(subitem => {
        // Se subitem não tem permissão, é sempre visível
        if (!subitem.permission) return true;
        // Verifica se usuário tem a permissão
        return hasPermission(subitem.permission);
      });
      // Se o submenu ficou vazio após filtrar, não mostra o menu principal
      if (submenuFiltrado.length === 0) return false;
      // Atualiza o submenu com apenas itens permitidos
      item.submenu = submenuFiltrado;
    }
    
    // Se não tem permissão definida no menu principal, item é sempre visível
    if (!item.permission) {
      return true;
    }
    
    // Verifica se usuário tem a permissão do menu principal
    return hasPermission(item.permission);
  });

  const isActive = (path) => location.pathname === path;

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Backdrop para mobile */}
      {isMobile && sidebarOpen && sidebarVisible && (
        <div 
          className="fixed inset-0 bg-transparent z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      {sidebarVisible && (
        <aside 
          className={`${
            isMobile 
              ? `fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ${
                  sidebarOpen ? 'translate-x-0' : '-translate-x-full'
                }`
              : `${sidebarOpen ? 'w-64' : 'w-20'} transition-all duration-300`
          } bg-gradient-to-b from-indigo-50 to-purple-50 border-r border-indigo-100 flex flex-col shadow-lg`}
        >
        {/* Logo/Header com Toggle */}
        <div className="p-4 flex items-center justify-between border-b border-indigo-100 bg-white/50">
          <div className="flex items-center gap-3">
            {!isMobile && (
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-400 to-purple-500 hover:from-indigo-500 hover:to-purple-600 flex items-center justify-center shadow-md transition-all cursor-pointer"
                title={sidebarOpen ? 'Recolher menu' : 'Expandir menu'}
              >
                <FiMenu className="text-white w-6 h-6" />
              </button>
            )}
            <div>
              <h1 className="font-bold text-lg text-gray-800">Pet Shop Pro</h1>
              <p className="text-xs text-gray-500">Central de Gestão</p>
            </div>
          </div>
          
          {/* Botão Fechar (mobile) ou Patinha (desktop) */}
          <button
            onClick={() => isMobile ? setSidebarOpen(false) : setSidebarVisible(false)}
            className="p-2 hover:bg-indigo-100 rounded-lg transition-colors"
            title={isMobile ? 'Fechar menu' : 'Esconder menu completamente'}
          >
            {isMobile ? (
              <FiX className="w-6 h-6 text-indigo-600" />
            ) : (
              <PawPrint className="w-5 h-5 text-indigo-600" />
            )}
          </button>
        </div>

        {/* Menu Items */}
        <nav className="flex-1 py-2 md:py-4 overflow-y-auto overflow-x-hidden">
          {Array.isArray(menuItems) && menuItems.map((item) => (
            <div key={item.path}>
              {item.submenu ? (
                <>
                  <button
                    onClick={() => {
                      setSubmenusOpen(prev => ({
                        ...prev,
                        [item.path]: !prev[item.path]
                      }));
                    }}
                    className={`w-full flex items-center justify-between gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 mx-1 md:mx-2 rounded-lg transition-all text-sm md:text-base ${
                      location.pathname.startsWith(item.path)
                        ? 'bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm'
                        : 'text-gray-700 hover:bg-white/60'
                    }`}
                  >
                    <div className="flex items-center gap-2 md:gap-3">
                      <item.icon className="text-base md:text-lg flex-shrink-0" />
                      {sidebarOpen && <span className="font-medium text-xs md:text-sm">{item.label}</span>}
                    </div>
                    {sidebarOpen && (
                      submenusOpen[item.path] 
                        ? <FiChevronDown className="text-xs md:text-sm text-gray-400" /> 
                        : <FiChevronRight className="text-xs md:text-sm text-gray-400" />
                    )}
                  </button>
                  {submenusOpen[item.path] && sidebarOpen && (
                    <div className="mt-1 mb-2 space-y-0.5 md:space-y-1">
                      {Array.isArray(item.submenu) && item.submenu.map((subitem) => (
                        <Link
                          key={subitem.path}
                          to={subitem.path}
                          onClick={handleMenuClick}
                          className={`flex items-center gap-2 md:gap-3 px-3 md:px-4 py-1.5 md:py-2 mx-1 md:mx-2 ml-8 md:ml-12 rounded-lg transition-all text-xs md:text-sm ${
                            isActive(subitem.path)
                              ? 'bg-white text-indigo-600 shadow-sm font-medium'
                              : 'text-gray-600 hover:bg-white/50'
                          }`}
                        >
                          <span>{subitem.label}</span>
                        </Link>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <Link
                  to={item.path}
                  onClick={handleMenuClick}
                  className={`flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 mx-1 md:mx-2 my-0.5 md:my-1 rounded-lg transition-all text-sm md:text-base ${
                    isActive(item.path)
                      ? 'bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm'
                      : 'text-gray-700 hover:bg-white/60'
                  }`}
                  title={!sidebarOpen ? item.label : ''}
                >
                  <item.icon className="text-base md:text-lg flex-shrink-0" />
                  {sidebarOpen && (
                    <div className="flex items-center justify-between flex-1">
                      <span className="font-medium text-xs md:text-sm">{item.label}</span>
                      {item.badge && (
                        <span className="w-2 h-2 bg-red-400 rounded-full animate-pulse"></span>
                      )}
                    </div>
                  )}
                </Link>
              )}
            </div>
          ))}
        </nav>

        {/* Bottom Actions */}
        <div className="border-t border-indigo-100 bg-white/30">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 mx-2 my-2 rounded-lg text-gray-700 hover:bg-red-50 hover:text-red-600 transition-all text-left"
            title={!sidebarOpen ? 'Sair' : ''}
          >
            <FiLogOut className="text-lg" />
            {sidebarOpen && <span className="font-medium text-sm">Sair</span>}
          </button>
        </div>
        </aside>
      )}
      
      {/* Botão flutuante para mostrar sidebar quando escondida (apenas desktop) */}
      {!sidebarVisible && !isMobile && (
        <button
          onClick={() => setSidebarVisible(true)}
          className="fixed left-0 top-4 z-50 p-3 bg-gradient-to-br from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white rounded-r-xl shadow-lg transition-all"
          title="Mostrar menu"
        >
          <PawPrint className="w-6 h-6" />
        </button>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-3 md:px-6 py-3 md:py-4 flex items-center justify-between">
          {/* Menu Hamburguer (Mobile) */}
          {isMobile && sidebarVisible && (
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors md:hidden"
              aria-label="Toggle menu"
            >
              <FiMenu className="w-6 h-6 text-gray-700" />
            </button>
          )}
          
          {/* Botão Patinha Mobile - Mostrar menu quando escondido */}
          {isMobile && !sidebarVisible && (
            <button
              onClick={() => setSidebarVisible(true)}
              className="p-2 rounded-lg hover:bg-indigo-100 transition-colors md:hidden"
              aria-label="Mostrar menu"
            >
              <PawPrint className="w-6 h-6 text-indigo-600" />
            </button>
          )}
          
          {/* User Info */}
          <div className="flex items-center gap-2 md:gap-3 ml-auto">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-gray-900">{user?.nome || user?.email}</p>
              <p className="text-xs text-gray-500">{user?.email}</p>
            </div>
            <div className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-sm md:text-base">
              {user?.nome?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-3 md:p-6">
          <Outlet />
        </main>
      </div>

      {/* Botão flutuante da calculadora */}
      <FloatingCalculatorButton
        onClick={() => {
          console.log('🎯 Layout: Abrindo calculadora...');
          setCalculadoraAberta(true);
        }}
      />

      {/* Modal da Calculadora Universal */}
      {calculadoraAberta && (
        <ModalCalculadoraUniversal
          isOpen={calculadoraAberta}
          onClose={() => {
            console.log('🎯 Layout: Fechando calculadora...');
            setCalculadoraAberta(false);
          }}
        />
      )}

      {telaBloqueadaSuspeita && (
        <button
          onClick={destravarTela}
          className="fixed bottom-4 right-4 z-[80] px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-semibold shadow-lg"
          title="Remover bloqueio visual da tela"
        >
          Destravar tela
        </button>
      )}
    </div>
  );
};

export default Layout;
