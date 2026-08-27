import { AlertTriangle, X } from "lucide-react";
import { safeArray } from "../../utils/safeArray";

export default function VincularCategoriaDREModal({
  categoria,
  isOpen,
  loading,
  onChange,
  onClose,
  onSubmit,
  subcategoriaId,
  subcategoriasDRE,
}) {
  if (!isOpen || !categoria) return null;

  const subcategoriasAtivas = safeArray(subcategoriasDRE).filter(
    (subcategoria) => subcategoria.ativo !== false,
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-[70]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between border-b p-5">
          <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <AlertTriangle className="text-amber-500" size={22} />
            Classificar categoria no DRE
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Fechar classificação DRE"
          >
            <X size={24} />
          </button>
        </div>

        <form onSubmit={onSubmit} className="p-5 space-y-5">
          <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            A categoria <strong>{categoria.nome}</strong> ainda não está vinculada ao DRE. Escolha
            abaixo onde as contas desta categoria devem aparecer.
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Subcategoria DRE *
            </label>
            <select
              value={subcategoriaId}
              onChange={(event) => onChange(event.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              required
              autoFocus
            >
              <option value="">Selecione a classificação...</option>
              {subcategoriasAtivas.map((subcategoria) => (
                <option key={subcategoria.id} value={subcategoria.id}>
                  {subcategoria.nome}
                </option>
              ))}
            </select>
            {subcategoriasAtivas.length === 0 && (
              <p className="text-sm text-red-600 mt-2">
                Nenhuma subcategoria DRE ativa foi encontrada. Cadastre primeiro o plano DRE.
              </p>
            )}
          </div>

          <p className="text-xs text-gray-500">
            O vínculo será salvo na categoria e usado automaticamente nas próximas contas.
          </p>

          <div className="flex justify-end gap-3 border-t pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !subcategoriaId || subcategoriasAtivas.length === 0}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Salvando..." : "Salvar vínculo"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
