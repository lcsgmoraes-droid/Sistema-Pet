import { FiPlus, FiTrash2 } from "react-icons/fi";

export default function CategoriaFinanceiraSubcategoriasFields({
  adicionarSubcategoriaNova,
  atualizarSubcategoriaNova,
  formData,
  handleKeyDownSubcategoria,
  removerSubcategoriaNova,
}) {
  return (
    <div className="border-t pt-4">
      <div className="flex items-center justify-between mb-3">
        <label className="block text-sm font-medium text-gray-700">
          Subcategorias DRE (opcional)
        </label>
        <button
          type="button"
          onClick={() => adicionarSubcategoriaNova()}
          className="text-sm text-purple-600 hover:text-purple-800 flex items-center gap-1"
        >
          <FiPlus size={14} /> Adicionar
        </button>
      </div>

      {formData.novasSubcategorias.length > 0 && (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {formData.novasSubcategorias.map((sub, index) => (
            <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded-md">
              <input
                type="text"
                value={sub.nome}
                onChange={(e) => atualizarSubcategoriaNova(index, "nome", e.target.value)}
                onKeyDown={(e) => handleKeyDownSubcategoria(e, index)}
                placeholder="Nome da subcategoria (Tab para adicionar mais)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => removerSubcategoriaNova(index)}
                className="text-red-600 hover:text-red-800 p-1"
                title="Remover"
              >
                <FiTrash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      {formData.novasSubcategorias.length === 0 && (
        <p className="text-sm text-gray-500 italic">
          Clique em "Adicionar" ou crie a categoria primeiro e depois adicione subcategorias
        </p>
      )}
    </div>
  );
}
