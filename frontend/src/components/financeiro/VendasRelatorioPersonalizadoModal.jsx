export default function VendasRelatorioPersonalizadoModal({
  aberto,
  colunasDisponiveis,
  colunasRelatorio,
  exportarRelatorioListaVendas,
  ordenacaoRelatorio,
  setModalRelatorioAberto,
  setOrdenacaoRelatorio,
  toggleColunaRelatorio,
}) {
  if (!aberto) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Relatorio Personalizado - Lista de Vendas
          </h3>
          <button
            onClick={() => setModalRelatorioAberto(false)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <span className="text-2xl leading-none">x</span>
          </button>
        </div>

        <div className="px-6 py-4 max-h-[60vh] overflow-y-auto space-y-4">
          <div>
            <label
              htmlFor="ordenacao-relatorio-vendas"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Ordem
            </label>
            <select
              id="ordenacao-relatorio-vendas"
              value={ordenacaoRelatorio}
              onChange={(event) => setOrdenacaoRelatorio(event.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="data_desc">Data (mais recente primeiro)</option>
              <option value="data_asc">Data (mais antiga primeiro)</option>
              <option value="bruta_desc">Venda bruta (maior para menor)</option>
              <option value="bruta_asc">Venda bruta (menor para maior)</option>
              <option value="lucro_desc">Lucro (maior para menor)</option>
              <option value="lucro_asc">Lucro (menor para maior)</option>
            </select>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Colunas</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {colunasDisponiveis.map((coluna) => (
                <label
                  key={coluna.key}
                  className="flex items-center gap-2 p-2 rounded hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={colunasRelatorio.includes(coluna.key)}
                    onChange={() => toggleColunaRelatorio(coluna.key)}
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
            onClick={() => setModalRelatorioAberto(false)}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={() => {
              exportarRelatorioListaVendas({ escopo: "filtrado" });
              setModalRelatorioAberto(false);
            }}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
          >
            Gerar relatorio
          </button>
        </div>
      </div>
    </div>
  );
}
