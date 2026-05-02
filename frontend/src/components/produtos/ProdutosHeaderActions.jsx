import React from "react";
import { FiHelpCircle } from "react-icons/fi";
import { FileText, Pencil, Plus, Settings, Trash2, UploadCloud } from "lucide-react";
import ActionButton from "../ui/ActionButton";

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
            <ActionButton
              onClick={onOpenEdicaoLote}
              intent="edit"
              tone="solid"
              size="md"
              icon={Pencil}
              className="shadow-sm hover:shadow-md"
            >
              Editar em Lote ({selecionadosCount})
            </ActionButton>
            <ActionButton
              onClick={onExcluirSelecionados}
              intent="delete"
              tone="solid"
              size="md"
              icon={Trash2}
              className="shadow-sm hover:shadow-md"
            >
              Excluir Selecionados ({selecionadosCount})
            </ActionButton>
          </>
        )}
        <ActionButton
          id="tour-produtos-importar"
          onClick={onOpenImportacao}
          intent="create"
          tone="solid"
          size="md"
          icon={UploadCloud}
          className="shadow-sm hover:shadow-md"
        >
          Importar Excel
        </ActionButton>
        <ActionButton
          onClick={abrirModalColunas}
          intent="neutral"
          tone="soft"
          size="md"
          icon={Settings}
          className="bg-white shadow-sm hover:shadow-md"
          title="Configurar colunas visiveis"
        >
          Colunas
        </ActionButton>
        <div className="relative" ref={menuRelatoriosRef}>
          <ActionButton
            onClick={onToggleMenuRelatorios}
            intent="neutral"
            tone="soft"
            size="md"
            icon={FileText}
            className="bg-white shadow-sm hover:shadow-md"
          >
            Relatorios
          </ActionButton>

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
        <ActionButton
          id="tour-produtos-novo"
          onClick={() => navigate("/produtos/novo")}
          intent="create"
          tone="solid"
          size="md"
          icon={Plus}
          className="shadow-sm hover:shadow-md"
        >
          Novo Produto
        </ActionButton>
      </div>
    </div>
  );
}
