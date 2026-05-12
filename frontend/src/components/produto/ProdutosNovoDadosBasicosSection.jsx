import { useMemo, useState } from 'react';
import SafeMarkdown from '../ui/SafeMarkdown';
import {
  CategoriaProdutoSelector,
  MarcaProdutoSelector,
} from '../produtos/CatalogoProdutoSelectors';
import ActionButton from '../ui/ActionButton';
import { normalizeMarkdownContent } from '../../utils/safeMarkdown';

export default function ProdutosNovoDadosBasicosSection({
  categoriasHierarquicas,
  departamentos,
  formData,
  handleChange,
  handleGerarCodigoBarras,
  handleGerarSKU,
  marcas,
}) {
  const [descricaoModo, setDescricaoModo] = useState('editar');
  const descricaoNormalizada = useMemo(
    () => normalizeMarkdownContent(formData.descricao),
    [formData.descricao],
  );

  function handleDescricaoBlur() {
    if (descricaoNormalizada !== (formData.descricao || '')) {
      handleChange('descricao', descricaoNormalizada);
    }
  }

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
            <ActionButton type="button" onClick={handleGerarSKU} intent="neutral">
              Gerar
            </ActionButton>
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
            <ActionButton type="button" onClick={handleGerarCodigoBarras} intent="neutral">
              Gerar
            </ActionButton>
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
          <CategoriaProdutoSelector
            label="Categoria"
            categorias={categoriasHierarquicas}
            value={formData.categoria_id}
            onChange={(valor) => handleChange('categoria_id', valor)}
            placeholder="Selecione..."
            searchPlaceholder="Digite para buscar categoria..."
            inputClassName="border-gray-300"
          />
        </div>

        <div>
          <MarcaProdutoSelector
            label="Marca"
            marcas={marcas}
            value={formData.marca_id}
            onChange={(valor) => handleChange('marca_id', valor)}
            placeholder="Selecione..."
            searchPlaceholder="Digite para buscar marca..."
            inputClassName="border-gray-300"
          />
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
          <div className="mb-1 flex items-center justify-between gap-2">
            <label className="block text-sm font-medium text-gray-700">Descricao</label>
            <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
              <button
                type="button"
                onClick={() => setDescricaoModo('editar')}
                className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                  descricaoModo === 'editar'
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Editar
              </button>
              <button
                type="button"
                onClick={() => setDescricaoModo('previa')}
                className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                  descricaoModo === 'previa'
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Previa
              </button>
            </div>
          </div>

          {descricaoModo === 'editar' ? (
            <textarea
              value={formData.descricao}
              onChange={(e) => handleChange('descricao', e.target.value)}
              onBlur={handleDescricaoBlur}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows="4"
              placeholder="Descricao detalhada do produto..."
            />
          ) : (
            <div className="min-h-[104px] rounded-lg border border-gray-200 bg-white px-3 py-2">
              <SafeMarkdown value={descricaoNormalizada} empty="Sem descricao" />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
