export default function ContaPagarParcelamentoSection({ controller }) {
  const {
    atualizarDataParcela,
    atualizarValorParcela,
    dados,
    gerarPreview,
    intervaloParcelas,
    isEditando,
    previewParcelas,
    setDados,
    setIntervaloParcelas,
    setPreviewParcelas,
  } = controller;

  if (isEditando) return null;

  return (
    <section className="space-y-4 border-t pt-4">
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="eh_parcelado"
          checked={dados.eh_parcelado}
          onChange={(event) => {
            setDados({ ...dados, eh_parcelado: event.target.checked });
            if (!event.target.checked) setPreviewParcelas([]);
          }}
          disabled={dados.eh_recorrente}
          className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <label
          htmlFor="eh_parcelado"
          className="text-lg font-semibold text-gray-700 cursor-pointer"
        >
          💳 Parcelar esta conta
        </label>
      </div>

      {dados.eh_parcelado && !dados.eh_recorrente && (
        <div className="ml-6 space-y-4 p-4 bg-blue-50 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Número de Parcelas *
              </label>
              <input
                type="number"
                min="2"
                max="120"
                value={dados.total_parcelas}
                onChange={(event) => setDados({ ...dados, total_parcelas: event.target.value })}
                onBlur={gerarPreview}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Intervalo (dias)
              </label>
              <select
                value={intervaloParcelas}
                onChange={(event) => {
                  setIntervaloParcelas(parseInt(event.target.value));
                  setTimeout(gerarPreview, 100);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="7">7 dias (semanal)</option>
                <option value="14">14 dias (quinzenal)</option>
                <option value="15">15 dias</option>
                <option value="21">21 dias</option>
                <option value="30">30 dias (mensal)</option>
                <option value="60">60 dias (bimestral)</option>
                <option value="90">90 dias (trimestral)</option>
              </select>
            </div>

            <div>
              <button
                type="button"
                onClick={gerarPreview}
                className="mt-6 w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                📋 Gerar Preview
              </button>
            </div>
          </div>

          {previewParcelas.length > 0 && (
            <div className="mt-4">
              <h4 className="font-semibold text-gray-700 mb-3">📅 Preview das Parcelas</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {previewParcelas.map((parcela, index) => (
                  <div key={index} className="flex items-center gap-3 p-2 bg-white rounded border">
                    <span className="font-semibold text-gray-600 min-w-[80px]">
                      Parcela {parcela.numero}/{previewParcelas.length}
                    </span>
                    <input
                      type="number"
                      step="0.01"
                      value={parcela.valor}
                      onChange={(event) => atualizarValorParcela(index, event.target.value)}
                      className="w-32 px-2 py-1 border border-gray-300 rounded text-sm"
                      placeholder="Valor"
                    />
                    <input
                      type="date"
                      value={parcela.data_vencimento}
                      onChange={(event) => atualizarDataParcela(index, event.target.value)}
                      className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                    />
                  </div>
                ))}
              </div>
              <div className="mt-3 p-2 bg-gray-100 rounded">
                <strong>
                  Total: R${" "}
                  {previewParcelas.reduce((sum, parcela) => sum + parcela.valor, 0).toFixed(2)}
                </strong>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
