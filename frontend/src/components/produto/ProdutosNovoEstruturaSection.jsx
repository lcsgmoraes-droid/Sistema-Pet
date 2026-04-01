export default function ProdutosNovoEstruturaSection({
  buscaPredecessor,
  formData,
  handleBuscaPredecessorChange,
  handleChange,
  handleRemoverPredecessor,
  handleSelecionarPredecessor,
  handleToggleBuscaPredecessor,
  isEdicao,
  mostrarBuscaPredecessor,
  predecessorSelecionado,
  produtosBusca,
  setAbaAtiva,
  setFormData,
}) {
  return (
    <>
      {!isEdicao && (
        <div className="border-t pt-6 mt-6">
          <div className="p-6 bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <h3 className="text-lg font-semibold text-gray-900">Evolucao do Produto</h3>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={mostrarBuscaPredecessor}
                  onChange={(e) => handleToggleBuscaPredecessor(e.target.checked)}
                  className="h-4 w-4 text-amber-600 focus:ring-amber-500 border-gray-300 rounded"
                />
                <span className="text-sm font-medium text-gray-700">Este produto substitui outro</span>
              </label>
            </div>

            {mostrarBuscaPredecessor ? (
              <div className="space-y-4">
                <div className="p-4 bg-white rounded-lg border-2 border-amber-300">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Buscar Produto Anterior</label>
                  <input
                    type="text"
                    placeholder="Digite o nome ou codigo do produto..."
                    value={buscaPredecessor}
                    onChange={(e) => handleBuscaPredecessorChange(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                  />

                  {produtosBusca.length > 0 && (
                    <div className="mt-2 max-h-48 overflow-y-auto border border-gray-300 rounded-lg">
                      {produtosBusca.map((produto) => (
                        <div
                          key={produto.id}
                          onClick={() => handleSelecionarPredecessor(produto)}
                          className="p-3 hover:bg-amber-50 cursor-pointer border-b border-gray-200 last:border-0"
                        >
                          <div className="font-medium text-gray-900">{produto.nome}</div>
                          <div className="text-sm text-gray-600">
                            SKU: {produto.codigo} | Preco: R$ {produto.preco_venda?.toFixed(2)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {predecessorSelecionado && (
                    <div className="mt-3 p-3 bg-green-50 border border-green-300 rounded-lg">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-sm font-medium text-green-800">Produto Selecionado:</div>
                          <div className="font-semibold text-gray-900 mt-1">{predecessorSelecionado.nome}</div>
                          <div className="text-sm text-gray-600">SKU: {predecessorSelecionado.codigo}</div>
                        </div>
                        <button type="button" onClick={handleRemoverPredecessor} className="text-red-600 hover:text-red-800">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {predecessorSelecionado && (
                  <div className="p-4 bg-white rounded-lg border-2 border-amber-300">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Motivo da Substituicao</label>
                    <select
                      value={formData.motivo_descontinuacao}
                      onChange={(e) => handleChange('motivo_descontinuacao', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent mb-2"
                    >
                      <option value="">Selecione o motivo...</option>
                      <option value="Mudanca de embalagem">Mudanca de embalagem</option>
                      <option value="Mudanca de peso/gramatura">Mudanca de peso/gramatura</option>
                      <option value="Reformulacao do produto">Reformulacao do produto</option>
                      <option value="Mudanca de fornecedor">Mudanca de fornecedor</option>
                      <option value="Upgrade de linha">Upgrade de linha</option>
                      <option value="Outro">Outro</option>
                    </select>

                    {formData.motivo_descontinuacao === 'Outro' && (
                      <textarea
                        value={formData.motivo_descontinuacao}
                        onChange={(e) => handleChange('motivo_descontinuacao', e.target.value)}
                        placeholder="Descreva o motivo..."
                        rows="2"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      />
                    )}

                    <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
                      <strong>O que acontecera:</strong>
                      <ul className="mt-2 space-y-1 list-disc list-inside">
                        <li>O produto "<strong>{predecessorSelecionado.nome}</strong>" sera marcado como <strong>descontinuado</strong></li>
                        <li>Todo o historico de vendas sera mantido e podera ser consultado</li>
                        <li>Voce podera gerar relatorios consolidados somando ambos os produtos</li>
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-600 mt-2">
                Marque esta opcao se este produto substitui outro ja cadastrado (ex: mudanca de embalagem de 350g para 300g).
                Isso permite manter o historico consolidado de vendas.
              </p>
            )}
          </div>
        </div>
      )}

      {!isEdicao && (
        <div className="border-t pt-6">
          <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              Tipo do Produto
            </h3>

            <p className="text-sm text-gray-600 mb-4">Escolha o tipo de produto que esta cadastrando:</p>

            <div className="space-y-3">
              <div
                className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
                style={{ borderColor: formData.tipo_produto === 'SIMPLES' ? '#3b82f6' : '#e5e7eb' }}
              >
                <input
                  type="radio"
                  id="tipo_simples"
                  name="tipo_produto"
                  value="SIMPLES"
                  checked={formData.tipo_produto === 'SIMPLES'}
                  onChange={() => {
                    handleChange('tipo_produto', 'SIMPLES');
                    setFormData((prev) => ({ ...prev, composicao_kit: [], e_kit_fisico: false }));
                  }}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <label htmlFor="tipo_simples" className="font-medium text-gray-900 cursor-pointer">Produto Simples</label>
                  <p className="text-sm text-gray-600 mt-1">Produto unico, vendavel, com controle de estoque proprio.</p>
                </div>
              </div>

              <div
                className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
                style={{ borderColor: formData.tipo_produto === 'PAI' ? '#3b82f6' : '#e5e7eb' }}
              >
                <input
                  type="radio"
                  id="tipo_variacoes"
                  name="tipo_produto"
                  value="PAI"
                  checked={formData.tipo_produto === 'PAI'}
                  onChange={() => {
                    handleChange('tipo_produto', 'PAI');
                    setFormData((prev) => ({
                      ...prev,
                      preco_custo: '',
                      preco_venda: '',
                      preco_promocional: '',
                      composicao_kit: [],
                      e_kit_fisico: false,
                    }));
                  }}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <label htmlFor="tipo_variacoes" className="font-medium text-gray-900 cursor-pointer">Produto com Variacoes</label>
                  <p className="text-sm text-gray-600 mt-1">
                    Produto agrupador (nao vendavel). Tera variacoes com SKU, preco e estoque proprios.
                    <br />
                    <span className="text-xs italic">Exemplo: Camiseta (produto pai) {'->'} P, M, G (variacoes)</span>
                  </p>
                  {formData.tipo_produto === 'PAI' && !isEdicao && (
                    <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
                      <strong>Salve o produto primeiro</strong> para depois cadastrar as variacoes na aba "Variacoes".
                    </div>
                  )}
                  {formData.tipo_produto === 'PAI' && isEdicao && (
                    <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                      Produto salvo! Va para a aba "Variacoes" para cadastrar as variacoes.
                    </div>
                  )}
                </div>
              </div>

              <div
                className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
                style={{ borderColor: formData.tipo_produto === 'KIT' ? '#3b82f6' : '#e5e7eb' }}
              >
                <input
                  type="radio"
                  id="tipo_kit"
                  name="tipo_produto"
                  value="KIT"
                  checked={formData.tipo_produto === 'KIT'}
                  onChange={() => {
                    handleChange('tipo_produto', 'KIT');
                    setAbaAtiva(9);
                  }}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <label htmlFor="tipo_kit" className="font-medium text-gray-900 cursor-pointer">Produto com Composicao (Kit)</label>
                  <p className="text-sm text-gray-600 mt-1">
                    Kit composto por outros produtos existentes.
                    <br />
                    <span className="text-xs italic">Exemplo: Kit Banho (shampoo + condicionador + toalha)</span>
                  </p>
                  {formData.tipo_produto === 'KIT' && (
                    <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                      <strong>Aba "Composicao" aberta!</strong> Va para a aba Composicao para definir se o kit tera estoque virtual ou fisico e adicionar os produtos que o compoem.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {isEdicao && formData.tipo_produto === 'VARIACAO' && (
        <div className="border-t pt-6">
          <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Composicao (Kit)
            </h3>

            <div className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 border-gray-300">
              <input
                type="checkbox"
                id="variacao_e_kit"
                checked={!!formData.tipo_kit}
                onChange={(e) => {
                  if (e.target.checked) {
                    handleChange('tipo_kit', 'VIRTUAL');
                    handleChange('e_kit_fisico', false);
                    setAbaAtiva(9);
                  } else {
                    handleChange('tipo_kit', null);
                    handleChange('composicao_kit', []);
                    handleChange('e_kit_fisico', false);
                  }
                }}
                className="mt-1 h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <div className="flex-1">
                <label htmlFor="variacao_e_kit" className="font-medium text-gray-900 cursor-pointer text-lg">
                  Esta variacao e um KIT (possui composicao)
                </label>
                <p className="text-sm text-gray-600 mt-2">
                  Marque esta opcao se esta variacao e composta por outros produtos.
                  <br />
                  <span className="text-xs italic">Exemplo: Camiseta P - Kit (camiseta + brinde)</span>
                </p>
                {formData.tipo_kit && (
                  <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                    <strong>Variacao configurada como KIT!</strong> Va para a aba "Composicao" para definir os produtos que compoem este kit.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
