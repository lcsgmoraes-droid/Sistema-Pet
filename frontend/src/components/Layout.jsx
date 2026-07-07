import { CalendarDays, FlaskConical, Stethoscope, Syringe } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { FiFileText, FiMenu } from "react-icons/fi";
import { toast } from "react-hot-toast";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useModulos } from "../contexts/ModulosContext";
import { api } from "../services/api";
import { useEscapeFallbackForVisibleModals } from "../utils/modalEscape";
import { isVeterinarioProfile } from "../utils/veterinarioPerfil";
import {
  FLOATING_CALCULATOR_ENABLED_KEY,
  FLOATING_CALCULATOR_PREF_EVENT,
  isFloatingCalculatorEnabled,
} from "../utils/floatingCalculatorPreference";
import FloatingCalculatorButton from "./FloatingCalculatorButton";
import {
  FAVORITE_DRAG_CLICK_SUPPRESSION_MS,
  buildVisibleMenuFavorites,
  normalizeMenuFavorites,
  reorderMenuFavorites,
  sameFavoritePathOrder,
  shouldBlockFavoriteShortcutClick,
  toggleMenuFavorite,
} from "./layout/menuFavorites";
import LayoutFavoritesBar from "./layout/LayoutFavoritesBar";
import LayoutSidebar from "./layout/LayoutSidebar";
import { createLayoutMenuItems } from "./layout/menuConfig";
import ModalCalculadoraUniversal from "./ModalCalculadoraUniversal";
import ThemeToggle from "./theme/ThemeToggle";

const COREPET_ICON = "/brand/corepet/corepet-icon-64.png";

