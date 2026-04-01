export default function ProdutosNovoFornecedorModal({
  clientes,
  fornecedorData,
  fornecedorEdit,
  setFornecedorData,
  onClose,
  onSubmit,
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-xl font-bold text-gray-900 mb-4">
          {fornecedorEdit ? 'Editar Fornecedor' : 'Adicionar Fornecedor'}
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Fornecedor *</label>
            <select
              value={fornecedorData.fornecedor_id}
              onChange={(e) => setFornecedorData({ ...fornecedorData, fornecedor_id: e.target.value })}
              disabled={Boolean(fornecedorEdit)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            >
              <option value="">Selecione...</option>
              {clientes.map((cli) => (
                <option key={cli.id} value={cli.id}>
                  {cli.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Codigo no Fornecedor</label>
            <input
              type="text"
              value={fornecedorData.codigo_fornecedor}
              onChange={(e) => setFornecedorData({ ...fornecedorData, codigo_fornecedor: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="SKU-FORNECEDOR-001"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Preco de Custo</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
              <input
                type="number"
                step="0.01"
                value={fornecedorData.preco_custo}
                onChange={(e) => setFornecedorData({ ...fornecedorData, preco_custo: e.target.value })}
                className="w-full pl-12 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="0,00"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Prazo de Entrega (dias)</label>
            <input
              type="number"
              value={fornecedorData.prazo_entrega}
              onChange={(e) => setFornecedorData({ ...fornecedorData, prazo_entrega: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="7"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Estoque no Fornecedor</label>
            <input
              type="number"
              step="0.01"
              value={fornecedorData.estoque_fornecedor}
              onChange={(e) => setFornecedorData({ ...fornecedorData, estoque_fornecedor: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="100"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={fornecedorData.e_principal}
              onChange={(e) => setFornecedorData({ ...fornecedorData, e_principal: e.target.checked })}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <label className="text-sm font-medium text-gray-700">Fornecedor Principal</label>
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
            Salvar
          </button>
        </div>
      </div>
    </div>
  );
}
