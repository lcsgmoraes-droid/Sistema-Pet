const InfoTooltip = ({ title }) => (
  <span className="tooltip-icon" title={title}>
    🛈
  </span>
);

const opcoesIcms = [
  ["", "Selecione..."],
  ["00", "00 - Tributada integralmente"],
  ["10", "10 - Tributada com ICMS por ST"],
  ["20", "20 - Com redução de base"],
  ["30", "30 - Isenta com ICMS por ST"],
  ["40", "40 - Isenta"],
  ["41", "41 - Não tributada"],
  ["50", "50 - Suspensão"],
  ["51", "51 - Diferimento"],
  ["60", "60 - ICMS cobrado anteriormente por ST"],
  ["70", "70 - Redução de base com ICMS por ST"],
  ["90", "90 - Outros"],
  ["101", "101 - Simples Nacional com permissão de crédito"],
  ["102", "102 - Simples Nacional sem permissão de crédito"],
  ["103", "103 - Simples Nacional com isenção por faixa de receita"],
  ["201", "201 - Simples Nacional com crédito e ICMS por ST"],
  ["202", "202 - Simples Nacional sem crédito e com ICMS por ST"],
  ["203", "203 - Simples Nacional com isenção e ICMS por ST"],
  ["300", "300 - Simples Nacional, imune"],
  ["400", "400 - Simples Nacional, não tributada"],
  ["500", "500 - Simples Nacional, ICMS cobrado anteriormente por ST"],
  ["900", "900 - Simples Nacional, outros"],
];

const opcoesPisCofins = [
  ["", "Selecione..."],
  ["01", "01 - Operação tributável, alíquota normal"],
  ["02", "02 - Operação tributável, alíquota diferenciada"],
  ["03", "03 - Operação tributável por unidade"],
  ["04", "04 - Tributação monofásica, alíquota zero"],
  ["05", "05 - Substituição tributária"],
  ["06", "06 - Alíquota zero"],
  ["07", "07 - Isenta"],
  ["08", "08 - Sem incidência"],
  ["09", "09 - Suspensão"],
  ["49", "49 - Outras operações de saída"],
  ["99", "99 - Outras operações"],
];

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
            Origem{" "}
            <InfoTooltip title="Define se o produto é nacional ou importado. Impacta o cálculo do ICMS." />
          </label>
          <select
            value={formData.tributacao?.origem_mercadoria || "0"}
            onChange={(e) => handleChangeTributacao("origem_mercadoria", e.target.value)}
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
            NCM{" "}
            <InfoTooltip title="Nomenclatura Comum do Mercosul. Classificação fiscal do produto, base para impostos." />
          </label>
          <input
            type="text"
            value={formData.tributacao?.ncm || ""}
            onChange={(e) => handleChangeTributacao("ncm", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="00000000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CEST{" "}
            <InfoTooltip title="Código Especificador da Substituição Tributária. Para produtos sujeitos a ICMS ST." />
          </label>
          <input
            type="text"
            value={formData.tributacao?.cest || ""}
            onChange={(e) => handleChangeTributacao("cest", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0000000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CFOP{" "}
            <InfoTooltip title="Código Fiscal de Operações e Prestações. Define a natureza da operação de venda." />
          </label>
          <input
            type="text"
            value={formData.tributacao?.cfop || ""}
            onChange={(e) => handleChangeTributacao("cfop", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CSOSN/CST do ICMS{" "}
            <InfoTooltip title="Código da situação tributária do ICMS. No Simples Nacional, use um CSOSN de três dígitos." />
          </label>
          <select
            value={formData.tributacao?.cst_icms || ""}
            onChange={(e) => handleChangeTributacao("cst_icms", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {opcoesIcms.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CST do PIS{" "}
            <InfoTooltip title="Código da situação tributária do PIS aplicado à saída deste produto." />
          </label>
          <select
            value={formData.tributacao?.pis_cst || ""}
            onChange={(e) => handleChangeTributacao("pis_cst", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {opcoesPisCofins.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CST do COFINS{" "}
            <InfoTooltip title="Código da situação tributária da COFINS aplicado à saída deste produto." />
          </label>
          <select
            value={formData.tributacao?.cofins_cst || ""}
            onChange={(e) => handleChangeTributacao("cofins_cst", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {opcoesPisCofins.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Alíquota ICMS (%){" "}
            <InfoTooltip title="Imposto sobre Circulação de Mercadorias. Alíquota estadual aplicada na venda. Impacta o preço final." />
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.tributacao?.icms_aliquota || ""}
            onChange={(e) => handleChangeTributacao("icms_aliquota", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0,00"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Alíquota PIS (%){" "}
            <InfoTooltip title="Programa de Integração Social. Contribuição federal sobre a venda. Geralmente 1,65%." />
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.tributacao?.pis_aliquota || ""}
            onChange={(e) => handleChangeTributacao("pis_aliquota", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0,00"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Alíquota COFINS (%){" "}
            <InfoTooltip title="Contribuição para Financiamento da Seguridade Social. Contribuição federal sobre a venda. Geralmente 7,6%." />
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.tributacao?.cofins_aliquota || ""}
            onChange={(e) => handleChangeTributacao("cofins_aliquota", e.target.value)}
            disabled={formData.tributacao?.herdado_da_empresa === true}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="0,00"
          />
        </div>
      </div>
    </div>
  );
}