const Layout = () => {
  useEscapeFallbackForVisibleModals();

  const location = useLocation();
  const isBradescoOrganizerRoute = location.pathname === "/organizador-bradesco";
  const { user, logout } = useAuth();
  const {
    modulosAtivos,
    moduloAtivo,
    devControlesAtivos,
    devModoModulos,
    definirModoDevModulos,
    alternarModuloDev,
  } = useModulos();

  const getModoDevLabel = () => {
    if (devModoModulos === "all_unlocked") return "Todos liberados";
    if (devModoModulos === "all_locked") return "Premium bloqueado";
    if (devModoModulos === "custom") return "Personalizado";
    return "Modo normal";
  };

  const onToggleModuloDev = (event, modulo) => {
    event.preventDefault();
    event.stopPropagation();
    alternarModuloDev(modulo);
  };

  // Estado para detectar mobile
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // Detectar mudanças no tamanho da tela
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Função para verificar se o usuário tem permissão
  const hasPermission = (permission) => {
    if (!user) return false;

    // Admins têm acesso a tudo (qualquer variação do nome do role admin)
    const adminRoles = ["admin", "Admin", "Administrador", "administrador", "ADMIN"];
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

  const hasAnyPermission = (permissions = []) => {
    if (!Array.isArray(permissions) || permissions.length === 0) return false;
    return permissions.some((permission) => hasPermission(permission));
  };

  // Estado da sidebar com persistência e fechada por padrão no PDV
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    // Em mobile, sempre começa fechada
    if (window.innerWidth < 768) return false;

    const saved = localStorage.getItem("sidebar_open");
    if (saved !== null) {
      return JSON.parse(saved);
    }
    // Se não tem preferência salva, fecha no PDV por padrão
    return location.pathname !== "/pdv";
  });

  const [submenusOpen, setSubmenusOpen] = useState({});

  // Estado para esconder completamente a sidebar
  const [sidebarVisible, setSidebarVisible] = useState(() => {
    const saved = localStorage.getItem("sidebar_visible");
    return saved !== null ? JSON.parse(saved) : true;
  });
  const effectiveSidebarVisible = !isBradescoOrganizerRoute && sidebarVisible;

  // Estado da calculadora universal
  const [calculadoraAberta, setCalculadoraAberta] = useState(false);
  const [calculadoraModo, setCalculadoraModo] = useState("calcular");
  const [calculadoraFlutuanteAtiva, setCalculadoraFlutuanteAtiva] = useState(() =>
    isFloatingCalculatorEnabled(),
  );

  // Contagem de lembretes pendentes para badge dinâmico
  const [lembretesCount, setLembretesCount] = useState(0);
  const [menuFavorites, setMenuFavorites] = useState([]);
  const lembretesPollingRef = useRef(false);
  const [telaBloqueadaSuspeita, setTelaBloqueadaSuspeita] = useState(false);
  const overlaySuspeitoDesdeRef = useRef(new Map());
  const favoriteDragClickGuardRef = useRef({
    isDragging: false,
    suppressClickUntil: 0,
  });
  const perfilVeterinario = isVeterinarioProfile(user);
  const rotaVeterinaria = location.pathname.startsWith("/veterinario");
  const exibirAtalhosVetMobile = isMobile && perfilVeterinario && rotaVeterinaria;
  const atalhosVetMobile = [
    { path: "/veterinario", label: "Painel", icon: Stethoscope },
    { path: "/veterinario/agenda", label: "Agenda", icon: CalendarDays },
    { path: "/veterinario/consultas", label: "Consultas", icon: FiFileText },
    { path: "/veterinario/vacinas", label: "Vacinas", icon: Syringe },
    { path: "/veterinario/exames", label: "Exames", icon: FlaskConical },
  ];

  useEffect(() => {
    const atualizarCalculadoraFlutuante = (event) => {
      if (event.type === "storage" && event.key !== FLOATING_CALCULATOR_ENABLED_KEY) {
        return;
      }

      setCalculadoraFlutuanteAtiva(event.detail?.enabled ?? isFloatingCalculatorEnabled());
    };

    window.addEventListener(FLOATING_CALCULATOR_PREF_EVENT, atualizarCalculadoraFlutuante);
    window.addEventListener("storage", atualizarCalculadoraFlutuante);

    return () => {
      window.removeEventListener(FLOATING_CALCULATOR_PREF_EVENT, atualizarCalculadoraFlutuante);
      window.removeEventListener("storage", atualizarCalculadoraFlutuante);
    };
  }, []);

  const neutralizarOverlay = (elementoOverlay) => {
    if (!elementoOverlay) return;

    elementoOverlay.setAttribute("data-overlay-neutralizado", "true");
    elementoOverlay.style.pointerEvents = "none";
    elementoOverlay.style.backgroundColor = "transparent";
    elementoOverlay.style.opacity = "0";
    elementoOverlay.style.transition = "opacity 120ms ease";
  };

  const ehOverlayTelaCheia = (elementoOverlay) => {
    const estilo = window.getComputedStyle(elementoOverlay);
    const larguraTelaCheia = elementoOverlay.offsetWidth >= window.innerWidth - 8;
    const alturaTelaCheia = elementoOverlay.offsetHeight >= window.innerHeight - 8;
    const zIndex = Number.parseInt(estilo.zIndex || "0", 10);

    return estilo.position === "fixed" && larguraTelaCheia && alturaTelaCheia && zIndex >= 40;
  };

  const encontrarOverlaysOrfaos = () => {
    if (typeof window === "undefined" || typeof document === "undefined") {
      return [];
    }

    const overlays = Array.from(document.querySelectorAll("div.fixed.inset-0"));

    return overlays.filter((elementoOverlay) => {
      if (elementoOverlay.getAttribute("data-overlay-neutralizado") === "true") {
        return false;
      }

      if (!ehOverlayTelaCheia(elementoOverlay)) {
        return false;
      }

      const classes = elementoOverlay.className || "";
      if (typeof classes === "string" && classes.includes("bg-transparent")) {
        return false;
      }

      const modalBackdropFor = elementoOverlay.getAttribute("data-modal-backdrop-for");
      if (modalBackdropFor) {
        const painelModalAtivo = Array.from(document.querySelectorAll("[data-modal-panel]")).some(
          (painel) => painel.getAttribute("data-modal-panel") === modalBackdropFor,
        );

        if (painelModalAtivo) {
          return false;
        }
      }

      const estilo = window.getComputedStyle(elementoOverlay);
      const visivel = estilo.display !== "none" && estilo.visibility !== "hidden";
      const bloqueiaClique = estilo.pointerEvents !== "none";
      const fundoAtivo =
        estilo.backgroundColor &&
        estilo.backgroundColor !== "rgba(0, 0, 0, 0)" &&
        estilo.backgroundColor !== "transparent";
      const possuiSpinner = Boolean(elementoOverlay.querySelector(".animate-spin"));
      const overlayCalculadora =
        elementoOverlay.getAttribute("data-overlay-type") === "calculadora-universal";

      if (!visivel || !bloqueiaClique) {
        return false;
      }

      const possuiConteudoModal = Boolean(
        elementoOverlay.querySelector(
          '[role="dialog"], .bg-white, .rounded-lg, .rounded-xl, .shadow-2xl, .shadow-xl',
        ),
      );

      if (overlayCalculadora && !calculadoraAberta) {
        return true;
      }

      return !possuiConteudoModal && (fundoAtivo || possuiSpinner);
    });
  };

  const neutralizarOverlaysOrfaos = () => {
    const overlaysOrfaos = encontrarOverlaysOrfaos();
    overlaysOrfaos.forEach((elementoOverlay) => neutralizarOverlay(elementoOverlay));
    overlaySuspeitoDesdeRef.current.clear();
  };

  const destravarTela = (silencioso = false) => {
    setSidebarOpen(false);
    setCalculadoraAberta(false);

    const eventoEscape = new KeyboardEvent("keydown", { key: "Escape" });
    window.dispatchEvent(eventoEscape);

    neutralizarOverlaysOrfaos();
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

  const handleToggleSubmenu = (path) => {
    setSubmenusOpen((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  const toggleSidebarMobile = () => {
    setSidebarVisible(true);
    setSidebarOpen((open) => !open);
  };

  // Persistir estado da sidebar no localStorage (apenas desktop)
  useEffect(() => {
    if (!isMobile) {
      localStorage.setItem("sidebar_open", JSON.stringify(sidebarOpen));
    }
  }, [sidebarOpen, isMobile]);

  useEffect(() => {
    if (!isMobile) {
      localStorage.setItem("sidebar_visible", JSON.stringify(sidebarVisible));
    }
  }, [sidebarVisible, isMobile]);

  // Fechar menu mobile ao mudar de rota
  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [location.pathname, isMobile]);

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

        const overlayCalculadora =
          elementoOverlay.getAttribute("data-overlay-type") === "calculadora-universal";
        const limiteMs = overlayCalculadora ? 900 : 1800;

        if (agora - vistoDesde >= limiteMs) {
          precisaDestravarAutomaticamente = true;
        }
      });

      setTelaBloqueadaSuspeita(overlaysOrfaos.length > 0);

      if (precisaDestravarAutomaticamente) {
        neutralizarOverlaysOrfaos();
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

  // Buscar contagem de lembretes pendentes para badge dinâmico
  useEffect(() => {
    const fetchLembretesCount = async ({ force = false } = {}) => {
      if (lembretesPollingRef.current) return;
      if (!force && document.visibilityState === "hidden") return;

      lembretesPollingRef.current = true;
      try {
        const pendentesResp = await api.get("/lembretes/pendentes");
        const blingAtivoConfirmado =
          Boolean(user) && Array.isArray(modulosAtivos) && moduloAtivo("bling");
        const autoResp = blingAtivoConfirmado
          ? await api.get("/integracoes/bling/nf/autocadastros-recentes", {
              params: { horas: 24, resumo: true },
            })
          : null;

        const pendentesPayload = pendentesResp?.data || {};
        const pendentes = Number(
          pendentesPayload?.total ??
            (Array.isArray(pendentesPayload?.lembretes) ? pendentesPayload.lembretes.length : 0),
        );
        const autocadastros24h = Number(autoResp?.data?.total || 0);

        setLembretesCount(Math.max(0, pendentes + autocadastros24h));
      } catch {
        // Silencioso — não bloqueia o layout
      } finally {
        lembretesPollingRef.current = false;
      }
    };
    fetchLembretesCount({ force: true });
    const interval = setInterval(fetchLembretesCount, 300000);
    return () => clearInterval(interval);
  }, [moduloAtivo, modulosAtivos]);

  useEffect(() => {
    let ativo = true;

    const carregarMenuFavorites = async () => {
      if (!user) {
        setMenuFavorites([]);
        return;
      }

      try {
        const response = await api.get("/usuarios/me/menu-favoritos");
        if (ativo) {
          setMenuFavorites(normalizeMenuFavorites(response?.data?.items || []));
        }
      } catch {
        if (ativo) {
          setMenuFavorites([]);
        }
      }
    };

    carregarMenuFavorites();
    return () => {
      ativo = false;
    };
  }, [user?.id, user?.tenant_id]);

  const allMenuItems = createLayoutMenuItems({ lembretesCount });

  const itemLiberadoPorModulo = (item) => !item.modulo || moduloAtivo(item.modulo);
  const itemLiberadoPorPermissao = (item) => {
    if (item.anyOfPermissions) return hasAnyPermission(item.anyOfPermissions);
    if (!item.permission) return true;
    return hasPermission(item.permission);
  };

  // Filtrar menus baseado nas permissões do usuário e no plano do tenant
  const menuItems = allMenuItems.filter((item) => {
    if (!itemLiberadoPorModulo(item)) {
      return false;
    }

    // Se tem submenu, filtrar os itens do submenu por permissão e módulo PRIMEIRO
    if (item.submenu && Array.isArray(item.submenu)) {
      const submenuFiltrado = item.submenu.filter((subitem) => {
        if (!itemLiberadoPorModulo(subitem)) return false;
        // Se subitem não tem permissão, é sempre visível
        if (!subitem.permission) return true;
        // Verifica se usuário tem a permissão
        return itemLiberadoPorPermissao(subitem);
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
    return itemLiberadoPorPermissao(item);
  });

  const visibleMenuFavorites = useMemo(
    () => buildVisibleMenuFavorites(menuFavorites, menuItems),
    [menuFavorites, menuItems],
  );
  const favoritePaths = useMemo(
    () => new Set(menuFavorites.map((favorite) => favorite.path)),
    [menuFavorites],
  );

  const handleToggleFavorite = async (item) => {
    const favoritosAnteriores = menuFavorites;
    let proximosFavoritos;

    try {
      proximosFavoritos = toggleMenuFavorite(favoritosAnteriores, item);
    } catch (error) {
      toast.error(error?.message || "Nao foi possivel alterar favoritos.");
      return;
    }

    setMenuFavorites(proximosFavoritos);

    try {
      const response = await api.put("/usuarios/me/menu-favoritos", {
        items: proximosFavoritos,
      });
      setMenuFavorites(normalizeMenuFavorites(response?.data?.items || proximosFavoritos));
    } catch {
      setMenuFavorites(favoritosAnteriores);
      toast.error("Nao foi possivel salvar favoritos agora.");
    }
  };

  const markFavoriteDragStarted = () => {
    favoriteDragClickGuardRef.current = {
      isDragging: true,
      suppressClickUntil: Date.now() + FAVORITE_DRAG_CLICK_SUPPRESSION_MS,
    };
  };

  const markFavoriteDragFinished = () => {
    favoriteDragClickGuardRef.current = {
      isDragging: false,
      suppressClickUntil: Date.now() + FAVORITE_DRAG_CLICK_SUPPRESSION_MS,
    };
  };

  const handleFavoriteShortcutClick = (event) => {
    const guard = favoriteDragClickGuardRef.current;
    const shouldBlockClick = shouldBlockFavoriteShortcutClick({
      isDragging: guard.isDragging,
      suppressClickUntil: guard.suppressClickUntil,
    });

    if (!shouldBlockClick) return;

    event.preventDefault();
    event.stopPropagation();
  };

  const handleFavoriteDragEnd = async ({ active, over }) => {
    markFavoriteDragFinished();

    if (!over || active.id === over.id) return;

    const favoritosAnteriores = menuFavorites;
    const proximosFavoritos = reorderMenuFavorites(
      favoritosAnteriores,
      String(active.id),
      String(over.id),
    );

    if (sameFavoritePathOrder(proximosFavoritos, favoritosAnteriores)) {
      return;
    }

    setMenuFavorites(proximosFavoritos);

    try {
      const response = await api.put("/usuarios/me/menu-favoritos", {
        items: proximosFavoritos,
      });
      setMenuFavorites(normalizeMenuFavorites(response?.data?.items || proximosFavoritos));
    } catch {
      setMenuFavorites(favoritosAnteriores);
      toast.error("Nao foi possivel salvar a nova ordem dos favoritos.");
    }
  };

  useEffect(() => {
    setSubmenusOpen((prev) => {
      let mudou = false;
      const proximo = { ...prev };

      menuItems.forEach((item) => {
        if (!Array.isArray(item.submenu) || item.submenu.length === 0) return;

        const possuiRotaAtiva = item.submenu.some((subitem) =>
          location.pathname.startsWith(subitem.path),
        );

        // Autoabre apenas na primeira vez para a rota ativa.
        // Se o usuario fechou manualmente, respeitamos esse estado.
        if (possuiRotaAtiva && typeof proximo[item.path] === "undefined") {
          proximo[item.path] = true;
          mudou = true;
        }
      });

      return mudou ? proximo : prev;
    });
  }, [location.pathname]);

  const isActive = (path) => location.pathname === path;

  return (
    <div className="erp-shell flex h-screen min-w-0 bg-gray-50 dark:bg-slate-950">
      {/* Backdrop para mobile */}
      {isMobile && sidebarOpen && effectiveSidebarVisible && (
        <div
          className="erp-mobile-sidebar-backdrop fixed inset-0 bg-transparent z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      {effectiveSidebarVisible && (
        <LayoutSidebar
          isMobile={isMobile}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          setSidebarVisible={setSidebarVisible}
          devControlesAtivos={devControlesAtivos}
          devModoModulos={devModoModulos}
          definirModoDevModulos={definirModoDevModulos}
          getModoDevLabel={getModoDevLabel}
          menuItems={menuItems}
          submenusOpen={submenusOpen}
          currentPath={location.pathname}
          isActive={isActive}
          handleToggleSubmenu={handleToggleSubmenu}
          handleMenuClick={handleMenuClick}
          favoritePaths={favoritePaths}
          handleToggleFavorite={handleToggleFavorite}
          moduloAtivo={moduloAtivo}
          onToggleModuloDev={onToggleModuloDev}
          logout={logout}
        />
      )}
      {!effectiveSidebarVisible && !isMobile && !isBradescoOrganizerRoute && (
        <button
          onClick={() => setSidebarVisible(true)}
          className="fixed left-0 top-4 z-50 p-3 bg-gradient-to-br from-[#0f5f63] to-[#0f8b8d] hover:from-[#0d4f52] hover:to-[#0d7375] text-white rounded-r-xl shadow-lg transition-all"
          title="Mostrar menu"
        >
          <img src={COREPET_ICON} alt="" className="h-6 w-6 rounded bg-white" />
        </button>
      )}

      {/* Main Content */}
      <div className="erp-main-column flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="erp-topbar flex shrink-0 items-center justify-between gap-2 border-b border-gray-200 bg-white px-3 py-3 md:px-6 md:py-4 dark:border-slate-800 dark:bg-slate-950">
          {/* Menu Hamburguer (Mobile) */}
          {isMobile && effectiveSidebarVisible && (
            <button
              type="button"
              onClick={toggleSidebarMobile}
              className="touch-manipulation rounded-lg p-2 hover:bg-gray-100 transition-colors md:hidden"
              aria-label="Toggle menu"
              aria-expanded={sidebarOpen}
            >
              <FiMenu className="w-6 h-6 text-gray-700" />
            </button>
          )}

          {/* Botao CorePet Mobile - Mostrar menu quando escondido */}
          {isMobile && !effectiveSidebarVisible && !isBradescoOrganizerRoute && (
            <button
              onClick={() => setSidebarVisible(true)}
              className="p-2 rounded-lg hover:bg-[#d8eee9] transition-colors md:hidden"
              aria-label="Mostrar menu"
            >
              <img src={COREPET_ICON} alt="" className="h-6 w-6 rounded" />
            </button>
          )}

          {/* User Info */}
          <div className="flex items-center gap-2 md:gap-3 ml-auto">
            <ThemeToggle />
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-gray-900 dark:text-slate-100">
                {user?.nome || user?.email}
              </p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{user?.email}</p>
            </div>
            <div className="w-9 h-9 md:w-10 md:h-10 rounded-full bg-[#0f5f63] flex items-center justify-center text-white font-bold text-sm md:text-base">
              {user?.nome?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}
            </div>
          </div>
        </header>

        {!isBradescoOrganizerRoute && (
          <LayoutFavoritesBar
            favorites={visibleMenuFavorites}
            isActive={isActive}
            onShortcutClick={handleFavoriteShortcutClick}
            onDragStart={markFavoriteDragStarted}
            onDragEnd={handleFavoriteDragEnd}
            onDragCancel={markFavoriteDragFinished}
          />
        )}

        {/* Page Content */}
        <main
          className={`erp-page-content flex-1 overflow-y-auto ${isBradescoOrganizerRoute ? "p-0" : `p-3 md:p-6 ${exibirAtalhosVetMobile ? "pb-24" : ""}`}`}
        >
          <Outlet />
        </main>
      </div>

      {/* Botão flutuante da calculadora */}
      {calculadoraFlutuanteAtiva && !exibirAtalhosVetMobile && (
        <FloatingCalculatorButton
          onClick={() => {
            console.log("🎯 Layout: Abrindo calculadora...");
            setCalculadoraModo("calcular");
            setCalculadoraAberta(true);
          }}
          onCompareClick={() => {
            console.log("Abrindo comparador de preco...");
            setCalculadoraModo("comparar-preco");
            setCalculadoraAberta(true);
          }}
        />
      )}

      {exibirAtalhosVetMobile && (
        <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-cyan-100 bg-white/95 px-2 pb-[calc(env(safe-area-inset-bottom,0px)+0.35rem)] pt-2 shadow-[0_-10px_30px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="grid grid-cols-5 gap-1">
            {atalhosVetMobile.map((item) => {
              const Icon = item.icon;
              const ativo = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-[11px] font-medium transition-colors ${
                    ativo
                      ? "bg-cyan-50 text-cyan-700"
                      : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      )}

      {/* Modal da Calculadora Universal */}
      {calculadoraAberta && (
        <ModalCalculadoraUniversal
          isOpen={calculadoraAberta}
          modoInicial={calculadoraModo}
          onClose={() => {
            console.log("🎯 Layout: Fechando calculadora...");
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
