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

// Caixa única para QUALQUER ícone de acessório à direita de um item de menu — estrela, seta de
// submenu ou cadeado de módulo bloqueado. Regra de ouro desta linha: nenhum desses três ícones
// pode aparecer "cru" (sem passar por aqui), porque foi exatamente isso que causou o
// desalinhamento entre estrela e seta antes — a estrela tinha padding próprio (p-1) e a seta
// era renderizada sem nenhum, então mesmo dentro de colunas de largura igual o ÍCONE em si
// ficava em posições x diferentes. Todo ícone de acessório tem exatamente o mesmo padding, sem
// exceção — é isso que garante o alinhamento, não a coluna por fora.
function MenuAcessorio({ as: Tag = "span", className = "", children, ...rest }) {
  return (
    <Tag
      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded p-1 transition-colors ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}

// Ponta (esquerda ou direita) da linha do menu: ícone de liderança de um lado, grupo de
// acessórios (MenuAcessorio, um ou mais) do outro. O label no meio é flex-1 e consome todo
// espaço sobrando, então a ponta da direita já cai exatamente na borda direita da linha sozinha
// — não precisa de largura fixa pra isso (uma largura fixa, na verdade, quebra o caso de dois
// acessórios juntos — cadeado + estrela não cabem os dois no mesmo tamanho que só a estrela).
// O alinhamento de verdade vem do MenuAcessorio ter o mesmo padding em todo lugar (ver lá).
function MenuColuna({ children, alinhar = "center", className = "" }) {
  const justify =
    alinhar === "end" ? "justify-end" : alinhar === "start" ? "justify-start" : "justify-center";
  return <span className={`flex shrink-0 items-center ${justify} ${className}`}>{children}</span>;
}

// Cadeado de módulo bloqueado — sempre dentro de MenuAcessorio, nunca cru (ver comentário lá).
function ModuloAcessorio({ modulo, moduloAtivo }) {
  if (!modulo || moduloAtivo(modulo)) return null;

  return (
    <MenuAcessorio>
      <TooltipPremium modulo={modulo} placement="right">
        <FiLock className="h-3.5 w-3.5 flex-shrink-0 text-amber-400" aria-label="Módulo premium" />
      </TooltipPremium>
    </MenuAcessorio>
  );
}

// Seta de expandir/recolher submenu — sempre dentro de MenuAcessorio, nunca cru.
function SubmenuAcessorio({ aberto }) {
  const Icone = aberto ? FiChevronDown : FiChevronRight;
  return (
    <MenuAcessorio>
      <Icone className="h-3.5 w-3.5 text-gray-400 dark:text-slate-500" />
    </MenuAcessorio>
  );
}

// Estrela de favorito — sempre dentro de MenuAcessorio (como botão, já que é clicável).
function FavoriteToggle({ item, active, onToggleFavorite, className = "" }) {
  if (!onToggleFavorite || !item?.path) return null;

  const label = active
    ? `Remover ${item.label} dos favoritos`
    : `Adicionar ${item.label} aos favoritos`;

  return (
    <MenuAcessorio
      as="button"
      type="button"
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onToggleFavorite(item);
      }}
      title={label}
      aria-label={label}
      aria-pressed={active}
      className={`${
        active
          ? "text-amber-500 hover:bg-amber-50 dark:text-amber-300 dark:hover:bg-amber-500/10"
          : "text-gray-300 hover:bg-white/70 hover:text-amber-500 dark:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-amber-300"
      } ${className}`}
    >
      <FiStar className={`h-3.5 w-3.5 ${active ? "fill-current" : ""}`} />
    </MenuAcessorio>
  );
}

function favoriteItem(item, fallback) {
  return {
    ...item,
    iconKey: item.iconKey ?? fallback?.iconKey,
    icon: item.icon ?? fallback?.icon,
  };
}

// Ícone de liderança (esquerda) do item — mesmo tamanho condicional (menor quando recolhido)
// usado em todo lugar que renderiza um ícone principal de item de menu.
function IconeItem({ icon: Icone, sidebarOpen }) {
  return (
    <Icone
      className={sidebarOpen ? "h-4 w-4 md:h-5 md:w-5 flex-shrink-0" : "h-4 w-4 flex-shrink-0"}
    />
  );
}

// Grupo de acessórios à direita de um item COM submenu: cadeado (se bloqueado) OU seta — nunca
// os dois juntos, o cadeado substitui a seta.
function AcessoriosSubmenu({ item, submenusOpen, moduloAtivo }) {
  const bloqueado = item.modulo && !moduloAtivo(item.modulo);
  return (
    <MenuColuna alinhar="end">
      {bloqueado ? (
        <ModuloAcessorio modulo={item.modulo} moduloAtivo={moduloAtivo} />
      ) : (
        <SubmenuAcessorio aberto={Boolean(submenusOpen[item.path])} />
      )}
    </MenuColuna>
  );
}

