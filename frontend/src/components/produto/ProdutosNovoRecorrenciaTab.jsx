export default function ProdutosNovoRecorrenciaTab({
  formData,
  handleChange,
  handleTipoRecorrenciaChange,
}) {
  return (
    <div className="space-y-6">
      <div className="bg-purple-50 border-l-4 border-purple-500 p-4 mb-6">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-purple-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-purple-800">Sistema de Recorrência (Fase 1)</h3>
            <div className="mt-2 text-sm text-purple-700">
              <p>Configure produtos que precisam ser recomprados periodicamente (vacinas, antipulgas, rações).</p>
              <p className="mt-1">O sistema criará lembretes automáticos para notificar clientes 7 dias antes.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center p-4 bg-gray-50 rounded-lg">
        <input
          type="checkbox"
          id="tem_recorrencia"
          checked={formData.tem_recorrencia}
          onChange={(e) => handleChange('tem_recorrencia', e.target.checked)}
          className="h-5 w-5 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
        />
        <label htmlFor="tem_recorrencia" className="ml-3">
          <span className="text-base font-medium text-gray-900">Produto com Recorrência</span>
          <p className="text-sm text-gray-500">Ativar lembretes automáticos para este produto</p>
        </label>
      </div>

      {formData.tem_recorrencia && (
        <div className="space-y-4 border-t pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Recorrência *
              </label>
              <select
                value={formData.tipo_recorrencia}
                onChange={(e) => handleTipoRecorrenciaChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="daily">Diária</option>
                <option value="weekly">Semanal (7 dias)</option>
                <option value="monthly">Mensal (30 dias)</option>
                <option value="yearly">Anual (365 dias)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Intervalo (em dias) *
              </label>
              <input
                type="number"
                min="1"
                value={formData.intervalo_dias}
                onChange={(e) => handleChange('intervalo_dias', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Ex: 30 (para Nexgard)"
              />
              <p className="text-xs text-gray-500 mt-1">
                Exemplos: Nexgard = 30, Vacina Anual = 365
              </p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Número de Doses (opcional)
            </label>
            <input
              type="number"
              min="1"
              value={formData.numero_doses}
              onChange={(e) => handleChange('numero_doses', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Ex: 3 (para vacina com 3 doses)"
            />
            <p className="text-xs text-gray-500 mt-1">
              💉 Se vazio, será recorrente indefinidamente. Se preenchido (ex: 3), o sistema finalizará após a última dose.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Compatibilidade por Espécie
            </label>
            <div className="flex gap-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="especie_compativel"
                  value="both"
                  checked={formData.especie_compativel === 'both'}
                  onChange={(e) => handleChange('especie_compativel', e.target.value)}
                  className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300"
                />
                <span className="ml-2 text-sm text-gray-700">🐶🐱 Cães e Gatos</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="especie_compativel"
                  value="dog"
                  checked={formData.especie_compativel === 'dog'}
                  onChange={(e) => handleChange('especie_compativel', e.target.value)}
                  className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300"
                />
                <span className="ml-2 text-sm text-gray-700">🐶 Apenas Cães</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="especie_compativel"
                  value="cat"
                  checked={formData.especie_compativel === 'cat'}
                  onChange={(e) => handleChange('especie_compativel', e.target.value)}
                  className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300"
                />
                <span className="ml-2 text-sm text-gray-700">🐱 Apenas Gatos</span>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Observações / Instruções
            </label>
            <textarea
              value={formData.observacoes_recorrencia}
              onChange={(e) => handleChange('observacoes_recorrencia', e.target.value)}
              rows="3"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Ex: Aplicar mensalmente no mesmo dia. Não atrasar mais de 5 dias."
            />
          </div>

          {formData.intervalo_dias && (
            <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
              <h4 className="text-sm font-semibold text-purple-900 mb-2">📌 Preview do Lembrete</h4>
              <div className="text-sm text-purple-700 space-y-1">
                <p>✓ Cliente será notificado <strong>7 dias antes</strong> da próxima dose</p>
                <p>✓ Intervalo configurado: <strong>{formData.intervalo_dias} dias</strong></p>
                <p>✓ Após a compra, um novo lembrete será criado automaticamente</p>
                {formData.especie_compativel !== 'both' && (
                  <p className="mt-2 text-purple-800">
                    ⚠️ Sistema validará se o pet é compatível na hora da venda
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
