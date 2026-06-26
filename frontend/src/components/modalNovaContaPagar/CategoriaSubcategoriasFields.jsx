import { Plus, X } from "lucide-react";

export default function CategoriaSubcategoriasFields({
  formCategoria,
  onAdicionarSubcategoria,
  onKeyDownSubcategoria,
  onRemoverSubcategoria,
  onUpdateSubcategoria,
}) {
  return (
    <div className="border-t pt-4">
      <div className="flex items-center justify-between mb-2">
        <label className="block text-sm font-medium text-gray-700">
          Subcategorias DRE (opcional)
        </label>
        <button
          type="button"
          onClick={onAdicionarSubcategoria}
          className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <Plus size={14} /> Adicionar
        </button>
      </div>

      {formCategoria.novasSubcategorias.length > 0 && (
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {formCategoria.novasSubcategorias.map((subcategoria, index) => (
            <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded-md">
              <input
                type="text"
                value={subcategoria.nome}
                onChange={(event) => onUpdateSubcategoria(index, "nome", event.target.value)}
                onKeyDown={(event) => onKeyDownSubcategoria(event, index)}
                placeholder="Nome (Tab para adicionar mais)"
                className="flex-1 px-2 py-1 border border-gray-300 rounded-md text-sm"
              />
              <button
                type="button"
                onClick={() => onRemoverSubcategoria(index)}
                className="text-red-600 hover:text-red-800 p-1"
              >
                <X size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      {formCategoria.novasSubcategorias.length === 0 && (
        <p className="text-xs text-gray-500 italic">
          Aperte Tab no último campo para adicionar mais subcategorias
        </p>
      )}
    </div>
  );
}