// Grupo de acessórios à direita de um item SEM submenu (folha): cadeado/badge (se aplicável) e
// sempre a estrela de favorito, lado a lado.
function AcessoriosItem({ item, moduloAtivo, favoritePaths, onToggleFavorite }) {
  return (
    <MenuColuna alinhar="end" className="gap-0.5">
      <ModuloAcessorio modulo={item.modulo} moduloAtivo={moduloAtivo} />
      {!item.modulo && item.badge ? (
        <span
          className="h-2 w-2 shrink-0 rounded-full bg-orange-400 motion-safe:animate-pulse"
          title={item.badgeLabel || "Há itens pendentes"}
          aria-label={item.badgeLabel || "Há itens pendentes"}
        />
      ) : null}
      <FavoriteToggle
        item={favoriteItem(item)}
        active={favoritePaths?.has(item.path)}
        onToggleFavorite={onToggleFavorite}
      />
    </MenuColuna>
  );
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
                  {/* O <button>, mesmo com display:flex, não encolhe/preenche como um <div> faria —
                      precisa de "w-full" pra ocupar a largura disponível. Mas w-full (100% do pai)
                      não desconta a própria margem, então a margem mx-1/mx-2 mora aqui fora, e o
                      botão é 100% desta div já "encolhida" — era essa combinação (w-full + margem
                      no mesmo elemento) que empurrava a seta ~16px além da borda da sidebar. */}
                  <div className={sidebarOpen ? "ml-1 md:ml-2 mr-1" : "mx-2"}>
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
                          ? "gap-2 md:gap-3 pl-3 md:pl-4 pr-2 py-2.5 md:py-3 text-sm md:text-base"
                          : "justify-center px-2 py-2.5 text-sm"
                      } ${
                        currentPath.startsWith(item.path)
                          ? "bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm dark:from-cyan-500/15 dark:to-blue-500/15 dark:text-cyan-200"
                          : "text-gray-700 hover:bg-white/60 dark:text-slate-300 dark:hover:bg-slate-800"
                      }`}
                    >
                      <MenuColuna alinhar={sidebarOpen ? "start" : "center"}>
                        <IconeItem icon={item.icon} sidebarOpen={sidebarOpen} />
                      </MenuColuna>
                      {sidebarOpen && (
                        <span
                          data-sidebar-label
                          className="v2-menu-item min-w-0 flex-1 text-left font-medium"
                        >
                          {item.label}
                        </span>
                      )}
                      {sidebarOpen && (
                        <AcessoriosSubmenu
                          item={item}
                          submenusOpen={submenusOpen}
                          moduloAtivo={moduloAtivo}
                        />
                      )}
                    </button>
                  </div>
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
                            {sidebarOpen && subitem.badge ? (
                              <span
                                className="h-2 w-2 shrink-0 rounded-full bg-orange-400 motion-safe:animate-pulse"
                                title={subitem.badgeLabel || "Há itens pendentes"}
                                aria-label={subitem.badgeLabel || "Há itens pendentes"}
                              />
                            ) : null}
                            {sidebarOpen && (
                              <MenuColuna alinhar="end" className="gap-0.5">
                                <ModuloAcessorio
                                  modulo={subitem.modulo}
                                  moduloAtivo={moduloAtivo}
                                />
                                <FavoriteToggle
                                  item={favoriteItem(subitem, item)}
                                  active={favoritePaths?.has(subitem.path)}
                                  onToggleFavorite={onToggleFavorite}
                                />
                              </MenuColuna>
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
                      ? "gap-2 md:gap-3 pl-3 md:pl-4 pr-2 py-2.5 md:py-3 ml-1 md:ml-2 mr-1 text-sm md:text-base"
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
                    <MenuColuna alinhar={sidebarOpen ? "start" : "center"}>
                      <IconeItem icon={item.icon} sidebarOpen={sidebarOpen} />
                    </MenuColuna>
                    {sidebarOpen && (
                      <span
                        data-sidebar-label
                        className="v2-menu-item min-w-0 flex-1 text-left font-medium"
                      >
                        {item.label}
                      </span>
                    )}
                  </Link>
                  {sidebarOpen && (
                    <AcessoriosItem
                      item={item}
                      moduloAtivo={moduloAtivo}
                      favoritePaths={favoritePaths}
                      onToggleFavorite={onToggleFavorite}
                    />
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
                  {subitem.badge ? (
                    <span
                      className="h-2 w-2 shrink-0 rounded-full bg-orange-400 motion-safe:animate-pulse"
                      title={subitem.badgeLabel || "Há itens pendentes"}
                      aria-label={subitem.badgeLabel || "Há itens pendentes"}
                    />
                  ) : null}
                  <MenuColuna alinhar="end" className="gap-0.5">
                    <ModuloAcessorio modulo={subitem.modulo} moduloAtivo={moduloAtivo} />
                    <FavoriteToggle
                      item={favoriteItem(subitem, flyoutMenu.flyout.item)}
                      active={favoritePaths?.has(subitem.path)}
                      onToggleFavorite={onToggleFavorite}
                    />
                  </MenuColuna>
                </div>
              ))}
          </div>,
          document.body,
        )}
    </>
  );
}
