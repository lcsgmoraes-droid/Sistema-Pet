import {
  FileText,
  GitMerge,
  Package,
  Pencil,
  Plus,
  Settings,
  Trash2,
  UploadCloud,
} from "lucide-react";
import ActionButton from "../ui/ActionButton";
import PageHeader from "../ui/PageHeader";

export default function ProdutosHeaderActions({
  abrirModalColunas,
  iniciarTour,
  menuRelatoriosAberto,
  menuRelatoriosRef,
  navigate,
  onExcluirSelecionados,
  onGerarRelatorioFiltrado,
  onGerarRelatorioGeral,
  onOpenFusao,
  onOpenEdicaoLote,
  onOpenImportacao,
  onOpenModalRelatorio,
  onToggleMenuRelatorios,
  selecionadosCount,
}) {
  const actionClassName = "w-full shadow-sm hover:shadow-md sm:w-auto";
  const secondaryActionClassName = "w-full bg-white shadow-sm hover:shadow-md sm:w-auto";

  const actions = (
    <>
      {selecionadosCount > 0 && (
        <>
          <ActionButton
            onClick={onOpenEdicaoLote}
            intent="edit"
            tone="solid"
            size="md"
            icon={Pencil}
            className={actionClassName}
          >
            Editar em Lote ({selecionadosCount})
          </ActionButton>
          {selecionadosCount === 2 && (
            <ActionButton
              onClick={onOpenFusao}
              intent="warning"
              tone="solid"
              size="md"
              icon={GitMerge}
              className={actionClassName}
            >
              Fundir Produtos
            </ActionButton>
          )}
          <ActionButton
            onClick={onExcluirSelecionados}
            intent="delete"
            tone="solid"
            size="md"
            icon={Trash2}
            className={actionClassName}
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
        className={actionClassName}
      >
        Importar Excel
      </ActionButton>
      <ActionButton
        onClick={abrirModalColunas}
        intent="neutral"
        tone="soft"
        size="md"
        icon={Settings}
        className={secondaryActionClassName}
        title="Configurar colunas visiveis"
      >
        Colunas
      </ActionButton>
      <div className="relative w-full sm:w-auto" ref={menuRelatoriosRef}>
        <ActionButton
          onClick={onToggleMenuRelatorios}
          intent="neutral"
          tone="soft"
          size="md"
          icon={FileText}
          className={secondaryActionClassName}
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
        className={actionClassName}
      >
        Novo Produto
      </ActionButton>
    </>
  );

  return (
    <PageHeader
      actions={actions}
      className="mb-4 md:mb-6"
      icon={Package}
      onTour={iniciarTour}
      subtitle="Gerencie seu estoque de produtos"
      title="Produtos"
    />
  );
}
