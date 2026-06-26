import CategoriaFinanceiraModal from "./CategoriaFinanceiraModal";
import CategoriasFinanceirasFilters from "./CategoriasFinanceirasFilters";
import CategoriasFinanceirasHeader from "./CategoriasFinanceirasHeader";
import CategoriasFinanceirasList from "./CategoriasFinanceirasList";
import SubcategoriaDREModal from "./SubcategoriaDREModal";
import { useCategoriasFinanceirasController } from "./useCategoriasFinanceirasController";

export default function CategoriasFinanceirasPage() {
  const controller = useCategoriasFinanceirasController();

  return (
    <div className="p-6">
      <CategoriasFinanceirasHeader
        countDespesas={controller.countDespesas}
        countReceitas={controller.countReceitas}
        onNewCategory={controller.openCategoriaModal}
      />

      <CategoriasFinanceirasFilters
        countDespesas={controller.countDespesas}
        countReceitas={controller.countReceitas}
        filtroTipo={controller.filtroTipo}
        onFiltroTipoChange={controller.setFiltroTipo}
        totalCategorias={controller.categorias.length}
      />

      <CategoriasFinanceirasList
        categorias={controller.categorias}
        categoriasFiltradas={controller.categoriasFiltradas}
        categoriaExpandida={controller.categoriaExpandida}
        getSubcategoriasDREDaCategoria={controller.getSubcategoriasDREDaCategoria}
        handleDelete={controller.handleDelete}
        handleEdit={controller.handleEdit}
        handleQuickCustoPeDRE={controller.handleQuickCustoPeDRE}
        handleQuickTipoCusto={controller.handleQuickTipoCusto}
        loading={controller.loading}
        toggleExpansao={controller.toggleExpansao}
      />

      <CategoriaFinanceiraModal
        adicionarSubcategoriaNova={controller.adicionarSubcategoriaNova}
        atualizarSubcategoriaNova={controller.atualizarSubcategoriaNova}
        closeCategoriaModal={controller.closeCategoriaModal}
        colors={controller.colors}
        editando={controller.editando}
        formData={controller.formData}
        handleKeyDownSubcategoria={controller.handleKeyDownSubcategoria}
        handleSubmit={controller.handleSubmit}
        icons={controller.icons}
        removerSubcategoriaNova={controller.removerSubcategoriaNova}
        setFormData={controller.setFormData}
        showModal={controller.showModal}
      />

      <SubcategoriaDREModal
        categorias={controller.categorias}
        closeSubcategoriaModal={controller.closeSubcategoriaModal}
        editandoSub={controller.editandoSub}
        formSubData={controller.formSubData}
        handleSubmitSub={controller.handleSubmitSub}
        setFormSubData={controller.setFormSubData}
        showSubModal={controller.showSubModal}
      />
    </div>
  );
}
