import React from "react";

export default function ProdutosRelatorioModal({
  colunasRelatorio,
  colunasRelatorioProdutos,
  isOpen,
  onClose,
  onGerarRelatorioPersonalizado,
  onToggleColunaRelatorio,
  ordenacaoRelatorio,
  setOrdenacaoRelatorio,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Relatorio Personalizado de Produtos
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
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

        <div className="px-6 py-4 max-h-[60vh] overflow-y-auto space-y-4">
          <div>
            <label
              htmlFor="ordenacao-relatorio-produtos"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Ordem do relatorio
            </label>
            <select
              id="ordenacao-relatorio-produtos"
              value={ordenacaoRelatorio}
              onChange={(event) => setOrdenacaoRelatorio(event.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="nome_asc">Nome (A-Z)</option>
              <option value="nome_desc">Nome (Z-A)</option>
              <option value="estoque_asc">Estoque (menor para maior)</option>
              <option value="estoque_desc">Estoque (maior para menor)</option>
              <option value="preco_asc">Preco venda (menor para maior)</option>
              <option value="preco_desc">Preco venda (maior para menor)</option>
            </select>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Colunas para exibir</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {colunasRelatorioProdutos.map((coluna) => (
                <label
                  key={coluna.key}
                  className="flex items-center gap-2 p-2 rounded hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={colunasRelatorio.includes(coluna.key)}
                    onChange={() => onToggleColunaRelatorio(coluna.key)}
                    className="w-4 h-4 text-indigo-600 rounded"
                  />
                  <span className="text-sm text-gray-700">{coluna.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={onGerarRelatorioPersonalizado}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
          >
            Gerar relatorio
          </button>
        </div>
      </div>
    </div>
  );
}
