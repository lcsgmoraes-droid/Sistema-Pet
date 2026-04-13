function formatMoeda(value, parseNumber) {
  return value ? `R$ ${parseNumber(value).toFixed(2).replace('.', ',')}` : 'R$ 0,00';
}

function formatPercentual(value, parseNumber) {
  return value ? `${parseNumber(value).toFixed(2).replace('.', ',')}%` : '0,00%';
}

export default function ProdutosNovoPrecosSection({
  camposEmEdicao,
  formData,
  handleChange,
  parseNumber,
  setCamposEmEdicao,
}) {
  if (formData.tipo_produto === 'PAI') {
    return null;
  }

  const lojaFisicaAtiva = formData.ativo !== false && formData.situacao !== false;

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Preco de Custo</label>
          <input
            type="text"
            value={camposEmEdicao.preco_custo ? (formData.preco_custo || '') : formatMoeda(formData.preco_custo, parseNumber)}
            onChange={(e) => {
              const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
              handleChange('preco_custo', value);
            }}
            onFocus={(e) => {
              setCamposEmEdicao((prev) => ({ ...prev, preco_custo: true }));
              e.target.select();
            }}
            onBlur={(e) => {
              setCamposEmEdicao((prev) => ({ ...prev, preco_custo: false }));
              const value = parseNumber(e.target.value);
              handleChange('preco_custo', value > 0 ? value.toFixed(2) : '');
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="R$ 0,00"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Markup</label>
          <input
            type="text"
            value={camposEmEdicao.markup ? (formData.markup || '') : formatPercentual(formData.markup, parseNumber)}
            onChange={(e) => {
              const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
              handleChange('markup', value);
            }}
            onFocus={(e) => {
              setCamposEmEdicao((prev) => ({ ...prev, markup: true }));
              e.target.select();
            }}
            onBlur={(e) => {
              setCamposEmEdicao((prev) => ({ ...prev, markup: false }));
              const value = parseNumber(e.target.value);
              handleChange('markup', value >= 0 ? value.toFixed(2) : '');
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="0,00%"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Preco de Venda *</label>
          <input
            type="text"
            value={camposEmEdicao.preco_venda ? (formData.preco_venda || '') : formatMoeda(formData.preco_venda, parseNumber)}
            onChange={(e) => {
              const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
              handleChange('preco_venda', value);
            }}
            onFocus={(e) => {
              setCamposEmEdicao((prev) => ({ ...prev, preco_venda: true }));
              e.target.select();
            }}
            onBlur={(e) => {
              setCamposEmEdicao((prev) => ({ ...prev, preco_venda: false }));
              const value = parseNumber(e.target.value);
              handleChange('preco_venda', value > 0 ? value.toFixed(2) : '');
            }}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="R$ 0,00"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Preco Promocional</label>
          <input
            type="text"
            value={camposEmEdicao.preco_promocional ? (formData.preco_promocional || '') : formatMoeda(formData.preco_promocional, parseNumber)}
            onChange={(e) => {
              const value = e.target.value.replace(/[^\d.,]/g, '').replace(',', '.');
              handleChange('preco_promocional', value);
            }}
            onFocus={(e) => {
              setCamposEmEdicao((prev) => ({ ...prev, preco_promocional: true }));
              e.target.select();
            }}
            onBlur={(e) => {
              setCamposEmEdicao((prev) => ({ ...prev, preco_promocional: false }));
              const value = parseNumber(e.target.value);
              handleChange('preco_promocional', value > 0 ? value.toFixed(2) : '');
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="R$ 0,00"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Inicio da Promocao (ERP)</label>
          <input
            type="date"
            value={formData.data_inicio_promocao}
            onChange={(e) => handleChange('data_inicio_promocao', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Fim da Promocao (ERP)</label>
          <input
            type="date"
            value={formData.data_fim_promocao}
            onChange={(e) => handleChange('data_fim_promocao', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">Precos por Canal (Ecommerce / App)</h3>
          <p className="text-xs text-gray-500 mt-1">Se deixar vazio, o sistema usa o preco de venda padrao.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs font-bold text-purple-700 uppercase">Ecommerce</div>
              <label className="flex items-center gap-2 text-xs text-gray-700">
                <input
                  type="checkbox"
                  checked={lojaFisicaAtiva && formData.anunciar_ecommerce !== false}
                  onChange={(e) => handleChange('anunciar_ecommerce', e.target.checked)}
                  disabled={!lojaFisicaAtiva}
                />
                Exibir no canal
              </label>
            </div>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.preco_ecommerce}
              onChange={(e) => handleChange('preco_ecommerce', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Preco normal"
            />
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.preco_ecommerce_promo}
              onChange={(e) => handleChange('preco_ecommerce_promo', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Preco promocional"
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
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs font-bold text-green-700 uppercase">App Movel</div>
              <label className="flex items-center gap-2 text-xs text-gray-700">
                <input
                  type="checkbox"
                  checked={lojaFisicaAtiva && formData.anunciar_app !== false}
                  onChange={(e) => handleChange('anunciar_app', e.target.checked)}
                  disabled={!lojaFisicaAtiva}
                />
                Exibir no canal
              </label>
            </div>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.preco_app}
              onChange={(e) => handleChange('preco_app', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              placeholder="Preco normal"
            />
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.preco_app_promo}
              onChange={(e) => handleChange('preco_app_promo', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              placeholder="Preco promocional"
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

        {!lojaFisicaAtiva && (
          <p className="text-xs text-amber-700">
            Produto inativo na loja fisica: anuncio em Ecommerce e App Movel fica desativado automaticamente.
          </p>
        )}
      </div>
    </>
  );
}
