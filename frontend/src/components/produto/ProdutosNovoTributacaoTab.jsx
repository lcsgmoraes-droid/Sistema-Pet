const InfoTooltip = ({ title }) => (
  <span className="tooltip-icon" title={title}>
    🛈
  </span>
);

export default function ProdutosNovoTributacaoTab({
  formData,
  handleChangeTributacao,
  handlePersonalizarFiscal,
}) {
  return (
    <div className="space-y-6">
      {formData.tributacao?.herdado_da_empresa && (
        <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded-lg">
          <div className="flex items-start gap-3">
            <div className="text-yellow-600 text-xl">🏢</div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-yellow-900">Fiscal herdado da empresa</h3>
              <p className="text-sm text-yellow-800 mt-1">
                Este produto está usando a configuração fiscal padrão da empresa.
              </p>
              <div className="mt-3">
                <button
                  type="button"
                  className="px-4 py-2 bg-yellow-100 text-yellow-900 rounded-lg hover:bg-yellow-200 text-sm"
                  onClick={handlePersonalizarFiscal}
                >
                  ✏️ Personalizar fiscal deste produto
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Origem <InfoTooltip title="Define se o produto é nacional ou importado. Impacta o cálculo do ICMS." />
          </label>
          <select
            value={formData.tributacao?.origem_mercadoria || '0'}
            onChange={(e) => handleChangeTributacao('origem_mercadoria', e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            <option value="0">0 - Nacional</option>
            <option value="1">1 - Estrangeira (Importação direta)</option>
            <option value="2">2 - Estrangeira (Adquirida no mercado interno)</option>
            <option value="3">3 - Nacional (&gt; 40% conteúdo importado)</option>
            <option value="4">4 - Nacional (Conforme processo produtivo básico)</option>
            <option value="5">5 - Nacional (&lt; 40% conteúdo importado)</option>
            <option value="6">6 - Estrangeira (Importação direta sem similar)</option>
            <option value="7">7 - Estrangeira (Mercado interno sem similar)</option>
            <option value="8">8 - Nacional (&gt; 70% conteúdo importado)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            NCM <InfoTooltip title="Nomenclatura Comum do Mercosul. Classificação fiscal do produto, base para impostos." />
          </label>
          <input
            type="text"
            value={formData.tributacao?.ncm || ''}
            onChange={(e) => handleChangeTributacao('ncm', e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="00000000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CEST <InfoTooltip title="Código Especificador da Substituição Tributária. Para produtos sujeitos a ICMS ST." />
          </label>
          <input
            type="text"
            value={formData.tributacao?.cest || ''}
            onChange={(e) => handleChangeTributacao('cest', e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0000000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CFOP <InfoTooltip title="Código Fiscal de Operações e Prestações. Define a natureza da operação de venda." />
          </label>
          <input
            type="text"
            value={formData.tributacao?.cfop || ''}
            onChange={(e) => handleChangeTributacao('cfop', e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Alíquota ICMS (%) <InfoTooltip title="Imposto sobre Circulação de Mercadorias. Alíquota estadual aplicada na venda. Impacta o preço final." />
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.tributacao?.icms_aliquota || ''}
            onChange={(e) => handleChangeTributacao('icms_aliquota', e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0,00"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Alíquota PIS (%) <InfoTooltip title="Programa de Integração Social. Contribuição federal sobre a venda. Geralmente 1,65%." />
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.tributacao?.pis_aliquota || ''}
            onChange={(e) => handleChangeTributacao('pis_aliquota', e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0,00"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Alíquota COFINS (%) <InfoTooltip title="Contribuição para Financiamento da Seguridade Social. Contribuição federal sobre a venda. Geralmente 7,6%." />
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.tributacao?.cofins_aliquota || ''}
            onChange={(e) => handleChangeTributacao('cofins_aliquota', e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0,00"
          />
        </div>
      </div>
    </div>
  );
}
