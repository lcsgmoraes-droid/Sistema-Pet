export default function ProdutosNovoDadosBasicosSection({
  categoriasHierarquicas,
  departamentos,
  formData,
  handleChange,
  handleGerarCodigoBarras,
  handleGerarSKU,
  marcas,
}) {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">SKU *</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={formData.sku}
              onChange={(e) => handleChange('sku', e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Ex: PROD0001"
            />
            <button type="button" onClick={handleGerarSKU} className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm">
              Gerar
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Esse valor e salvo como o SKU oficial do produto.
            {formData.codigo ? ` Atual: ${formData.codigo}` : ''}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Codigo de Barras</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={formData.codigo_barras}
              onChange={(e) => handleChange('codigo_barras', e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="EAN-13"
            />
            <button type="button" onClick={handleGerarCodigoBarras} className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm">
              Gerar
            </button>
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Produto *</label>
        <input
          type="text"
          value={formData.nome}
          onChange={(e) => handleChange('nome', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Ex: Racao Golden para Caes Adultos 15kg"
          required
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
          <select value={formData.tipo} onChange={(e) => handleChange('tipo', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
            <option value="produto">Produto</option>
            <option value="servico">Servico</option>
            <option value="ambos">Produto e Servico</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Departamento</label>
          <select value={formData.departamento_id} onChange={(e) => handleChange('departamento_id', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
            <option value="">Selecione...</option>
            {departamentos.map((dep) => (
              <option key={dep.id} value={dep.id}>{dep.nome}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Categoria</label>
          <select value={formData.categoria_id} onChange={(e) => handleChange('categoria_id', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
            <option value="">Selecione...</option>
            {categoriasHierarquicas.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.nomeFormatado}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Marca</label>
          <select value={formData.marca_id} onChange={(e) => handleChange('marca_id', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
            <option value="">Selecione...</option>
            {marcas.map((marca) => (
              <option key={marca.id} value={marca.id}>{marca.nome}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Unidade</label>
          <select value={formData.unidade} onChange={(e) => handleChange('unidade', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
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
          <label className="block text-sm font-medium text-gray-700 mb-1">Descricao</label>
          <textarea
            value={formData.descricao}
            onChange={(e) => handleChange('descricao', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows="2"
            placeholder="Descricao detalhada do produto..."
          />
        </div>
      </div>
    </>
  );
}
