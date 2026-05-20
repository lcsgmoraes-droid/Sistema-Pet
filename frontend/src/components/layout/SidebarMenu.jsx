import {
  FiChevronDown,
  FiChevronRight,
  FiLock,
  FiUnlock,
} from "react-icons/fi";
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
          <FiUnlock
            className={`${iconClassName} text-green-500`}
            title={unlockedTitle}
          />
        ) : (
          <FiLock
            className={`${iconClassName} text-amber-400`}
            title={lockedTitle}
          />
        )}
      </span>
    );
  }

  if (!moduloAtivo(modulo)) {
    return (
      <TooltipPremium modulo={modulo} placement="right">
        <FiLock
          className={`${iconClassName} text-amber-400`}
          aria-label="Módulo premium"
        />
      </TooltipPremium>
    );
  }

  return null;
}

export default function SidebarMenu({
  menuItems,
  sidebarOpen,
  submenusOpen,
  currentPath,
  isActive,
  onToggleSubmenu,
  onMenuClick,
  devControlesAtivos,
  moduloAtivo,
  onToggleModuloDev,
}) {
  return (
    <nav className="flex-1 py-2 md:py-4 overflow-y-auto overflow-x-hidden">
      {Array.isArray(menuItems) &&
        menuItems.map((item) => (
          <div key={item.path}>
            {item.submenu ? (
              <>
                <button
                  onClick={() => onToggleSubmenu(item.path)}
                  className={`w-full flex items-center justify-between gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 mx-1 md:mx-2 rounded-lg transition-all text-sm md:text-base ${
                    currentPath.startsWith(item.path)
                      ? "bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm"
                      : "text-gray-700 hover:bg-white/60"
                  }`}
                >
                  <div className="flex items-center gap-2 md:gap-3">
                    <item.icon className="text-base md:text-lg flex-shrink-0" />
                    {sidebarOpen && (
                      <span className="font-medium text-xs md:text-sm">
                        {item.label}
                      </span>
                    )}
                  </div>
                  {sidebarOpen &&
                    (item.modulo && devControlesAtivos ? (
                      <ModuloMenuIndicator
                        modulo={item.modulo}
                        devControlesAtivos={devControlesAtivos}
                        moduloAtivo={moduloAtivo}
                        onToggleModuloDev={onToggleModuloDev}
                        wrapperClassName="p-1 rounded hover:bg-white/70 cursor-pointer"
                        iconClassName="text-xs md:text-sm flex-shrink-0"
                      />
                    ) : item.modulo && !moduloAtivo(item.modulo) ? (
                      <ModuloMenuIndicator
                        modulo={item.modulo}
                        devControlesAtivos={devControlesAtivos}
                        moduloAtivo={moduloAtivo}
                        onToggleModuloDev={onToggleModuloDev}
                        wrapperClassName="p-1 rounded hover:bg-white/70 cursor-pointer"
                        iconClassName="text-xs md:text-sm flex-shrink-0"
                      />
                    ) : submenusOpen[item.path] ? (
                      <FiChevronDown className="text-xs md:text-sm text-gray-400" />
                    ) : (
                      <FiChevronRight className="text-xs md:text-sm text-gray-400" />
                    ))}
                </button>
                {submenusOpen[item.path] && sidebarOpen && (
                  <div className="mt-1 mb-2 space-y-0.5 md:space-y-1">
                    {Array.isArray(item.submenu) &&
                      item.submenu.map((subitem) => (
                        <Link
                          key={subitem.path}
                          to={subitem.path}
                          onClick={onMenuClick}
                          className={`flex items-center gap-2 md:gap-3 px-3 md:px-4 py-1.5 md:py-2 mx-1 md:mx-2 ml-8 md:ml-12 rounded-lg transition-all text-xs md:text-sm ${
                            isActive(subitem.path)
                              ? "bg-white text-indigo-600 shadow-sm font-medium"
                              : "text-gray-600 hover:bg-white/50"
                          }`}
                        >
                          {sidebarOpen && <span>{subitem.label}</span>}
                          {!sidebarOpen && (
                            <span className="sr-only">{subitem.label}</span>
                          )}
                          {subitem.modulo && sidebarOpen && (
                            <ModuloMenuIndicator
                              modulo={subitem.modulo}
                              devControlesAtivos={devControlesAtivos}
                              moduloAtivo={moduloAtivo}
                              onToggleModuloDev={onToggleModuloDev}
                              wrapperClassName="p-1 rounded hover:bg-white/80 ml-auto cursor-pointer"
                              iconClassName="w-3 h-3 flex-shrink-0"
                            />
                          )}
                        </Link>
                      ))}
                  </div>
                )}
              </>
            ) : (
              <Link
                to={item.path}
                onClick={onMenuClick}
                className={`flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 mx-1 md:mx-2 my-0.5 md:my-1 rounded-lg transition-all text-sm md:text-base ${
                  isActive(item.path)
                    ? "bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 shadow-sm"
                    : "text-gray-700 hover:bg-white/60"
                }`}
                title={!sidebarOpen ? item.label : ""}
              >
                <item.icon className="text-base md:text-lg flex-shrink-0" />
                {sidebarOpen && (
                  <div className="flex items-center justify-between flex-1">
                    <span className="font-medium text-xs md:text-sm">
                      {item.label}
                    </span>
                    {item.modulo ? (
                      <ModuloMenuIndicator
                        modulo={item.modulo}
                        devControlesAtivos={devControlesAtivos}
                        moduloAtivo={moduloAtivo}
                        onToggleModuloDev={onToggleModuloDev}
                        wrapperClassName="p-1 rounded hover:bg-white/80 cursor-pointer"
                        iconClassName="w-3 h-3 flex-shrink-0"
                        unlockedTitle="Modulo liberado em DEV"
                        lockedTitle="Modulo bloqueado"
                      />
                    ) : item.badge ? (
                      <span className="w-2 h-2 bg-orange-400 rounded-full animate-pulse"></span>
                    ) : null}
                  </div>
                )}
              </Link>
            )}
          </div>
        ))}
    </nav>
  );
}
