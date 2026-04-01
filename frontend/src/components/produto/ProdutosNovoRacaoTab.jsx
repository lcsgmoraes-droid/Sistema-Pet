import TabelaConsumoEditor from '../TabelaConsumoEditor';

export default function ProdutosNovoRacaoTab({
  formData,
  handleChange,
  handleApresentacaoPesoChange,
  handleClassificacaoRacaoChange,
  handleFasePublicoChange,
  opcoesApresentacoes,
  opcoesFases,
  opcoesLinhas,
  opcoesPortes,
  opcoesSabores,
  opcoesTratamentos,
}) {
  return (
    <div className="space-y-6">
      <div className="bg-orange-50 border-l-4 border-orange-500 p-4 mb-6">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-orange-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-orange-800">Calculadora de Ração (Fase 2)</h3>
            <div className="mt-2 text-sm text-orange-700">
              <p>Configure informações de ração para usar na calculadora de duração e custo.</p>
              <p className="mt-1">A IA usará esses dados para recomendar rações aos clientes.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            É ração?
          </label>
          <select
            value={formData.classificacao_racao || 'nao'}
            onChange={(e) => handleClassificacaoRacaoChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          >
            <option value="nao">Não</option>
            <option value="sim">Sim</option>
          </select>
        </div>
      </div>

      {formData.classificacao_racao === 'sim' && (
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4">
          <h4 className="text-sm font-semibold text-blue-900 mb-4">📋 Informações Detalhadas da Ração</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Linha
              </label>
              <select
                value={formData.linha_racao_id}
                onChange={(e) => handleChange('linha_racao_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Selecione...</option>
                {opcoesLinhas.map((linha) => (
                  <option key={linha.id} value={linha.id}>{linha.nome}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Porte do Animal
              </label>
              <select
                value={formData.porte_animal_id}
                onChange={(e) => handleChange('porte_animal_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Selecione...</option>
                {opcoesPortes.map((porte) => (
                  <option key={porte.id} value={porte.id}>{porte.nome}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fase/Público
              </label>
              <select
                value={formData.fase_publico_id}
                onChange={(e) => handleFasePublicoChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Selecione...</option>
                {opcoesFases.map((fase) => (
                  <option key={fase.id} value={fase.id}>{fase.nome}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tratamento <span className="text-gray-400">(Opcional)</span>
              </label>
              <select
                value={formData.tipo_tratamento_id}
                onChange={(e) => handleChange('tipo_tratamento_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Nenhum</option>
                {opcoesTratamentos.map((tratamento) => (
                  <option key={tratamento.id} value={tratamento.id}>{tratamento.nome}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sabor/Proteína
              </label>
              <select
                value={formData.sabor_proteina_id}
                onChange={(e) => handleChange('sabor_proteina_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Selecione...</option>
                {opcoesSabores.map((sabor) => (
                  <option key={sabor.id} value={sabor.id}>{sabor.nome}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Apresentação (Peso)
              </label>
              <select
                value={formData.apresentacao_peso_id}
                onChange={(e) => handleApresentacaoPesoChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Selecione...</option>
                {opcoesApresentacoes.map((apr) => (
                  <option key={apr.id} value={apr.id}>{apr.peso_kg}kg</option>
                ))}
              </select>
            </div>
          </div>

          <p className="text-xs text-blue-600 mt-3">
            💡 <strong>Dica:</strong> Essas informações ajudam a IA a recomendar a ração ideal para cada pet no PDV.
            Você pode gerenciar as opções disponíveis em <strong>Cadastros &gt; Opções de Ração</strong>.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Espécies Indicadas
          </label>
          <div className="flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="especies_indicadas"
                value="both"
                checked={formData.especies_indicadas === 'both'}
                onChange={(e) => handleChange('especies_indicadas', e.target.value)}
                className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300"
              />
              <span className="ml-2 text-sm text-gray-700">🐶🐱 Ambos</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="especies_indicadas"
                value="dog"
                checked={formData.especies_indicadas === 'dog'}
                onChange={(e) => handleChange('especies_indicadas', e.target.value)}
                className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300"
              />
              <span className="ml-2 text-sm text-gray-700">🐶 Cães</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="especies_indicadas"
                value="cat"
                checked={formData.especies_indicadas === 'cat'}
                onChange={(e) => handleChange('especies_indicadas', e.target.value)}
                className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300"
              />
              <span className="ml-2 text-sm text-gray-700">🐱 Gatos</span>
            </label>
          </div>
        </div>
      </div>

      <input type="hidden" value={formData.tabela_nutricional} />

      <div>
        <TabelaConsumoEditor
          value={formData.tabela_consumo}
          onChange={(value) => handleChange('tabela_consumo', value)}
          pesoEmbalagem={parseFloat(formData.peso_embalagem) || null}
        />
      </div>

      {formData.peso_embalagem && formData.classificacao_racao && (
        <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
          <h4 className="text-sm font-semibold text-orange-900 mb-2">📊 Preview da Calculadora</h4>
          <div className="text-sm text-orange-700 space-y-1">
            <p>✓ Peso: <strong>{formData.peso_embalagem}kg</strong></p>
            <p>✓ Classificação: <strong>{formData.classificacao_racao.replace('_', ' ')}</strong></p>
            {formData.categoria_racao && <p>✓ Categoria: <strong>{formData.categoria_racao}</strong></p>}
            {formData.tabela_consumo && <p className="text-green-600">✓ Tabela de consumo configurada</p>}
            {!formData.tabela_consumo && <p className="text-yellow-600">⚠️ Sem tabela de consumo (usará cálculo genérico)</p>}
            <p className="mt-2 text-orange-800">
              💡 Use a Calculadora de Ração para ver duração e custo/dia
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
