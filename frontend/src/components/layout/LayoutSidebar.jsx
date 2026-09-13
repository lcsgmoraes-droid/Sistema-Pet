import {
  FiBell,
  FiChevronDown,
  FiChevronUp,
  FiCreditCard,
  FiHelpCircle,
  FiLogOut,
  FiMoon,
  FiSun,
  FiX,
} from "react-icons/fi";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import useNovidadesNaoVistas from "../../hooks/useNovidadesNaoVistas";
import { useTheme } from "../../theme/ThemeContext";
import SidebarMenu from "./SidebarMenu";

const COREPET_LOGO = "/brand/corepet/corepet-horizontal.png";
const COREPET_ICON = "/brand/corepet/corepet-icon-64.png";
// Rail de menu recolhido: 4rem/64px é o padrão usado por VS Code, GitHub etc. para sidebars
// só-ícone — mais estreito que o antigo 5rem/80px (Material Design Navigation Rail, pensado
// para touch, mais largo do que este app precisa no desktop).
const LARGURA_RECOLHIDA = "4rem";

// Hambúrguer que vira X (e volta) com uma animação simples de 3 barras — substitui os dois
// botões separados (recolher / esconder) por um único controle: o estado dele É o estado da
// sidebar (aberta = X, recolhida = hambúrguer), não uma ação de "fechar/esconder o menu".
function BotaoAlternarMenu({ aberto, onClick, title, className = "" }) {
  const barra =
    "absolute left-1/2 top-1/2 h-0.5 w-4 -translate-x-1/2 rounded-full bg-white transition-all duration-300";

  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-expanded={aberto}
      className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#0f5f63] to-[#0f8b8d] shadow-md transition-all hover:from-[#0d4f52] hover:to-[#0d7375] ${className}`}
    >
      <span className="relative block h-4 w-4">
        <span
          className={`${barra} ${aberto ? "translate-y-0 rotate-45" : "-translate-y-1.5 rotate-0"}`}
        />
        <span className={`${barra} ${aberto ? "opacity-0" : "opacity-100"}`} />
        <span
          className={`${barra} ${aberto ? "translate-y-0 -rotate-45" : "translate-y-1.5 rotate-0"}`}
        />
      </span>
      <span className="sr-only">{title}</span>
    </button>
  );
}

