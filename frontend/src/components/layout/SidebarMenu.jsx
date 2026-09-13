import { FiChevronDown, FiChevronRight, FiLock, FiStar } from "react-icons/fi";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import TooltipPremium from "../TooltipPremium";

function useSidebarHoverHint(sidebarOpen) {
  const [hint, setHint] = useState(null);
  const timerRef = useRef(null);

  useEffect(
    () => () => {
      window.clearTimeout(timerRef.current);
    },
    [],
  );

  const show = (event, label) => {
    window.clearTimeout(timerRef.current);
    setHint(null);

    const target = event.currentTarget;
    const text = target.querySelector("[data-sidebar-label]");
    const textIsTruncated = text && text.scrollWidth > text.clientWidth + 1;
    if (sidebarOpen && !textIsTruncated) return;

    const rect = target.getBoundingClientRect();
    timerRef.current = window.setTimeout(() => {
      setHint({
        label,
        left: Math.round(rect.right + 10),
        top: Math.round(rect.top + rect.height / 2),
      });
    }, 140);
  };

  const hide = () => {
    window.clearTimeout(timerRef.current);
    setHint(null);
  };

  const portal =
    hint && typeof document !== "undefined"
      ? createPortal(
          <div
            role="tooltip"
            style={{ left: hint.left, top: hint.top }}
            className="pointer-events-none fixed z-[140] max-w-sm -translate-y-1/2 rounded-lg border border-slate-700/10 bg-slate-900 px-3 py-2 text-sm font-semibold text-white shadow-xl dark:border-slate-600 dark:bg-slate-100 dark:text-slate-900"
          >
            {hint.label}
          </div>,
          document.body,
        )
      : null;

  return { show, hide, portal };
}

function ModuloMenuIndicator({ modulo, moduloAtivo, iconClassName }) {
  if (!modulo || moduloAtivo(modulo)) return null;

  return (
    <TooltipPremium modulo={modulo} placement="right">
      <FiLock className={`${iconClassName} text-amber-400`} aria-label="Módulo premium" />
    </TooltipPremium>
  );
}

function FavoriteToggle({ item, active, onToggleFavorite, className = "" }) {
  if (!onToggleFavorite || !item?.path) return null;

  const label = active
    ? `Remover ${item.label} dos favoritos`
    : `Adicionar ${item.label} aos favoritos`;

  return (
    <button
      type="button"
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onToggleFavorite(item);
      }}
      className={`rounded p-1 transition-colors ${
        active
          ? "text-amber-500 hover:bg-amber-50 dark:text-amber-300 dark:hover:bg-amber-500/10"
          : "text-gray-300 hover:bg-white/70 hover:text-amber-500 dark:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-amber-300"
      } ${className}`}
      title={label}
      aria-label={label}
      aria-pressed={active}
    >
      <FiStar className={`h-3.5 w-3.5 ${active ? "fill-current" : ""}`} />
    </button>
  );
}

function favoriteItem(item, fallback) {
  return {
    ...item,
    iconKey: item.iconKey ?? fallback?.iconKey,
    icon: item.icon ?? fallback?.icon,
  };
}

// Com a sidebar recolhida não há espaço pra expandir o submenu inline (é só um rail de ícones) —
// clicar num item com submenu abre esse popup flutuante ao lado, com a mesma lista de subitens.
function useSidebarFlyout(sidebarOpen) {
  const [flyout, setFlyout] = useState(null);
  const flyoutRef = useRef(null);

  useEffect(() => {
    if (sidebarOpen) setFlyout(null);
  }, [sidebarOpen]);

  useEffect(() => {
    if (!flyout) return undefined;

    const aoClicarFora = (evento) => {
      if (flyoutRef.current?.contains(evento.target)) return;
      if (evento.target.closest?.("[data-submenu-trigger]")) return;
      setFlyout(null);
    };
    const aoPressionarTecla = (evento) => {
      if (evento.key === "Escape") setFlyout(null);
    };

    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoPressionarTecla);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoPressionarTecla);
    };
  }, [flyout]);

  useEffect(() => {
    if (!flyout) return;
    flyoutRef.current?.querySelector("a,button")?.focus();
  }, [flyout]);

  const toggle = (event, item) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setFlyout((atual) =>
      atual?.item.path === item.path
        ? null
        : { item, left: Math.round(rect.right + 10), top: Math.round(rect.top) },
    );
  };

  const close = () => setFlyout(null);

  return { flyout, flyoutRef, toggle, close };
}

