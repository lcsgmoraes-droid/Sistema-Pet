import React from "react";

export default function ProdutosEdicaoLoteModal({
  categorias,
  dadosEdicaoLote,
  departamentos,
  isOpen,
  marcas,
  onClose,
  onSalvar,
  selecionadosCount,
  setDadosEdicaoLote,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-900">Editar em Lote</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Atualizar <strong>{selecionadosCount}</strong> produto(s) selecionado(s)
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Marca</label>
            <select
              value={dadosEdicaoLote.marca_id}
              onChange={(event) =>
                setDadosEdicaoLote({
                  ...dadosEdicaoLote,
                  marca_id: event.target.value,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Nao alterar</option>
              {marcas.map((marca) => (
                <option key={marca.id} value={marca.id}>
                  {marca.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Categoria</label>
            <select
              value={dadosEdicaoLote.categoria_id}
              onChange={(event) =>
                setDadosEdicaoLote({
                  ...dadosEdicaoLote,
                  categoria_id: event.target.value,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Nao alterar</option>
              {categorias.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.categoria_pai_id ? "  -> " : ""}
                  {cat.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Departamento
            </label>
            <select
              value={dadosEdicaoLote.departamento_id}
              onChange={(event) =>
                setDadosEdicaoLote({
                  ...dadosEdicaoLote,
                  departamento_id: event.target.value,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Nao alterar</option>
              {departamentos.map((dep) => (
                <option key={dep.id} value={dep.id}>
                  {dep.nome}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onSalvar}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Salvar Alteracoes
          </button>
        </div>
      </div>
    </div>
  );
}
