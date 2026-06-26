import { normalizeDisplayText } from "./categoriasFinanceirasUtils";

export default function SubcategoriaDREModal({
  categorias,
  closeSubcategoriaModal,
  editandoSub,
  formSubData,
  handleSubmitSub,
  setFormSubData,
  showSubModal,
}) {
  if (!showSubModal) return null;

  const categoriaPai = categorias.find((categoria) => categoria.id === formSubData.categoria_id);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">
          {editandoSub ? "Editar Subcategoria DRE" : "Nova Subcategoria DRE"}
        </h2>

        {formSubData.categoria_id && categoriaPai && (
          <div className="mb-4 p-3 bg-blue-50 rounded-md border border-blue-200">
            <span className="text-sm text-gray-600">Categoria: </span>
            <span className="font-semibold text-gray-800">
              {normalizeDisplayText(categoriaPai.nome)}
            </span>
          </div>
        )}

        <form onSubmit={handleSubmitSub}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome da Subcategoria *
            </label>
            <input
              type="text"
              value={formSubData.nome}
              onChange={(e) => setFormSubData({ ...formSubData, nome: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">DescriÃ§Ã£o</label>
            <textarea
              value={formSubData.descricao}
              onChange={(e) => setFormSubData({ ...formSubData, descricao: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows="3"
            />
          </div>

          <div className="mb-6">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formSubData.ativo}
                onChange={(e) => setFormSubData({ ...formSubData, ativo: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-gray-700">Ativo</span>
            </label>
          </div>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={closeSubcategoriaModal}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              {editandoSub ? "Atualizar" : "Criar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