export default function LayoutSidebar({
  isMobile,
  sidebarOpen,
  sidebarWidth,
  setSidebarWidth,
  setSidebarOpen,
  menuItems,
  submenusOpen,
  currentPath,
  isActive,
  handleToggleSubmenu,
  handleMenuClick,
  favoritePaths,
  handleToggleFavorite,
  moduloAtivo,
  user,
  logout,
}) {
  const resizeRef = useRef(null);
  const [redimensionando, setRedimensionando] = useState(false);
  const [menuUsuarioAberto, setMenuUsuarioAberto] = useState(false);
  const userMenuRef = useRef(null);
  const novidadesNaoVistas = useNovidadesNaoVistas();
  const { isDark, toggleTheme } = useTheme();

  const nomeUsuario = user?.nome || user?.username || user?.email;
  const identificadorUsuario = user?.username || user?.email;
  const inicialUsuario = (
    user?.nome?.[0] ||
    user?.username?.[0] ||
    user?.email?.[0] ||
    ""
  ).toUpperCase();

  useEffect(() => {
    if (!menuUsuarioAberto) return undefined;

    const aoClicarFora = (evento) => {
      if (!userMenuRef.current?.contains(evento.target)) setMenuUsuarioAberto(false);
    };
    const aoPressionarTecla = (evento) => {
      if (evento.key === "Escape") setMenuUsuarioAberto(false);
    };

    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoPressionarTecla);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoPressionarTecla);
    };
  }, [menuUsuarioAberto]);

  const fecharMenuUsuarioEClicar = () => {
    setMenuUsuarioAberto(false);
    handleMenuClick();
  };

  useEffect(
    () => () => {
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    },
    [],
  );

  const iniciarRedimensionamento = (event) => {
    if (isMobile || !sidebarOpen) return;

    event.preventDefault();
    resizeRef.current = { xInicial: event.clientX, larguraInicial: sidebarWidth };
    setRedimensionando(true);
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";

    const mover = (moveEvent) => {
      const estado = resizeRef.current;
      if (!estado) return;
      const proximaLargura = Math.min(
        440,
        Math.max(232, estado.larguraInicial + moveEvent.clientX - estado.xInicial),
      );
      setSidebarWidth(Math.round(proximaLargura));
    };

    const finalizar = () => {
      resizeRef.current = null;
      setRedimensionando(false);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      window.removeEventListener("pointermove", mover);
      window.removeEventListener("pointerup", finalizar);
    };

    window.addEventListener("pointermove", mover);
    window.addEventListener("pointerup", finalizar);
  };

  return (
    <aside
      className={`${
        isMobile
          ? `erp-mobile-sidebar fixed inset-y-0 left-0 z-50 w-64 max-w-[calc(100vw-24px)] transform overflow-hidden transition-transform duration-300 ${
              sidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`
          : `${redimensionando ? "" : "transition-[width] duration-200"} relative`
      } erp-sidebar shrink-0 bg-gradient-to-b from-[#f4fbfa] to-[#fff8ea] border-r border-[#d8eee9] flex flex-col shadow-lg dark:border-slate-800 dark:from-slate-950 dark:to-slate-900`}
      style={
        isMobile
          ? undefined
          : {
              width: sidebarOpen ? `${sidebarWidth}px` : LARGURA_RECOLHIDA,
              minWidth: sidebarOpen ? `${sidebarWidth}px` : LARGURA_RECOLHIDA,
            }
      }
    >
      {isMobile ? (
        <div className="flex items-center justify-between gap-3 border-b border-[#d8eee9] bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/80">
          <img
            src={COREPET_LOGO}
            alt="CorePet"
            className="h-9 w-auto max-w-[148px] object-contain"
          />
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="rounded-lg p-2 transition-colors hover:bg-[#d8eee9] dark:hover:bg-slate-800"
            title="Fechar menu"
            aria-label="Fechar menu"
          >
            <FiX className="h-6 w-6 text-[#0f5f63] dark:text-cyan-200" />
          </button>
        </div>
      ) : sidebarOpen ? (
        <div className="flex items-center justify-between gap-3 border-b border-[#d8eee9] bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/80">
          <img
            src={COREPET_LOGO}
            alt="CorePet"
            className="h-9 w-auto max-w-[148px] object-contain"
          />
          <BotaoAlternarMenu aberto onClick={() => setSidebarOpen(false)} title="Recolher menu" />
        </div>
      ) : (
        <div className="relative flex items-center justify-center border-b border-[#d8eee9] bg-white/70 py-4 dark:border-slate-800 dark:bg-slate-950/80">
          <img src={COREPET_ICON} alt="CorePet" className="h-8 w-8 rounded-lg object-contain" />
          <BotaoAlternarMenu
            onClick={() => setSidebarOpen(true)}
            title="Expandir menu"
            className="absolute -right-4 top-1/2 -translate-y-1/2"
          />
        </div>
      )}

      <SidebarMenu
        menuItems={menuItems}
        sidebarOpen={sidebarOpen}
        submenusOpen={submenusOpen}
        currentPath={currentPath}
        isActive={isActive}
        onToggleSubmenu={handleToggleSubmenu}
        onMenuClick={handleMenuClick}
        favoritePaths={favoritePaths}
        onToggleFavorite={handleToggleFavorite}
        moduloAtivo={moduloAtivo}
      />

      <div
        ref={userMenuRef}
        className="relative border-t border-[#d8eee9] bg-white/40 dark:border-slate-800 dark:bg-slate-950/80"
      >
        {menuUsuarioAberto && (
          <div
            role="menu"
            aria-label="Menu do usuário"
            className="absolute bottom-full left-2 mb-2 w-64 overflow-hidden rounded-xl border border-[#d8eee9] bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-slate-900"
          >
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                toggleTheme();
                setMenuUsuarioAberto(false);
              }}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-gray-700 transition-all hover:bg-gray-50 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {isDark ? (
                <FiSun className="flex-shrink-0 text-lg" />
              ) : (
                <FiMoon className="flex-shrink-0 text-lg" />
              )}
              <span className="v2-menu-item font-medium">
                {isDark ? "Usar tela clara" : "Usar tela escura"}
              </span>
            </button>
            <Link
              to="/meu-plano"
              role="menuitem"
              onClick={fecharMenuUsuarioEClicar}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-emerald-700 transition-all hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-500/10"
            >
              <FiCreditCard className="flex-shrink-0 text-lg" />
              <span className="v2-menu-item font-medium">Meu Plano</span>
            </Link>
            <Link
              to="/novidades"
              role="menuitem"
              onClick={fecharMenuUsuarioEClicar}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-[#9a6b05] transition-all hover:bg-[#fff1c9] dark:text-amber-300 dark:hover:bg-amber-500/10"
            >
              <FiBell className="flex-shrink-0 text-lg" />
              <span className="v2-menu-item font-medium">Novidades</span>
              {novidadesNaoVistas > 0 ? (
                <span
                  className="ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] font-bold text-white"
                  aria-label={`${novidadesNaoVistas} novidade(s) não vista(s)`}
                >
                  {novidadesNaoVistas > 9 ? "9+" : novidadesNaoVistas}
                </span>
              ) : null}
            </Link>
            <Link
              to="/ajuda"
              role="menuitem"
              onClick={fecharMenuUsuarioEClicar}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-[#0f5f63] transition-all hover:bg-[#d8eee9] dark:text-cyan-200 dark:hover:bg-slate-800"
            >
              <FiHelpCircle className="flex-shrink-0 text-lg" />
              <span className="v2-menu-item font-medium">Ajuda & Planos</span>
            </Link>
            <div className="my-1 border-t border-[#d8eee9] dark:border-slate-800" />
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setMenuUsuarioAberto(false);
                logout();
              }}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-gray-700 transition-all hover:bg-red-50 hover:text-red-600 dark:text-slate-300 dark:hover:bg-red-500/10 dark:hover:text-red-200"
            >
              <FiLogOut className="flex-shrink-0 text-lg" />
              <span className="v2-menu-item font-medium">Sair</span>
            </button>
          </div>
        )}

        <button
          type="button"
          onClick={() => setMenuUsuarioAberto((aberto) => !aberto)}
          aria-haspopup="menu"
          aria-expanded={menuUsuarioAberto}
          className="flex w-full items-center gap-2.5 px-3 py-3 text-left transition-all hover:bg-white/70 dark:hover:bg-slate-900/60"
          title={!sidebarOpen ? nomeUsuario : ""}
        >
          <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-[#0f5f63] text-sm font-bold text-white">
            {inicialUsuario}
          </span>
          {sidebarOpen && (
            <>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-gray-900 dark:text-slate-100">
                  {nomeUsuario}
                </span>
                <span className="v2-texto-ajuda block truncate">{identificadorUsuario}</span>
              </span>
              {menuUsuarioAberto ? (
                <FiChevronUp className="flex-shrink-0 text-gray-400 dark:text-slate-500" />
              ) : (
                <FiChevronDown className="flex-shrink-0 text-gray-400 dark:text-slate-500" />
              )}
            </>
          )}
        </button>
      </div>

      {!isMobile && sidebarOpen && (
        <button
          type="button"
          data-sidebar-resize-handle
          onPointerDown={iniciarRedimensionamento}
          className={`group absolute inset-y-0 -right-2 z-30 w-2 cursor-col-resize touch-none focus:outline-none ${
            redimensionando ? "bg-[#0f8b8d]/10" : "bg-transparent"
          }`}
          title="Arraste para ajustar a largura do menu"
          aria-label="Ajustar largura do menu lateral"
        >
          <span
            aria-hidden="true"
            className={`absolute left-1/2 top-1/2 h-14 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#0f8b8d]/45 shadow-sm transition-all group-hover:h-20 group-hover:bg-[#0f8b8d]/80 group-focus:h-20 group-focus:bg-[#0f8b8d]/80 ${
              redimensionando ? "h-24 bg-[#0f8b8d]" : ""
            }`}
          />
          <span className="pointer-events-none absolute left-4 top-1/2 z-40 hidden -translate-y-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white shadow-lg group-hover:block group-focus:block">
            Arraste para aumentar ou diminuir
          </span>
        </button>
      )}
    </aside>
  );
}