export default function SidebarMenu({
  menuItems,
  sidebarOpen,
  submenusOpen,
  currentPath,
  isActive,
  onToggleSubmenu,
  onMenuClick,
  favoritePaths,
  onToggleFavorite,
  moduloAtivo,
}) {
  const hoverHint = useSidebarHoverHint(sidebarOpen);
  const flyoutMenu = useSidebarFlyout(sidebarOpen);

  return (
    <>
      <nav className="flex-1 py-2 md:py-4 overflow-y-auto overflow-x-hidden">
        {Array.isArray(menuItems) &&
          menuItems.map((item, index) => (
            <div key={item.path}>
              {item.section !== menuItems[index - 1]?.section && (
                <div
                  className={
                    sidebarOpen
                      ? "px-4 pb-1 pt-4"
                      : "mx-2 my-3 border-t border-[#d8eee9] dark:border-slate-800"
                  }
                  aria-label={sidebarOpen ? item.section : undefined}
                >
                  {sidebarOpen && <p className="v2-menu-secao">{item.section}</p>}
                </div>
              )}
              {item.submenu ? (
                <>
                  <button
                    data-submenu-trigger
                    onClick={(event) =>
                      sidebarOpen ? onToggleSubmenu(item.path) : flyoutMenu.toggle(event, item)
                    }
                    onMouseEnter={(event) => hoverHint.show(event, item.label)}
                    onMouseLeave={hoverHint.hide}
                    onFocus={(event) => hoverHint.show(event, item.label)}
                    onBlur={hoverHint.hide}
                    title={item.label}
                    aria-label={sidebarOpen ? undefined : item.label}
                    aria-haspopup={sidebarOpen ? undefined : "menu"}
                    aria-expanded={sidebarOpen ? submenusOpen[item.path] : undefined}
                    className={`w-full flex items-center rounded-lg transition-all ${
                      sidebarOpen
                        ? "justify-between gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 mx-1 md:mx-2 text-sm md:text-base"
                        : "justify-center px-2 py-2.5 mx-2 text-sm"
                    } ${
                      currentPath.startsWith(item.path)
                        ? "bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm dark:from-cyan-500/15 dark:to-blue-500/15 dark:text-cyan-200"
                        : "text-gray-700 hover:bg-white/60 dark:text-slate-300 dark:hover:bg-slate-800"
                    }`}
                  >
                    <div className="flex items-center gap-2 md:gap-3">
                      <item.icon className="h-4 w-4 md:h-5 md:w-5 flex-shrink-0" />
                      {sidebarOpen && (
                        <span data-sidebar-label className="v2-menu-item min-w-0 font-medium">
                          {item.label}
                        </span>
                      )}
                    </div>
                    {sidebarOpen &&
                      (item.modulo && !moduloAtivo(item.modulo) ? (
                        <ModuloMenuIndicator
                          modulo={item.modulo}
                          moduloAtivo={moduloAtivo}
                          iconClassName="text-xs md:text-sm flex-shrink-0"
                        />
                      ) : submenusOpen[item.path] ? (
                        <FiChevronDown className="text-xs md:text-sm text-gray-400 dark:text-slate-500" />
                      ) : (
                        <FiChevronRight className="text-xs md:text-sm text-gray-400 dark:text-slate-500" />
                      ))}
                  </button>
                  {submenusOpen[item.path] && sidebarOpen && (
                    <div className="mt-1 mb-2 space-y-0.5 md:space-y-1">
                      {Array.isArray(item.submenu) &&
                        item.submenu.map((subitem) => (
                          <div
                            key={subitem.path}
                            onMouseEnter={(event) => hoverHint.show(event, subitem.label)}
                            onMouseLeave={hoverHint.hide}
                            className={`flex items-center gap-2 md:gap-3 px-3 md:px-4 py-1.5 md:py-2 mx-1 md:mx-2 ml-8 md:ml-12 rounded-lg transition-all text-xs md:text-sm ${
                              isActive(subitem.path)
                                ? "bg-white text-indigo-600 shadow-sm font-medium dark:bg-slate-800 dark:text-cyan-200"
                                : "text-gray-600 hover:bg-white/50 dark:text-slate-400 dark:hover:bg-slate-800"
                            }`}
                          >
                            <Link
                              to={subitem.path}
                              onClick={onMenuClick}
                              className="flex min-w-0 flex-1 items-center"
                              title={subitem.label}
                            >
                              {sidebarOpen && (
                                <span data-sidebar-label className="v2-menu-item">
                                  {subitem.label}
                                </span>
                              )}
                              {!sidebarOpen && <span className="sr-only">{subitem.label}</span>}
                            </Link>
                            {subitem.modulo && sidebarOpen && (
                              <ModuloMenuIndicator
                                modulo={subitem.modulo}
                                moduloAtivo={moduloAtivo}
                                iconClassName="w-3 h-3 flex-shrink-0"
                              />
                            )}
                            {sidebarOpen && subitem.badge ? (
                              <span
                                className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-orange-400"
                                title={subitem.badgeLabel || "Há itens pendentes"}
                                aria-label={subitem.badgeLabel || "Há itens pendentes"}
                              />
                            ) : null}
                            {sidebarOpen && (
                              <FavoriteToggle
                                item={favoriteItem(subitem, item)}
                                active={favoritePaths?.has(subitem.path)}
                                onToggleFavorite={onToggleFavorite}
                              />
                            )}
                          </div>
                        ))}
                    </div>
                  )}
                </>
              ) : (
                <div
                  onMouseEnter={(event) => hoverHint.show(event, item.label)}
                  onMouseLeave={hoverHint.hide}
                  className={`flex items-center rounded-lg transition-all my-0.5 md:my-1 ${
                    sidebarOpen
                      ? "gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 mx-1 md:mx-2 text-sm md:text-base"
                      : "justify-center px-2 py-2.5 mx-2 text-sm"
                  } ${
                    isActive(item.path)
                      ? "bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm dark:from-cyan-500/15 dark:to-blue-500/15 dark:text-cyan-200"
                      : "text-gray-700 hover:bg-white/60 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  <Link
                    to={item.path}
                    onClick={onMenuClick}
                    className={`flex items-center ${
                      sidebarOpen ? "min-w-0 flex-1 gap-2 md:gap-3" : "justify-center"
                    }`}
                    title={item.label}
                  >
                    <item.icon className="h-4 w-4 md:h-5 md:w-5 flex-shrink-0" />
                    {sidebarOpen && (
                      <span data-sidebar-label className="v2-menu-item font-medium">
                        {item.label}
                      </span>
                    )}
                  </Link>
                  {sidebarOpen && (
                    <div className="flex shrink-0 items-center gap-1">
                      {item.modulo ? (
                        <ModuloMenuIndicator
                          modulo={item.modulo}
                          moduloAtivo={moduloAtivo}
                          iconClassName="w-3 h-3 flex-shrink-0"
                        />
                      ) : item.badge ? (
                        <span className="w-2 h-2 bg-orange-400 rounded-full animate-pulse"></span>
                      ) : null}
                      <FavoriteToggle
                        item={favoriteItem(item)}
                        active={favoritePaths?.has(item.path)}
                        onToggleFavorite={onToggleFavorite}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
      </nav>
      {hoverHint.portal}
      {flyoutMenu.flyout &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            ref={flyoutMenu.flyoutRef}
            role="menu"
            aria-label={flyoutMenu.flyout.item.label}
            style={{ left: flyoutMenu.flyout.left, top: flyoutMenu.flyout.top }}
            className="fixed z-[130] max-h-[70vh] w-56 overflow-y-auto rounded-xl border border-[#d8eee9] bg-white py-1 shadow-lg dark:border-slate-800 dark:bg-slate-900"
          >
            <p className="v2-menu-secao px-3 pb-1 pt-2">{flyoutMenu.flyout.item.label}</p>
            {Array.isArray(flyoutMenu.flyout.item.submenu) &&
              flyoutMenu.flyout.item.submenu.map((subitem) => (
                <div
                  key={subitem.path}
                  className={`mx-1 flex items-center gap-2 rounded-lg px-2 py-1.5 transition-all ${
                    isActive(subitem.path)
                      ? "bg-indigo-50 font-medium text-indigo-600 dark:bg-slate-800 dark:text-cyan-200"
                      : "text-gray-600 hover:bg-gray-50 dark:text-slate-400 dark:hover:bg-slate-800"
                  }`}
                >
                  <Link
                    to={subitem.path}
                    role="menuitem"
                    onClick={() => {
                      flyoutMenu.close();
                      onMenuClick();
                    }}
                    className="flex min-w-0 flex-1 items-center"
                  >
                    <span className="v2-menu-item">{subitem.label}</span>
                  </Link>
                  {subitem.modulo && (
                    <ModuloMenuIndicator
                      modulo={subitem.modulo}
                      moduloAtivo={moduloAtivo}
                      iconClassName="w-3 h-3 flex-shrink-0"
                    />
                  )}
                  {subitem.badge ? (
                    <span
                      className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-orange-400"
                      title={subitem.badgeLabel || "Há itens pendentes"}
                      aria-label={subitem.badgeLabel || "Há itens pendentes"}
                    />
                  ) : null}
                  <FavoriteToggle
                    item={favoriteItem(subitem, flyoutMenu.flyout.item)}
                    active={favoritePaths?.has(subitem.path)}
                    onToggleFavorite={onToggleFavorite}
                  />
                </div>
              ))}
          </div>,
          document.body,
        )}
    </>
  );
}
