import { useEffect, useRef, useState } from "react";

import SidebarMenu from "./SidebarMenu";

// Rail de menu recolhido: 4rem/64px é o padrão usado por VS Code, GitHub etc. para sidebars
// só-ícone — mais estreito que o antigo 5rem/80px (Material Design Navigation Rail, pensado
// para touch, mais largo do que este app precisa no desktop).
const LARGURA_RECOLHIDA = "4rem";

export default function LayoutSidebar({
  isMobile,
  sidebarOpen,
  sidebarWidth,
  setSidebarWidth,
  menuItems,
  submenusOpen,
  currentPath,
  isActive,
  handleToggleSubmenu,
  handleMenuClick,
  favoritePaths,
  handleToggleFavorite,
  moduloAtivo,
}) {
  const resizeRef = useRef(null);
  const [redimensionando, setRedimensionando] = useState(false);

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
          ? `erp-mobile-sidebar fixed left-0 top-14 bottom-0 z-50 w-64 max-w-[calc(100vw-24px)] transform overflow-hidden transition-transform duration-300 ${
              sidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`
          : `${redimensionando ? "" : "transition-[width] duration-300 ease-in-out"} relative`
      } erp-sidebar shrink-0 bg-gradient-to-b from-[#f4fbfa] to-[#fff8ea] border-r border-[#d8eee9] flex flex-col shadow-lg dark:border-slate-800 dark:from-slate-950 dark:to-slate-900`}
      style={
        isMobile
          ? undefined
          : {
              // Só "width" aqui de propósito: "shrink-0" já impede o flex pai de espremer a
              // sidebar, então um "minWidth" redundante (que não estava na lista de transição)
              // pulava pro valor novo instantaneamente e travava a animação no meio do caminho.
              width: sidebarOpen ? `${sidebarWidth}px` : LARGURA_RECOLHIDA,
            }
      }
    >
      {/* A marca (logo) e o controle de recolher/expandir/fechar subiram pro
          GlobalHeader, sempre visível acima da sidebar — aqui fica só o
          menu em si. */}
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
