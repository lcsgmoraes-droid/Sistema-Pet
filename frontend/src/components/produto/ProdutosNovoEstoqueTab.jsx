export default function ProdutosNovoEstoqueTab({
  formData,
  formatarData,
  formatarMoeda,
  handleChange,
  handleEditarLote,
  handleExcluirLote,
  isEdicao,
  lotes,
  setModalEntrada,
}) {
  return (
    <div className="space-y-6">
      {formData.tipo_produto === 'PAI' ? (
        <div className="text-center py-12 border-2 border-dashed border-blue-300 rounded-lg bg-blue-50">
          <svg className="mx-auto h-12 w-12 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
            />
          </svg>
          <p className="mt-4 text-lg font-medium text-blue-900">Produto com Variações</p>
          <p className="mt-2 text-sm text-blue-700">
            Produtos PAI não possuem estoque próprio.
            <br />
            O controle de estoque é feito individualmente nas variações.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.controle_lote}
                  onChange={(e) => handleChange('controle_lote', e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">Controlar Estoque</span>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estoque Mínimo</label>
              <input
                type="number"
                step="0.01"
                value={formData.estoque_minimo}
                onChange={(e) => handleChange('estoque_minimo', e.target.value)}
                disabled={!formData.controle_lote}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                placeholder="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Estoque Máximo</label>
              <input
                type="number"
                step="0.01"
                value={formData.estoque_maximo}
                onChange={(e) => handleChange('estoque_maximo', e.target.value)}
                disabled={!formData.controle_lote}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                placeholder="0"
              />
            </div>
          </div>

          {isEdicao && formData.controle_lote && (
            <>
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-900">Lotes (FIFO)</h3>
                <button
                  type="button"
                  onClick={() => setModalEntrada(true)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  + Nova Entrada
                </button>
              </div>

              {lotes.length === 0 ? (
                <div className="text-center py-8 text-gray-500">Nenhum lote cadastrado</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lote</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qtd Disponível</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fabricação</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validade</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Custo Unit.</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {lotes.map((lote) => (
                        <tr key={lote.id}>
                          <td className="px-4 py-3 text-sm text-gray-900">{lote.nome_lote || '-'}</td>
                          <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                            {lote.quantidade_disponivel}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-700">{formatarData(lote.data_fabricacao)}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{formatarData(lote.data_validade)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-900">
                            {formatarMoeda(lote.custo_unitario)}
                          </td>
                          <td className="px-4 py-3 text-sm text-center">
                            <div className="flex justify-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleEditarLote(lote)}
                                className="text-blue-600 hover:text-blue-800"
                                title="Editar lote"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                  />
                                </svg>
                              </button>
                              <button
                                type="button"
                                onClick={() => handleExcluirLote(lote)}
                                className="text-red-600 hover:text-red-800"
                                title="Excluir lote"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                  />
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          {!isEdicao && <div className="text-center py-8 text-gray-500">Salve o produto primeiro para gerenciar lotes</div>}
        </>
      )}
    </div>
  );
}
