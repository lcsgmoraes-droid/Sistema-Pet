import { FiBell, FiCreditCard, FiHelpCircle, FiLogOut, FiMenu, FiX } from "react-icons/fi";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import useNovidadesNaoVistas from "../../hooks/useNovidadesNaoVistas";
import SidebarMenu from "./SidebarMenu";

const COREPET_LOGO = "/brand/corepet/corepet-horizontal.png";

export default function LayoutSidebar({
  isMobile,
  sidebarOpen,
  sidebarWidth,
  setSidebarWidth,
  setSidebarOpen,
  setSidebarVisible,
  devControlesAtivos,
  devModoModulos,
  definirModoDevModulos,
  getModoDevLabel,
  menuItems,
  submenusOpen,
  currentPath,
  isActive,
  handleToggleSubmenu,
  handleMenuClick,
  favoritePaths,
  handleToggleFavorite,
  moduloAtivo,
  onToggleModuloDev,
  logout,
}) {
  const resizeRef = useRef(null);
  const [redimensionando, setRedimensionando] = useState(false);
  const novidadesNaoVistas = useNovidadesNaoVistas();

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
              width: sidebarOpen ? `${sidebarWidth}px` : "5rem",
              minWidth: sidebarOpen ? `${sidebarWidth}px` : "5rem",
            }
      }
    >
      <div
        className={`p-4 flex items-center border-b border-[#d8eee9] bg-white/70 dark:border-slate-800 dark:bg-slate-950/80 ${!isMobile && !sidebarOpen ? "justify-center" : "justify-between"}`}
      >
        <div className="flex items-center gap-3">
          {!isMobile && (
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#0f5f63] to-[#0f8b8d] hover:from-[#0d4f52] hover:to-[#0d7375] flex items-center justify-center shadow-md transition-all cursor-pointer"
              title={sidebarOpen ? "Recolher menu" : "Expandir menu"}
            >
              <FiMenu className="text-white w-6 h-6" />
            </button>
          )}
          {(isMobile || sidebarOpen) && (
            <div className="min-w-0">
              <img
                src={COREPET_LOGO}
                alt="CorePet"
                className="h-9 w-auto max-w-[148px] object-contain"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-slate-400">Central de Gestao</p>
              {devControlesAtivos && sidebarOpen && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[#0f8b8d] dark:text-cyan-300">
                    DEV modulos: {getModoDevLabel()}
                  </p>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => definirModoDevModulos("normal")}
                      className={`px-2 py-1 rounded text-[10px] border ${
                        devModoModulos === "normal"
                          ? "bg-[#d8eee9] border-[#b9ddd8] text-[#0f5f63] dark:border-cyan-400/40 dark:bg-cyan-500/15 dark:text-cyan-200"
                          : "bg-white/70 border-gray-200 text-gray-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"
                      }`}
                    >
                      Normal
                    </button>
                    <button
                      onClick={() => definirModoDevModulos("all_unlocked")}
                      className={`px-2 py-1 rounded text-[10px] border ${
                        devModoModulos === "all_unlocked"
                          ? "bg-green-100 border-green-200 text-green-700 dark:border-green-400/40 dark:bg-green-500/15 dark:text-green-200"
                          : "bg-white/70 border-gray-200 text-gray-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"
                      }`}
                    >
                      Liberar tudo
                    </button>
                    <button
                      onClick={() => definirModoDevModulos("all_locked")}
                      className={`px-2 py-1 rounded text-[10px] border ${
                        devModoModulos === "all_locked"
                          ? "bg-amber-100 border-amber-200 text-amber-700 dark:border-amber-400/40 dark:bg-amber-500/15 dark:text-amber-200"
                          : "bg-white/70 border-gray-200 text-gray-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"
                      }`}
                    >
                      Bloquear premium
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {(isMobile || sidebarOpen) && (
          <button
            onClick={() => (isMobile ? setSidebarOpen(false) : setSidebarVisible(false))}
            className="p-2 hover:bg-[#d8eee9] rounded-lg transition-colors dark:hover:bg-slate-800"
            title={isMobile ? "Fechar menu" : "Esconder menu completamente"}
          >
            {isMobile ? (
              <FiX className="w-6 h-6 text-[#0f5f63] dark:text-cyan-200" />
            ) : (
              <FiX className="w-5 h-5 text-[#0f5f63] dark:text-cyan-200" />
            )}
          </button>
        )}
      </div>

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
        devControlesAtivos={devControlesAtivos}
        moduloAtivo={moduloAtivo}
        onToggleModuloDev={onToggleModuloDev}
      />

      <div className="border-t border-[#d8eee9] bg-white/40 dark:border-slate-800 dark:bg-slate-950/80">
        <Link
          to="/meu-plano"
          onClick={handleMenuClick}
          className="w-full flex items-center gap-3 px-4 py-2.5 mx-2 mt-2 rounded-lg text-emerald-700 hover:bg-emerald-50 transition-all dark:text-emerald-300 dark:hover:bg-emerald-500/10"
          title={!sidebarOpen ? "Meu Plano" : ""}
        >
          <FiCreditCard className="text-lg flex-shrink-0" />
          {sidebarOpen && <span className="font-medium text-sm">Meu Plano</span>}
        </Link>
        <Link
          to="/novidades"
          onClick={handleMenuClick}
          className="relative mx-2 mt-1 flex w-full items-center gap-3 rounded-lg px-4 py-2.5 text-[#9a6b05] transition-all hover:bg-[#fff1c9] dark:text-amber-300 dark:hover:bg-amber-500/10"
          title={!sidebarOpen ? "Novidades" : ""}
        >
          <FiBell className="flex-shrink-0 text-lg" />
          {sidebarOpen && <span className="font-medium text-sm">Novidades</span>}
          {novidadesNaoVistas > 0 ? (
            <span
              className={`${
                sidebarOpen ? "ml-auto" : "absolute right-1 top-1"
              } inline-flex min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] font-bold text-white`}
              aria-label={`${novidadesNaoVistas} novidade(s) não vista(s)`}
            >
              {novidadesNaoVistas > 9 ? "9+" : novidadesNaoVistas}
            </span>
          ) : null}
        </Link>
        <Link
          to="/ajuda"
          onClick={handleMenuClick}
          className="w-full flex items-center gap-3 px-4 py-2.5 mx-2 mt-1 rounded-lg text-[#0f5f63] hover:bg-[#d8eee9] transition-all dark:text-cyan-200 dark:hover:bg-slate-800"
          title={!sidebarOpen ? "Ajuda & Planos" : ""}
        >
          <FiHelpCircle className="text-lg flex-shrink-0" />
          {sidebarOpen && <span className="font-medium text-sm">Ajuda & Planos</span>}
        </Link>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-3 mx-2 my-2 rounded-lg text-gray-700 hover:bg-red-50 hover:text-red-600 transition-all text-left dark:text-slate-300 dark:hover:bg-red-500/10 dark:hover:text-red-200"
          title={!sidebarOpen ? "Sair" : ""}
        >
          <FiLogOut className="text-lg" />
          {sidebarOpen && <span className="font-medium text-sm">Sair</span>}
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
