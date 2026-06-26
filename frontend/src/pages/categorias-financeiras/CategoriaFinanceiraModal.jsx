import CategoriaFinanceiraFormFields from "./CategoriaFinanceiraFormFields";
import CategoriaFinanceiraSubcategoriasFields from "./CategoriaFinanceiraSubcategoriasFields";

export default function CategoriaFinanceiraModal({
  adicionarSubcategoriaNova,
  atualizarSubcategoriaNova,
  closeCategoriaModal,
  colors,
  editando,
  formData,
  handleKeyDownSubcategoria,
  handleSubmit,
  icons,
  removerSubcategoriaNova,
  setFormData,
  showModal,
}) {
  if (!showModal) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
        <div className="flex justify-between items-center p-6 border-b">
          <h3 className="text-xl font-bold">{editando ? "Editar Categoria" : "Nova Categoria"}</h3>
          <button onClick={closeCategoriaModal} className="text-gray-500 hover:text-gray-700">
            âœ•
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <CategoriaFinanceiraFormFields
            colors={colors}
            editando={editando}
            formData={formData}
            icons={icons}
            setFormData={setFormData}
          />
          <CategoriaFinanceiraSubcategoriasFields
            adicionarSubcategoriaNova={adicionarSubcategoriaNova}
            atualizarSubcategoriaNova={atualizarSubcategoriaNova}
            formData={formData}
            handleKeyDownSubcategoria={handleKeyDownSubcategoria}
            removerSubcategoriaNova={removerSubcategoriaNova}
          />

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={closeCategoriaModal}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              {editando ? "Atualizar" : "Criar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
