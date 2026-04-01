export default function ProdutosNovoEntradaModal({
  entradaData,
  setEntradaData,
  onClose,
  onSubmit,
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Nova Entrada de Estoque</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Quantidade *</label>
            <input
              type="number"
              step="0.01"
              value={entradaData.quantidade}
              onChange={(e) => setEntradaData({ ...entradaData, quantidade: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1 flex justify-between items-center">
              <span>Numero do Lote</span>
              <button
                type="button"
                onClick={() => {
                  const sugestao = `LOTE-${new Date().toISOString().split('T')[0].replace(/-/g, '')}-${Math.floor(
                    Math.random() * 1000
                  )
                    .toString()
                    .padStart(3, '0')}`;
                  setEntradaData({ ...entradaData, nome_lote: sugestao });
                }}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                Gerar Sugestao
              </button>
            </label>
            <input
              type="text"
              value={entradaData.nome_lote}
              onChange={(e) => setEntradaData({ ...entradaData, nome_lote: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Ex: LOTE-20260105-001 (deixe vazio para gerar automaticamente)"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data de Fabricacao</label>
            <input
              type="date"
              value={entradaData.data_fabricacao}
              onChange={(e) => setEntradaData({ ...entradaData, data_fabricacao: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data de Validade</label>
            <input
              type="date"
              value={entradaData.data_validade}
              onChange={(e) => setEntradaData({ ...entradaData, data_validade: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Preco de Custo *</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
              <input
                type="number"
                step="0.01"
                value={entradaData.preco_custo}
                onChange={(e) => setEntradaData({ ...entradaData, preco_custo: e.target.value })}
                className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0,00"
              />
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button type="button" onClick={onSubmit} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
            Registrar Entrada
          </button>
        </div>
      </div>
    </div>
  );
}
