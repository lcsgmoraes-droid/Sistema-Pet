import React from "react";
import { FiHelpCircle } from "react-icons/fi";

export default function ProdutosHeaderActions({
  abrirModalColunas,
  iniciarTour,
  menuRelatoriosAberto,
  menuRelatoriosRef,
  navigate,
  onExcluirSelecionados,
  onGerarRelatorioFiltrado,
  onGerarRelatorioGeral,
  onOpenEdicaoLote,
  onOpenImportacao,
  onOpenModalRelatorio,
  onToggleMenuRelatorios,
  selecionadosCount,
}) {
  return (
    <div className="mb-4 flex flex-col gap-3 md:mb-6 lg:flex-row lg:items-start lg:justify-between">
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Produtos</h1>
          <p className="mt-1 text-sm text-gray-600 md:text-base">
            Gerencie seu estoque de produtos
          </p>
        </div>
        <button
          onClick={iniciarTour}
          title="Ver tour guiado desta pagina"
          className="flex items-center gap-1 px-2 py-1 text-sm text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors mt-1"
        >
          <FiHelpCircle className="text-base" />
          <span className="hidden sm:inline text-xs">Tour</span>
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {selecionadosCount > 0 && (
          <>
            <button
              onClick={onOpenEdicaoLote}
              className="px-3 py-2 text-sm text-white rounded-xl bg-emerald-600 hover:bg-emerald-700 shadow-sm hover:shadow-md transition-all duration-200 border border-emerald-500 md:px-4"
            >
              Editar em Lote ({selecionadosCount})
            </button>
            <button
              onClick={onExcluirSelecionados}
              className="px-3 py-2 text-sm text-white rounded-xl bg-red-600 hover:bg-red-700 shadow-sm hover:shadow-md transition-all duration-200 border border-red-500 md:px-4"
            >
              Excluir Selecionados ({selecionadosCount})
            </button>
          </>
        )}
        <button
          id="tour-produtos-importar"
          onClick={onOpenImportacao}
          className="px-3 py-2 text-sm text-white rounded-xl bg-sky-600 hover:bg-sky-700 shadow-sm hover:shadow-md transition-all duration-200 border border-sky-500 font-medium flex items-center gap-2 md:px-4"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          Importar Excel
        </button>
        <button
          onClick={abrirModalColunas}
          className="px-3 py-2 text-sm text-slate-700 rounded-xl bg-white hover:bg-slate-50 shadow-sm hover:shadow-md transition-all duration-200 border border-slate-300 font-medium flex items-center gap-2 md:px-4"
          title="Configurar colunas visiveis"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          Colunas
        </button>
        <div className="relative" ref={menuRelatoriosRef}>
          <button
            onClick={onToggleMenuRelatorios}
            className="px-3 py-2 text-sm text-indigo-700 rounded-xl bg-indigo-50 hover:bg-indigo-100 shadow-sm hover:shadow-md transition-all duration-200 border border-indigo-200 font-medium md:px-4"
          >
            Relatorios
          </button>

          {menuRelatoriosAberto && (
            <div className="absolute right-0 z-40 mt-2 w-[calc(100vw-2rem)] max-w-72 rounded-lg border border-gray-200 bg-white shadow-lg">
              <button
                onClick={onGerarRelatorioGeral}
                className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50"
              >
                Relatorio geral (todos os produtos)
              </button>
              <button
                onClick={onGerarRelatorioFiltrado}
                className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
              >
                Relatorio do que filtrei
              </button>
              <button
                onClick={onOpenModalRelatorio}
                className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 border-t border-gray-100"
              >
                Relatorio personalizado
              </button>
            </div>
          )}
        </div>
        <button
          id="tour-produtos-novo"
          onClick={() => navigate("/produtos/novo")}
          className="px-3 py-2 text-sm text-white rounded-xl bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow-md transition-all duration-200 border border-blue-500 font-medium md:px-4"
        >
          + Novo Produto
        </button>
      </div>
    </div>
  );
}
