import { FiCreditCard, FiHelpCircle, FiLogOut, FiMenu, FiX } from "react-icons/fi";
import { Link } from "react-router-dom";

import SidebarMenu from "./SidebarMenu";

const COREPET_LOGO = "/brand/corepet/corepet-horizontal.png";

export default function LayoutSidebar({
  isMobile,
  sidebarOpen,
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
  return (
    <aside
      className={`${
        isMobile
          ? `erp-mobile-sidebar fixed inset-y-0 left-0 z-50 w-64 max-w-[calc(100vw-24px)] transform overflow-hidden transition-transform duration-300 ${
              sidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`
          : `${sidebarOpen ? "w-64" : "w-20"} transition-all duration-300`
      } erp-sidebar bg-gradient-to-b from-[#f4fbfa] to-[#fff8ea] border-r border-[#d8eee9] flex flex-col shadow-lg`}
    >
      <div
        className={`p-4 flex items-center border-b border-[#d8eee9] bg-white/70 ${!isMobile && !sidebarOpen ? "justify-center" : "justify-between"}`}
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
              <p className="mt-1 text-xs text-gray-500">Central de Gestao</p>
              {devControlesAtivos && sidebarOpen && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[#0f8b8d]">
                    DEV modulos: {getModoDevLabel()}
                  </p>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => definirModoDevModulos("normal")}
                      className={`px-2 py-1 rounded text-[10px] border ${
                        devModoModulos === "normal"
                          ? "bg-[#d8eee9] border-[#b9ddd8] text-[#0f5f63]"
                          : "bg-white/70 border-gray-200 text-gray-500"
                      }`}
                    >
                      Normal
                    </button>
                    <button
                      onClick={() => definirModoDevModulos("all_unlocked")}
                      className={`px-2 py-1 rounded text-[10px] border ${
                        devModoModulos === "all_unlocked"
                          ? "bg-green-100 border-green-200 text-green-700"
                          : "bg-white/70 border-gray-200 text-gray-500"
                      }`}
                    >
                      Liberar tudo
                    </button>
                    <button
                      onClick={() => definirModoDevModulos("all_locked")}
                      className={`px-2 py-1 rounded text-[10px] border ${
                        devModoModulos === "all_locked"
                          ? "bg-amber-100 border-amber-200 text-amber-700"
                          : "bg-white/70 border-gray-200 text-gray-500"
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
            className="p-2 hover:bg-[#d8eee9] rounded-lg transition-colors"
            title={isMobile ? "Fechar menu" : "Esconder menu completamente"}
          >
            {isMobile ? (
              <FiX className="w-6 h-6 text-[#0f5f63]" />
            ) : (
              <FiX className="w-5 h-5 text-[#0f5f63]" />
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

      <div className="border-t border-[#d8eee9] bg-white/40">
        <Link
          to="/meu-plano"
          onClick={handleMenuClick}
          className="w-full flex items-center gap-3 px-4 py-2.5 mx-2 mt-2 rounded-lg text-emerald-700 hover:bg-emerald-50 transition-all"
          title={!sidebarOpen ? "Meu Plano" : ""}
        >
          <FiCreditCard className="text-lg flex-shrink-0" />
          {sidebarOpen && <span className="font-medium text-sm">Meu Plano</span>}
        </Link>
        <Link
          to="/ajuda"
          onClick={handleMenuClick}
          className="w-full flex items-center gap-3 px-4 py-2.5 mx-2 mt-1 rounded-lg text-[#0f5f63] hover:bg-[#d8eee9] transition-all"
          title={!sidebarOpen ? "Ajuda & Planos" : ""}
        >
          <FiHelpCircle className="text-lg flex-shrink-0" />
          {sidebarOpen && <span className="font-medium text-sm">Ajuda & Planos</span>}
        </Link>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-3 mx-2 my-2 rounded-lg text-gray-700 hover:bg-red-50 hover:text-red-600 transition-all text-left"
          title={!sidebarOpen ? "Sair" : ""}
        >
          <FiLogOut className="text-lg" />
          {sidebarOpen && <span className="font-medium text-sm">Sair</span>}
        </button>
      </div>
    </aside>
  );
}
