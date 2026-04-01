export default function ProdutosNovoCaracteristicasTab({
  buscaPredecessor,
  camposEmEdicao,
  categoriasHierarquicas,
  departamentos,
  formData,
  handleBuscaPredecessorChange,
  handleChange,
  handleGerarCodigoBarras,
  handleGerarSKU,
  handleRemoverPredecessor,
  handleSelecionarPredecessor,
  handleToggleBuscaPredecessor,
  isEdicao,
  marcas,
  mostrarBuscaPredecessor,
  parseNumber,
  predecessorSelecionado,
  produtosBusca,
  setAbaAtiva,
  setCamposEmEdicao,
  setFormData,
}) {
  return (
<div className="space-y-6">
  {/* Linha 1: Códigos */}
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        SKU *
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={formData.sku}
          onChange={(e) => handleChange('sku', e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Ex: PROD0001"
        />
        <button
          type="button"
          onClick={handleGerarSKU}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm"
        >
          Gerar
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        Esse valor é salvo como o SKU oficial do produto.
        {formData.codigo ? ` Atual: ${formData.codigo}` : ''}
      </p>
    </div>

    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Código de Barras
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={formData.codigo_barras}
          onChange={(e) => handleChange('codigo_barras', e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="EAN-13"
        />
        <button
          type="button"
          onClick={handleGerarCodigoBarras}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm"
        >
          Gerar
        </button>
      </div>
    </div>
  </div>

  {/* Linha 2: Nome */}
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      Nome do Produto *
    </label>
    <input
      type="text"
      value={formData.nome}
      onChange={(e) => handleChange('nome', e.target.value)}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      placeholder="Ex: Ração Golden para Cães Adultos 15kg"
      required
    />
  </div>

  {/* Linha 3: Classificação */}
  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Tipo
      </label>
      <select
        value={formData.tipo}
        onChange={(e) => handleChange('tipo', e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        <option value="produto">Produto</option>
        <option value="servico">Serviço</option>
        <option value="ambos">Produto e Serviço</option>
      </select>
    </div>

    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Departamento
      </label>
      <select
        value={formData.departamento_id}
        onChange={(e) => handleChange('departamento_id', e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        <option value="">Selecione...</option>
        {departamentos.map(dep => (
          <option key={dep.id} value={dep.id}>{dep.nome}</option>
        ))}
      </select>
    </div>

    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Categoria
      </label>
      <select
        value={formData.categoria_id}
        onChange={(e) => handleChange('categoria_id', e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        <option value="">Selecione...</option>
        { categoriasHierarquicas.map(cat => (
          <option key={cat.id} value={cat.id}>
            {cat.nomeFormatado}
          </option>
        ))}
      </select>
    </div>

    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Marca
      </label>
      <select
        value={formData.marca_id}
        onChange={(e) => handleChange('marca_id', e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        <option value="">Selecione...</option>
        {marcas.map(marca => (
          <option key={marca.id} value={marca.id}>{marca.nome}</option>
        ))}
      </select>
    </div>
  </div>

  {/* Linha 4: Unidade e Descrição */}
  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Unidade
      </label>
      <select
        value={formData.unidade}
        onChange={(e) => handleChange('unidade', e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
    </div>

    <div className="md:col-span-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Descrição
      </label>
      <textarea
        value={formData.descricao}
        onChange={(e) => handleChange('descricao', e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        rows="2"
        placeholder="Descrição detalhada do produto..."
      />
    </div>
  </div>

  {/* Linha 5: Preços - Oculta quando for produto PAI */}
  {formData.tipo_produto !== 'PAI' && (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Preço de Custo
        </label>
        <input
          type="text"
          value={
            camposEmEdicao.preco_custo
              ? (formData.preco_custo || '')
              : (formData.preco_custo ? `R$ ${parseNumber(formData.preco_custo).toFixed(2).replace('.', ',')}` : 'R$ 0,00')
          }
          onChange={(e) => {
            const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
            handleChange('preco_custo', value);
          }}
          onFocus={(e) => {
            setCamposEmEdicao(prev => ({ ...prev, preco_custo: true }));
            e.target.select();
          }}
          onBlur={(e) => {
            setCamposEmEdicao(prev => ({ ...prev, preco_custo: false }));
            const value = parseNumber(e.target.value);
            handleChange('preco_custo', value > 0 ? value.toFixed(2) : '');
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="R$ 0,00"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Markup
        </label>
        <input
          type="text"
          value={
            camposEmEdicao.markup
              ? (formData.markup || '')
              : (formData.markup ? `${parseNumber(formData.markup).toFixed(2).replace('.', ',')}%` : '0,00%')
          }
          onChange={(e) => {
            const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
            handleChange('markup', value);
          }}
          onFocus={(e) => {
            setCamposEmEdicao(prev => ({ ...prev, markup: true }));
            e.target.select();
          }}
          onBlur={(e) => {
            setCamposEmEdicao(prev => ({ ...prev, markup: false }));
            const value = parseNumber(e.target.value);
            handleChange('markup', value >= 0 ? value.toFixed(2) : '');
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="0,00%"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Preço de Venda *
        </label>
        <input
          type="text"
          value={
            camposEmEdicao.preco_venda
              ? (formData.preco_venda || '')
              : (formData.preco_venda ? `R$ ${parseNumber(formData.preco_venda).toFixed(2).replace('.', ',')}` : 'R$ 0,00')
          }
          onChange={(e) => {
            const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
            handleChange('preco_venda', value);
          }}
          onFocus={(e) => {
            setCamposEmEdicao(prev => ({ ...prev, preco_venda: true }));
            e.target.select();
          }}
          onBlur={(e) => {
            setCamposEmEdicao(prev => ({ ...prev, preco_venda: false }));
            const value = parseNumber(e.target.value);
            handleChange('preco_venda', value > 0 ? value.toFixed(2) : '');
          }}
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="R$ 0,00"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Preço Promocional
        </label>
        <input
          type="text"
          value={
            camposEmEdicao.preco_promocional
              ? (formData.preco_promocional || '')
              : (formData.preco_promocional ? `R$ ${parseNumber(formData.preco_promocional).toFixed(2).replace('.', ',')}` : 'R$ 0,00')
          }
          onChange={(e) => {
            const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
            handleChange('preco_promocional', value);
          }}
          onFocus={(e) => {
            setCamposEmEdicao(prev => ({ ...prev, preco_promocional: true }));
            e.target.select();
          }}
          onBlur={(e) => {
            setCamposEmEdicao(prev => ({ ...prev, preco_promocional: false }));
            const value = parseNumber(e.target.value);
            handleChange('preco_promocional', value > 0 ? value.toFixed(2) : '');
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="R$ 0,00"
        />
      </div>
    </div>
  )}

  {/* Linha 6: Validade do preço promocional base (ERP) */}
  {formData.tipo_produto !== 'PAI' && (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Início da Promoção (ERP)
        </label>
        <input
          type="date"
          value={formData.data_inicio_promocao}
          onChange={(e) => handleChange('data_inicio_promocao', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Fim da Promoção (ERP)
        </label>
        <input
          type="date"
          value={formData.data_fim_promocao}
          onChange={(e) => handleChange('data_fim_promocao', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
    </div>
  )}

  {/* Linha 7: Preços por Canal (Ecommerce / App) */}
  {formData.tipo_produto !== 'PAI' && (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-gray-700">Preços por Canal (Ecommerce / App)</h3>
        <p className="text-xs text-gray-500 mt-1">
          Se deixar vazio, o sistema usa o preço de venda padrão.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-3">
          <div className="text-xs font-bold text-purple-700 uppercase">Ecommerce</div>
          <input
            type="number"
            step="0.01"
            min="0"
            value={formData.preco_ecommerce}
            onChange={(e) => handleChange('preco_ecommerce', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            placeholder="Preço normal"
          />
          <input
            type="number"
            step="0.01"
            min="0"
            value={formData.preco_ecommerce_promo}
            onChange={(e) => handleChange('preco_ecommerce_promo', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            placeholder="Preço promocional"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <input
              type="datetime-local"
              value={formData.preco_ecommerce_promo_inicio ? formData.preco_ecommerce_promo_inicio.toString().slice(0, 16) : ''}
              onChange={(e) => handleChange('preco_ecommerce_promo_inicio', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <input
              type="datetime-local"
              value={formData.preco_ecommerce_promo_fim ? formData.preco_ecommerce_promo_fim.toString().slice(0, 16) : ''}
              onChange={(e) => handleChange('preco_ecommerce_promo_fim', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="space-y-3">
          <div className="text-xs font-bold text-green-700 uppercase">App Móvel</div>
          <input
            type="number"
            step="0.01"
            min="0"
            value={formData.preco_app}
            onChange={(e) => handleChange('preco_app', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            placeholder="Preço normal"
          />
          <input
            type="number"
            step="0.01"
            min="0"
            value={formData.preco_app_promo}
            onChange={(e) => handleChange('preco_app_promo', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            placeholder="Preço promocional"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <input
              type="datetime-local"
              value={formData.preco_app_promo_inicio ? formData.preco_app_promo_inicio.toString().slice(0, 16) : ''}
              onChange={(e) => handleChange('preco_app_promo_inicio', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
            <input
              type="datetime-local"
              value={formData.preco_app_promo_fim ? formData.preco_app_promo_fim.toString().slice(0, 16) : ''}
              onChange={(e) => handleChange('preco_app_promo_fim', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>
    </div>
  )}
  
  {/* =========================================
      SISTEMA PREDECESSOR/SUCESSOR
      ========================================= */}
  {!isEdicao && (
    <div className="border-t pt-6 mt-6">
      <div className="p-6 bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3 className="text-lg font-semibold text-gray-900">
              Evolução do Produto
            </h3>
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
        
        {mostrarBuscaPredecessor && (
          <div className="space-y-4">
            <div className="p-4 bg-white rounded-lg border-2 border-amber-300">
              {/* Busca de Produto */}
              <label className="block text-sm font-medium text-gray-700 mb-2">
                🔍 Buscar Produto Anterior
              </label>
              <input
                type="text"
                placeholder="Digite o nome ou código do produto..."
                value={buscaPredecessor}
                onChange={(e) => handleBuscaPredecessorChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              />
              
              {/* Resultados da Busca */}
              {produtosBusca.length > 0 && (
                <div className="mt-2 max-h-48 overflow-y-auto border border-gray-300 rounded-lg">
                  {produtosBusca.map(produto => (
                    <div
                      key={produto.id}
                      onClick={() => handleSelecionarPredecessor(produto)}
                      className="p-3 hover:bg-amber-50 cursor-pointer border-b border-gray-200 last:border-0"
                    >
                      <div className="font-medium text-gray-900">{produto.nome}</div>
                      <div className="text-sm text-gray-600">
                        SKU: {produto.codigo} | Preço: R$ {produto.preco_venda?.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Produto Selecionado */}
              {predecessorSelecionado && (
                <div className="mt-3 p-3 bg-green-50 border border-green-300 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm font-medium text-green-800">✅ Produto Selecionado:</div>
                      <div className="font-semibold text-gray-900 mt-1">{predecessorSelecionado.nome}</div>
                      <div className="text-sm text-gray-600">SKU: {predecessorSelecionado.codigo}</div>
                    </div>
                    <button
                      type="button"
                      onClick={handleRemoverPredecessor}
                      className="text-red-600 hover:text-red-800"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            {/* Motivo da Substituição */}
            {predecessorSelecionado && (
              <div className="p-4 bg-white rounded-lg border-2 border-amber-300">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  📝 Motivo da Substituição
                </label>
                <select
                  value={formData.motivo_descontinuacao}
                  onChange={(e) => handleChange('motivo_descontinuacao', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent mb-2"
                >
                  <option value="">Selecione o motivo...</option>
                  <option value="Mudança de embalagem">Mudança de embalagem</option>
                  <option value="Mudança de peso/gramatura">Mudança de peso/gramatura</option>
                  <option value="Reformulação do produto">Reformulação do produto</option>
                  <option value="Mudança de fornecedor">Mudança de fornecedor</option>
                  <option value="Upgrade de linha">Upgrade de linha</option>
                  <option value="Outro">Outro (descrever abaixo)</option>
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
                  <strong>ℹ️ O que acontecerá:</strong>
                  <ul className="mt-2 space-y-1 list-disc list-inside">
                    <li>O produto "<strong>{predecessorSelecionado.nome}</strong>" será marcado como <strong>descontinuado</strong></li>
                    <li>Todo o histórico de vendas será mantido e poderá ser consultado</li>
                    <li>Você poderá gerar relatórios consolidados somando ambos os produtos</li>
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}
        
        {!mostrarBuscaPredecessor && (
          <p className="text-sm text-gray-600 mt-2">
            Marque esta opção se este produto substitui outro já cadastrado (ex: mudança de embalagem de 350g para 300g).
            Isso permite manter o histórico consolidado de vendas.
          </p>
        )}
      </div>
    </div>
  )}
  
  {/* =========================================
      CONTROLE DE TIPO DE PRODUTO (NOVO)
      ========================================= */}
  {!isEdicao && (
    <div className="border-t pt-6">
      <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
          </svg>
          Tipo do Produto
        </h3>
        
        <p className="text-sm text-gray-600 mb-4">
          Escolha o tipo de produto que está cadastrando:
        </p>
        
        <div className="space-y-3">
          {/* Produto Simples */}
          <div className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
               style={{ borderColor: formData.tipo_produto === 'SIMPLES' ? '#3b82f6' : '#e5e7eb' }}>
            <input
              type="radio"
              id="tipo_simples"
              name="tipo_produto"
              value="SIMPLES"
              checked={formData.tipo_produto === 'SIMPLES'}
              onChange={(e) => {
                handleChange('tipo_produto', 'SIMPLES');
                setFormData(prev => ({ ...prev, composicao_kit: [], e_kit_fisico: false }));
              }}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="flex-1">
              <label htmlFor="tipo_simples" className="font-medium text-gray-900 cursor-pointer">
                ✅ Produto Simples
              </label>
              <p className="text-sm text-gray-600 mt-1">
                Produto único, vendável, com controle de estoque próprio.
              </p>
            </div>
          </div>
          
          {/* Produto com Variações */}
          <div className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
               style={{ borderColor: formData.tipo_produto === 'PAI' ? '#3b82f6' : '#e5e7eb' }}>
            <input
              type="radio"
              id="tipo_variacoes"
              name="tipo_produto"
              value="PAI"
              checked={formData.tipo_produto === 'PAI'}
              onChange={(e) => {
                handleChange('tipo_produto', 'PAI');
                // Produto PAI não tem preço próprio
                setFormData(prev => ({
                  ...prev,
                  preco_custo: '',
                  preco_venda: '',
                  preco_promocional: '',
                  composicao_kit: [],
                  e_kit_fisico: false
                }));
              }}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="flex-1">
              <label htmlFor="tipo_variacoes" className="font-medium text-gray-900 cursor-pointer">
                📦 Produto com Variações
              </label>
              <p className="text-sm text-gray-600 mt-1">
                Produto agrupador (não vendável). Terá variações com SKU, preço e estoque próprios.
                <br />
                <span className="text-xs italic">Exemplo: Camiseta (produto pai) → P, M, G (variações)</span>
              </p>
              {formData.tipo_produto === 'PAI' && !isEdicao && (
                <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
                  ⚠️ <strong>Salve o produto primeiro</strong> para depois cadastrar as variações na aba "Variações".
                </div>
              )}
              {formData.tipo_produto === 'PAI' && isEdicao && (
                <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                  ✅ Produto salvo! Vá para a aba "📦 Variações" para cadastrar as variações.
                </div>
              )}
            </div>
          </div>
          
          {/* Produto Kit/Composição */}
          <div className="flex items-start gap-3 p-4 bg-white rounded-lg border-2 hover:border-blue-400 transition-colors"
               style={{ borderColor: formData.tipo_produto === 'KIT' ? '#3b82f6' : '#e5e7eb' }}>
            <input
              type="radio"
              id="tipo_kit"
              name="tipo_produto"
              value="KIT"
              checked={formData.tipo_produto === 'KIT'}
              onChange={(e) => {
                handleChange('tipo_produto', 'KIT');
                setAbaAtiva(9); // Abre automaticamente a aba de composição
              }}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="flex-1">
              <label htmlFor="tipo_kit" className="font-medium text-gray-900 cursor-pointer">
                🧩 Produto com Composição (Kit)
              </label>
              <p className="text-sm text-gray-600 mt-1">
                Kit composto por outros produtos existentes.
                <br />
                <span className="text-xs italic">Exemplo: Kit Banho (shampoo + condicionador + toalha)</span>
              </p>
              {formData.tipo_produto === 'KIT' && (
                <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                  ✅ <strong>Aba "🧩 Composição" aberta!</strong> Vá para a aba Composição para definir se o kit terá estoque virtual ou físico e adicionar os produtos que o compõem.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )}
  
  {/* =========================================
      CHECKBOX: VARIACAO PODE SER KIT (Apenas em edição de variação)
      ========================================= */}
  {isEdicao && formData.tipo_produto === 'VARIACAO' && (
    <div className="border-t pt-6">
      <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Composição (Kit)
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
                setAbaAtiva(9); // Abre aba de composição
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
              🧩 Esta variação é um KIT (possui composição)
            </label>
            <p className="text-sm text-gray-600 mt-2">
              Marque esta opção se esta variação é composta por outros produtos.
              <br />
              <span className="text-xs italic">Exemplo: Camiseta P - Kit (camiseta + brinde)</span>
            </p>
            {formData.tipo_kit && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                ✅ <strong>Variação configurada como KIT!</strong> Vá para a aba "🧩 Composição" para definir os produtos que compõem este kit.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )}
</div>
  );
}
