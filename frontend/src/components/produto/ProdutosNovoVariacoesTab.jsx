export default function ProdutosNovoVariacoesTab({
  formData,
  isEdicao,
  mostrarFormVariacao,
  novaVariacao,
  setNovaVariacao,
  variacoes,
  handleToggleFormVariacao,
  handleCancelarVariacao,
  handleSalvarVariacao,
  handleExcluirVariacao,
  onEditarVariacao,
}) {
  return (
    <div className="space-y-6">
      {!isEdicao ? (
        <div className="text-center py-16 border-2 border-dashed border-yellow-300 rounded-lg bg-yellow-50">
          <svg className="mx-auto h-16 w-16 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <p className="mt-4 text-xl font-semibold text-yellow-900">Aba Bloqueada</p>
          <p className="mt-2 text-sm text-yellow-800">
            Salve o produto primeiro para habilitar o cadastro de variacoes.
          </p>
          <p className="mt-4 text-xs text-yellow-700">
            Apos salvar, voce sera redirecionado automaticamente para cadastrar as variacoes.
          </p>
        </div>
      ) : (
        <>
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h3 className="text-lg font-semibold text-blue-900 mb-2">
              Variacoes do Produto: {formData.nome}
            </h3>
            <p className="text-sm text-blue-700">
              Cadastre as variacoes deste produto. Cada variacao e um produto vendavel independente
              com seu proprio SKU, preco e estoque.
            </p>
          </div>

          <div>
            <div className="flex justify-between items-center mb-4">
              <h4 className="text-md font-semibold">Variacoes Cadastradas</h4>
              <button
                type="button"
                onClick={handleToggleFormVariacao}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                {mostrarFormVariacao ? 'Cancelar' : 'Nova Variacao'}
              </button>
            </div>

            {mostrarFormVariacao && (
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-4">
                <h5 className="font-semibold mb-3">Cadastrar Nova Variacao</h5>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SKU *</label>
                    <input
                      type="text"
                      value={novaVariacao.sku}
                      onChange={(e) => setNovaVariacao({ ...novaVariacao, sku: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="Ex: PROD001-P"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Nome Complementar *</label>
                    <input
                      type="text"
                      value={novaVariacao.nome}
                      onChange={(e) => setNovaVariacao({ ...novaVariacao, nome: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="Ex: Tamanho P"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Codigo de Barras</label>
                    <input
                      type="text"
                      value={novaVariacao.codigo_barras}
                      onChange={(e) => setNovaVariacao({ ...novaVariacao, codigo_barras: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="EAN-13"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Preco de Custo</label>
                    <input
                      type="number"
                      step="0.01"
                      value={novaVariacao.preco_custo}
                      onChange={(e) => setNovaVariacao({ ...novaVariacao, preco_custo: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Preco de Venda *</label>
                    <input
                      type="number"
                      step="0.01"
                      value={novaVariacao.preco_venda}
                      onChange={(e) => setNovaVariacao({ ...novaVariacao, preco_venda: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Estoque Minimo</label>
                    <input
                      type="number"
                      value={novaVariacao.estoque_minimo}
                      onChange={(e) => setNovaVariacao({ ...novaVariacao, estoque_minimo: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="0"
                    />
                  </div>
                </div>

                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={novaVariacao.e_kit}
                      onChange={(e) => setNovaVariacao({ ...novaVariacao, e_kit: e.target.checked })}
                      className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <div>
                      <span className="font-medium text-gray-900">Esta variacao e um KIT (possui composicao)</span>
                      <p className="text-sm text-gray-600 mt-1">
                        Se marcado, voce podera definir a composicao do kit apos salvar a variacao.
                      </p>
                    </div>
                  </label>
                </div>

                <div className="mt-4 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={handleCancelarVariacao}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={handleSalvarVariacao}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    Salvar Variacao
                  </button>
                </div>
              </div>
            )}

            {variacoes.length === 0 ? (
              <div className="text-center py-8 border-2 border-dashed border-gray-300 rounded-lg">
                <p className="text-gray-500">Nenhuma variacao cadastrada ainda.</p>
                <p className="text-sm text-gray-400 mt-1">Clique em "Nova Variacao" para comecar.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Codigo de Barras</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Custo</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Venda</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Estoque</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acoes</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {variacoes.map((variacao) => (
                      <tr key={variacao.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{variacao.codigo}</td>
                        <td className="px-4 py-3 text-sm text-gray-700">{variacao.nome}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{variacao.codigo_barras || '-'}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900">
                          R$ {(variacao.preco_custo || 0).toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900 font-semibold">
                          R$ {variacao.preco_venda.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">
                          <span className={`font-semibold ${variacao.estoque_atual <= variacao.estoque_minimo ? 'text-red-600' : 'text-green-600'}`}>
                            {variacao.estoque_atual || 0}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            type="button"
                            onClick={() => onEditarVariacao(variacao)}
                            className="text-blue-600 hover:text-blue-800 mr-2"
                            title="Editar"
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            onClick={() => handleExcluirVariacao(variacao)}
                            className="text-red-600 hover:text-red-800"
                            title="Excluir"
                          >
                            Excluir
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
