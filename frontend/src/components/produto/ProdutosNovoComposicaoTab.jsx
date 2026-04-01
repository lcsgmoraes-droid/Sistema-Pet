export default function ProdutosNovoComposicaoTab({
  formData,
  handleChange,
  estoqueVirtualKit,
  produtosDisponiveis,
  produtoKitSelecionado,
  setProdutoKitSelecionado,
  quantidadeKit,
  setQuantidadeKit,
  buscaComponente,
  setBuscaComponente,
  dropdownComponenteVisivel,
  setDropdownComponenteVisivel,
  adicionarProdutoKit,
  removerProdutoKit,
}) {
  return (
    <div className="space-y-6">
      <div className="bg-white border-2 border-gray-300 rounded-lg p-5">
        <h3 className="font-semibold text-gray-900 mb-4">Tipo de Estoque do Kit</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            onClick={() => handleChange('e_kit_fisico', false)}
            className={`cursor-pointer p-4 border-2 rounded-lg transition-all ${
              !formData.e_kit_fisico
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 bg-white hover:border-blue-300'
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                type="radio"
                name="tipo_estoque_kit"
                checked={!formData.e_kit_fisico}
                onChange={() => handleChange('e_kit_fisico', false)}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">📊</span>
                  <h4 className="font-semibold text-gray-900">Estoque Virtual</h4>
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  O estoque e calculado <strong>automaticamente</strong> com base nos componentes disponiveis.
                </p>
                <div className="mt-2 text-xs text-gray-500 space-y-1">
                  <div>✓ Nao permite movimentacao manual</div>
                  <div>✓ Estoque = menor disponibilidade dos componentes</div>
                  <div>✓ Ideal para kits montados sob demanda</div>
                </div>
              </div>
            </div>
          </div>

          <div
            onClick={() => handleChange('e_kit_fisico', true)}
            className={`cursor-pointer p-4 border-2 rounded-lg transition-all ${
              formData.e_kit_fisico
                ? 'border-green-500 bg-green-50'
                : 'border-gray-300 bg-white hover:border-green-300'
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                type="radio"
                name="tipo_estoque_kit"
                checked={formData.e_kit_fisico}
                onChange={() => handleChange('e_kit_fisico', true)}
                className="mt-1 h-4 w-4 text-green-600 focus:ring-green-500"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">📦</span>
                  <h4 className="font-semibold text-gray-900">Estoque Fisico</h4>
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  O kit possui estoque <strong>proprio e independente</strong> dos componentes.
                </p>
                <div className="mt-2 text-xs text-gray-500 space-y-1">
                  <div>✓ Permite movimentacao manual</div>
                  <div>✓ Entrada: diminui componentes (montou kits)</div>
                  <div>✓ Ideal para kits pre-montados</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <svg className="w-6 h-6 text-purple-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
          <div>
            <h3 className="font-semibold text-gray-900">Composicao do Kit</h3>
            <p className="text-sm text-gray-600 mt-1">
              Defina quais produtos compoem este kit e as quantidades necessarias de cada um.
            </p>
            {!formData.e_kit_fisico && (
              <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
                <strong>📊 Estoque Virtual Ativo</strong>
                <br />
                O estoque deste kit sera calculado automaticamente baseado nos componentes.
                <br />
                <span className="text-xs italic">
                  Estoque do kit = menor disponibilidade entre os componentes (considerando as quantidades necessarias)
                </span>
              </div>
            )}
            {formData.e_kit_fisico && (
              <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                <strong>📦 Estoque Fisico Ativo</strong>
                <br />
                <strong>Entrada no kit:</strong> Os componentes serao automaticamente DIMINUIDOS (unitarios viraram kit).
                <br />
                <strong>Saida manual:</strong> Voce podera escolher se os componentes voltam ao estoque (desfez o kit) ou nao (perda/roubo).
              </div>
            )}
          </div>
        </div>
      </div>

      {!formData.e_kit_fisico && formData.composicao_kit.length > 0 && (
        <div className="bg-white border-2 border-green-300 rounded-lg p-5">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-gray-700">Estoque Virtual do Kit</h4>
              <p className="text-xs text-gray-500 mt-1">Calculado automaticamente</p>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold text-green-600">{estoqueVirtualKit}</div>
              <p className="text-xs text-gray-500">kits disponiveis</p>
            </div>
          </div>
        </div>
      )}

      <div className="border border-gray-300 rounded-lg p-5 bg-gray-50">
        <h4 className="font-semibold text-gray-900 mb-4">Adicionar Produto ao Kit</h4>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Produto</label>
            <div className="relative">
              <input
                type="text"
                value={buscaComponente}
                onChange={(e) => {
                  setBuscaComponente(e.target.value);
                  setProdutoKitSelecionado('');
                  setDropdownComponenteVisivel(true);
                }}
                onFocus={() => setDropdownComponenteVisivel(true)}
                onBlur={() => setTimeout(() => setDropdownComponenteVisivel(false), 180)}
                placeholder="Buscar por SKU ou nome..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoComplete="off"
              />
              {dropdownComponenteVisivel &&
                buscaComponente.length > 0 &&
                (() => {
                  const termo = buscaComponente.toLowerCase();
                  const filtrados = produtosDisponiveis
                    .filter(
                      (produto) =>
                        (produto.codigo && produto.codigo.toLowerCase().includes(termo)) ||
                        (produto.nome && produto.nome.toLowerCase().includes(termo))
                    )
                    .slice(0, 30);
                  return filtrados.length > 0 ? (
                    <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-64 overflow-y-auto">
                      {filtrados.map((produto) => (
                        <div
                          key={produto.id}
                          className="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm flex justify-between items-center"
                          onMouseDown={() => {
                            setProdutoKitSelecionado(String(produto.id));
                            setBuscaComponente(`[${produto.codigo}] ${produto.nome}`);
                            setDropdownComponenteVisivel(false);
                          }}
                        >
                          <span>
                            <span className="font-semibold text-blue-700">{produto.codigo}</span> – {produto.nome}
                          </span>
                          <span className="text-xs text-gray-400 ml-2 shrink-0">
                            Estoque: {produto.estoque_atual || 0}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : null;
                })()}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Quantidade</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={quantidadeKit}
              onChange={(e) => setQuantidadeKit(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="1"
            />
          </div>
        </div>

        <button
          type="button"
          onClick={adicionarProdutoKit}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Adicionar ao Kit
        </button>
      </div>

      <div>
        <h4 className="font-semibold text-gray-900 mb-3">Produtos no Kit ({formData.composicao_kit.length})</h4>

        {formData.composicao_kit.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="mt-2 text-sm text-gray-600">Nenhum produto adicionado ao kit ainda</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produto</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Quantidade</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estoque</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Kits Possiveis</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acoes</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {formData.composicao_kit.map((item) => {
                  const kitsPossiveis = Math.floor(item.estoque_componente / item.quantidade);
                  const eGargalo = kitsPossiveis === estoqueVirtualKit && estoqueVirtualKit > 0;

                  return (
                    <tr key={item.produto_id} className={`hover:bg-gray-50 ${eGargalo ? 'bg-yellow-50' : ''}`}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.produto_sku || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {item.produto_nome}
                        {eGargalo && (
                          <span className="ml-2 text-xs bg-yellow-200 text-yellow-800 px-2 py-1 rounded">
                            ⚠️ LIMITADOR
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-center text-gray-900 font-semibold">{item.quantidade}</td>
                      <td className="px-4 py-3 text-sm text-center text-gray-600">{item.estoque_componente || 0}</td>
                      <td className="px-4 py-3 text-sm text-center">
                        <span
                          className={`font-semibold ${
                            kitsPossiveis === 0 ? 'text-red-600' : kitsPossiveis < 5 ? 'text-yellow-600' : 'text-green-600'
                          }`}
                        >
                          {kitsPossiveis}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          type="button"
                          onClick={() => removerProdutoKit(item.produto_id)}
                          className="text-red-600 hover:text-red-800"
                          title="Remover do kit"
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {formData.composicao_kit.length > 0 && estoqueVirtualKit === 0 && !formData.e_kit_fisico && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="text-sm text-red-800">
              <strong>Kit sem estoque disponivel!</strong>
              <p className="mt-1">Pelo menos um dos componentes esta sem estoque suficiente para montar o kit.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
