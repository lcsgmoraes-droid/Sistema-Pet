export default function ProdutosNovoEstoqueTab({
  formData,
  formatarData,
  formatarMoeda,
  handleChange,
  isEdicao,
  lotes,
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

          {!isEdicao &&
            !(formData.tipo_produto === "KIT" && !formData.e_kit_fisico) &&
            !formData.e_granel &&
            !String(formData.nome || "")
              .toLowerCase()
              .includes("granel") && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-4">
                <div>
                  <h3 className="font-semibold text-blue-900">Entrada inicial no cadastro</h3>
                  <p className="text-sm text-blue-800">
                    Informe a quantidade que está entrando agora. Lote, validade e fabricação são
                    opcionais.
                  </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="text-sm font-medium text-gray-700">
                    Quantidade de entrada
                    <input
                      type="text"
                      inputMode="decimal"
                      maxLength={10}
                      value={formData.entrada_inicial_quantidade || ""}
                      onChange={(e) => handleChange("entrada_inicial_quantidade", e.target.value)}
                      placeholder="Ex.: 10 ou 1,5"
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm font-medium text-gray-700">
                    Unidade
                    <select
                      value={formData.unidade || "UN"}
                      onChange={(e) => handleChange("unidade", e.target.value)}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
                    >
                      <option value="UN">UN - Unidade</option>
                      <option value="KG">KG - Quilograma</option>
                      <option value="G">G - Grama</option>
                      <option value="L">L - Litro</option>
                      <option value="ML">ML - Mililitro</option>
                      <option value="M">M - Metro</option>
                      <option value="CX">CX - Caixa</option>
                      <option value="PCT">PCT - Pacote</option>
                    </select>
                  </label>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <label className="text-sm font-medium text-gray-700">
                    Número do lote · opcional
                    <input
                      type="text"
                      maxLength={50}
                      value={formData.entrada_inicial_numero_lote || ""}
                      onChange={(e) => handleChange("entrada_inicial_numero_lote", e.target.value)}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm font-medium text-gray-700">
                    Validade · opcional
                    <input
                      type="date"
                      value={formData.entrada_inicial_data_validade || ""}
                      onChange={(e) =>
                        handleChange("entrada_inicial_data_validade", e.target.value)
                      }
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm font-medium text-gray-700">
                    Fabricação · opcional
                    <input
                      type="date"
                      value={formData.entrada_inicial_data_fabricacao || ""}
                      onChange={(e) =>
                        handleChange("entrada_inicial_data_fabricacao", e.target.value)
                      }
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
                    />
                  </label>
                </div>
              </div>
            )}

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
        </>
      )}
    </div>
  );
}
