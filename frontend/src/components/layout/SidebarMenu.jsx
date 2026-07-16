import { FiChevronDown, FiChevronRight, FiLock, FiStar, FiUnlock } from "react-icons/fi";
import { Link } from "react-router-dom";
import TooltipPremium from "../TooltipPremium";

function ModuloMenuIndicator({
  modulo,
  devControlesAtivos,
  moduloAtivo,
  onToggleModuloDev,
  wrapperClassName,
  iconClassName,
  unlockedTitle,
  lockedTitle,
}) {
  if (!modulo) return null;

  if (devControlesAtivos) {
    return (
      <span
        role="button"
        tabIndex={0}
        onClick={(event) => onToggleModuloDev(event, modulo)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            onToggleModuloDev(event, modulo);
          }
        }}
        className={wrapperClassName}
        title="DEV: clicar para travar/destravar modulo"
      >
        {moduloAtivo(modulo) ? (
          <FiUnlock className={`${iconClassName} text-green-500`} title={unlockedTitle} />
        ) : (
          <FiLock className={`${iconClassName} text-amber-400`} title={lockedTitle} />
        )}
      </span>
    );
  }

  if (!moduloAtivo(modulo)) {
    return (
      <TooltipPremium modulo={modulo} placement="right">
        <FiLock className={`${iconClassName} text-amber-400`} aria-label="Módulo premium" />
      </TooltipPremium>
    );
  }

  return null;
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
  devControlesAtivos,
  moduloAtivo,
  onToggleModuloDev,
}) {
  return (
    <nav className="flex-1 py-2 md:py-4 overflow-y-auto overflow-x-hidden">
      {Array.isArray(menuItems) &&
        menuItems.map((item, index) => (
          <div key={item.path}>
            {item.section !== menuItems[index - 1]?.section && (
              <div
                className={
                  sidebarOpen
                    ? "px-4 pb-1 pt-4"
                    : "mx-4 my-3 border-t border-[#d8eee9] dark:border-slate-800"
                }
                aria-label={sidebarOpen ? item.section : undefined}
              >
                {sidebarOpen && (
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#4b7f7b] dark:text-slate-500">
                    {item.section}
                  </p>
                )}
              </div>
            )}
            {item.submenu ? (
              <>
                <button
                  onClick={() => onToggleSubmenu(item.path)}
                  className={`w-full flex items-center justify-between gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 mx-1 md:mx-2 rounded-lg transition-all text-sm md:text-base ${
                    currentPath.startsWith(item.path)
                      ? "bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm dark:from-cyan-500/15 dark:to-blue-500/15 dark:text-cyan-200"
                      : "text-gray-700 hover:bg-white/60 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  <div className="flex items-center gap-2 md:gap-3">
                    <item.icon className="text-base md:text-lg flex-shrink-0" />
                    {sidebarOpen && (
                      <span className="font-medium text-xs md:text-sm">{item.label}</span>
                    )}
                  </div>
                  {sidebarOpen &&
                    (item.modulo && devControlesAtivos ? (
                      <ModuloMenuIndicator
                        modulo={item.modulo}
                        devControlesAtivos={devControlesAtivos}
                        moduloAtivo={moduloAtivo}
                        onToggleModuloDev={onToggleModuloDev}
                        wrapperClassName="p-1 rounded hover:bg-white/70 dark:hover:bg-slate-800 cursor-pointer"
                        iconClassName="text-xs md:text-sm flex-shrink-0"
                      />
                    ) : item.modulo && !moduloAtivo(item.modulo) ? (
                      <ModuloMenuIndicator
                        modulo={item.modulo}
                        devControlesAtivos={devControlesAtivos}
                        moduloAtivo={moduloAtivo}
                        onToggleModuloDev={onToggleModuloDev}
                        wrapperClassName="p-1 rounded hover:bg-white/70 dark:hover:bg-slate-800 cursor-pointer"
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
                          >
                            {sidebarOpen && <span className="truncate">{subitem.label}</span>}
                            {!sidebarOpen && <span className="sr-only">{subitem.label}</span>}
                          </Link>
                          {subitem.modulo && sidebarOpen && (
                            <ModuloMenuIndicator
                              modulo={subitem.modulo}
                              devControlesAtivos={devControlesAtivos}
                              moduloAtivo={moduloAtivo}
                              onToggleModuloDev={onToggleModuloDev}
                              wrapperClassName="p-1 rounded hover:bg-white/80 dark:hover:bg-slate-700 ml-auto cursor-pointer"
                              iconClassName="w-3 h-3 flex-shrink-0"
                            />
                          )}
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
                className={`flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 mx-1 md:mx-2 my-0.5 md:my-1 rounded-lg transition-all text-sm md:text-base ${
                  isActive(item.path)
                    ? "bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm dark:from-cyan-500/15 dark:to-blue-500/15 dark:text-cyan-200"
                    : "text-gray-700 hover:bg-white/60 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                <Link
                  to={item.path}
                  onClick={onMenuClick}
                  className="flex min-w-0 flex-1 items-center gap-2 md:gap-3"
                  title={!sidebarOpen ? item.label : ""}
                >
                  <item.icon className="text-base md:text-lg flex-shrink-0" />
                  {sidebarOpen && (
                    <span className="truncate font-medium text-xs md:text-sm">{item.label}</span>
                  )}
                </Link>
                {sidebarOpen && (
                  <div className="flex shrink-0 items-center gap-1">
                    {item.modulo ? (
                      <ModuloMenuIndicator
                        modulo={item.modulo}
                        devControlesAtivos={devControlesAtivos}
                        moduloAtivo={moduloAtivo}
                        onToggleModuloDev={onToggleModuloDev}
                        wrapperClassName="p-1 rounded hover:bg-white/80 dark:hover:bg-slate-700 cursor-pointer"
                        iconClassName="w-3 h-3 flex-shrink-0"
                        unlockedTitle="Modulo liberado em DEV"
                        lockedTitle="Modulo bloqueado"
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
  );
}
