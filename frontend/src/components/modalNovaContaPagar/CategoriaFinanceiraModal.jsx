import { X } from "lucide-react";
import CategoriaSubcategoriasFields from "./CategoriaSubcategoriasFields";

const ICONES_CATEGORIA = ["💸", "🏠", "⚡", "💧", "👥", "📦", "🔧", "🚗", "🍽️", "📝", "🛡️", "🛒"];

export default function CategoriaFinanceiraModal({
  formCategoria,
  isOpen,
  onAdicionarSubcategoria,
  onClose,
  onKeyDownSubcategoria,
  onRemoverSubcategoria,
  onSubmit,
  onUpdateSubcategoria,
  setFormCategoria,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-gray-800">Nova Categoria Financeira</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome da Categoria *
            </label>
            <input
              type="text"
              value={formCategoria.nome}
              onChange={(event) => setFormCategoria({ ...formCategoria, nome: event.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              required
              placeholder="Ex: Fornecedores, Aluguel, Salários..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ícone</label>
              <select
                value={formCategoria.icone}
                onChange={(event) =>
                  setFormCategoria({ ...formCategoria, icone: event.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                {ICONES_CATEGORIA.map((icone) => (
                  <option key={icone} value={icone}>
                    {icone}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cor</label>
              <input
                type="color"
                value={formCategoria.cor}
                onChange={(event) =>
                  setFormCategoria({ ...formCategoria, cor: event.target.value })
                }
                className="w-full h-10 border border-gray-300 rounded-md"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
            <textarea
              value={formCategoria.descricao}
              onChange={(event) =>
                setFormCategoria({ ...formCategoria, descricao: event.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows="2"
            />
          </div>

          <CategoriaSubcategoriasFields
            formCategoria={formCategoria}
            onAdicionarSubcategoria={onAdicionarSubcategoria}
            onKeyDownSubcategoria={onKeyDownSubcategoria}
            onRemoverSubcategoria={onRemoverSubcategoria}
            onUpdateSubcategoria={onUpdateSubcategoria}
          />

          <div className="flex gap-3 justify-end pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Criar Categoria
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
