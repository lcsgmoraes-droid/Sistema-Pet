export default function ProdutosNovoLoteModal({
  loteEmEdicao,
  setLoteEmEdicao,
  onClose,
  onSubmit,
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-xl font-bold text-gray-900 mb-4">Editar Lote</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Lote *</label>
            <input
              type="text"
              value={loteEmEdicao.nome_lote}
              onChange={(e) => setLoteEmEdicao({ ...loteEmEdicao, nome_lote: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Nome do lote"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Quantidade *</label>
            <input
              type="number"
              step="0.01"
              value={loteEmEdicao.quantidade_inicial}
              onChange={(e) => setLoteEmEdicao({ ...loteEmEdicao, quantidade_inicial: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data de Fabricacao</label>
            <input
              type="date"
              value={loteEmEdicao.data_fabricacao}
              onChange={(e) => setLoteEmEdicao({ ...loteEmEdicao, data_fabricacao: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data de Validade</label>
            <input
              type="date"
              value={loteEmEdicao.data_validade}
              onChange={(e) => setLoteEmEdicao({ ...loteEmEdicao, data_validade: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Custo Unitario *</label>
            <input
              type="number"
              step="0.01"
              value={loteEmEdicao.custo_unitario}
              onChange={(e) => setLoteEmEdicao({ ...loteEmEdicao, custo_unitario: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0,00"
            />
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
          <button type="button" onClick={onSubmit} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Salvar Alteracoes
          </button>
        </div>
      </div>
    </div>
  );
}
