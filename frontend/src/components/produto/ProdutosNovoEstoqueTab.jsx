export default function ProdutosNovoEstoqueTab({
  formData,
  formatarData,
  formatarMoeda,
  handleChange,
  isEdicao,
  lotes,
  salvando,
}) {
  return (
    <div className="space-y-6">
      {formData.tipo === "servico" ? (
        <div className="rounded-lg border-2 border-dashed border-teal-300 bg-teal-50 py-12 text-center">
          <p className="text-lg font-medium text-teal-900">Serviço não controla estoque</p>
          <p className="mt-2 text-sm text-teal-700">
            Não há saldo, lote, estoque mínimo ou lista de espera para este cadastro.
          </p>
        </div>
      ) : formData.tipo_produto === "PAI" ? (
        <div className="text-center py-12 border-2 border-dashed border-blue-300 rounded-lg bg-blue-50">
          <svg
            className="mx-auto h-12 w-12 text-blue-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
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
            <br />O controle de estoque é feito individualmente nas variações.
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
                  onChange={(e) => handleChange("controle_lote", e.target.checked)}
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
                onChange={(e) => handleChange("estoque_minimo", e.target.value)}
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
                onChange={(e) => handleChange("estoque_maximo", e.target.value)}
                disabled={!formData.controle_lote}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                placeholder="0"
              />
            </div>
          </div>

          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={formData.e_granel ? false : formData.participa_sugestao_compra !== false}
                disabled={formData.e_granel}
                onChange={(e) => handleChange("participa_sugestao_compra", e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500 disabled:opacity-50"
              />
              <span>
                <span className="block text-sm font-semibold text-emerald-900">
                  Entrar na sugestao inteligente de compra
                </span>
                <span className="mt-1 block text-sm text-emerald-800">
                  Desmarque para manter o produto cadastrado, mas esconder das sugestoes de pedido.
                  Produtos granel ficam fora automaticamente.
                </span>
              </span>
            </label>
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm text-blue-900">
              Registre entradas e saídas nas movimentações. Na mesma tela, identifique lotes e
              validades de quantidades que já estão no estoque, sem alterar o saldo.
            </p>
            <button
              type="submit"
              name="destino"
              value="estoque"
              disabled={salvando || (formData.tipo_produto === "KIT" && !formData.e_kit_fisico)}
              className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {salvando ? "Salvando..." : "Salvar e abrir lançamentos de estoque e lotes"}
            </button>
          </div>

          {isEdicao && formData.controle_lote && (
            <>
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-gray-900">Lotes (FIFO)</h3>
              </div>

              {lotes.length === 0 ? (
                <div className="text-center py-8 text-gray-500">Nenhum lote cadastrado</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Lote
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                          Qtd Disponível
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Fabricação
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Validade
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                          Custo Unit.
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {lotes.map((lote) => (
                        <tr key={lote.id}>
                          <td className="px-4 py-3 text-sm text-gray-900">
                            {lote.nome_lote || "-"}
                          </td>
                          <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                            {lote.quantidade_disponivel}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-700">
                            {formatarData(lote.data_fabricacao)}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-700">
                            {formatarData(lote.data_validade)}
                          </td>
                          <td className="px-4 py-3 text-sm text-right text-gray-900">
                            {formatarMoeda(lote.custo_unitario)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          {!isEdicao && (
            <div className="text-center py-8 text-gray-500">
              Use “Salvar e abrir lançamentos de estoque e lotes” para continuar após o cadastro.
            </div>
          )}
        </>
      )}
    </div>
  );
}
