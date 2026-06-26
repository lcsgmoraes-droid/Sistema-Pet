export default function Aba2RecebimentosResult({ handleAvancar, resetarTudo, resultado }) {
  return (
    <>
      {/* Resultado */}
      {resultado && resultado.success && (
        <div className="space-y-4">
          {/* Aviso de Reprocessamento (se aplicável) */}
          {resultado.ja_conciliado && resultado.aviso_reprocessamento && (
            <div className="bg-orange-50 border-l-4 border-orange-400 p-4 rounded-lg">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-6 w-6 text-orange-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <div className="ml-3 flex-1">
                  <h3 className="text-sm font-medium text-orange-800">
                    ⚠️ REPROCESSAMENTO DETECTADO
                  </h3>
                  <div className="mt-2 text-sm text-orange-700">
                    <p>{resultado.aviso_reprocessamento.mensagem}</p>
                    {resultado.aviso_reprocessamento.usuario_anterior && (
                      <p className="mt-1">
                        <span className="font-medium">Processado anteriormente por:</span>{" "}
                        {resultado.aviso_reprocessamento.usuario_anterior}
                      </p>
                    )}
                  </div>
                  <div className="mt-3">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                      Data: {resultado.data_referencia} | Operadora: {resultado.operadora_detectada}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Informações da Conciliação */}
          {(resultado.operadora_detectada || resultado.data_referencia) && (
            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-lg">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-blue-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">Informações da Conciliação</h3>
                  <div className="mt-2 text-sm text-blue-700 space-y-1">
                    {resultado.operadora_detectada && (
                      <p>
                        <span className="font-medium">Operadora:</span>{" "}
                        {resultado.operadora_detectada}
                        {resultado.confianca_deteccao && (
                          <span className="ml-2 text-xs">
                            (Confiança: {(resultado.confianca_deteccao * 100).toFixed(0)}%)
                          </span>
                        )}
                      </p>
                    )}
                    {resultado.data_referencia && (
                      <p>
                        <span className="font-medium">Data de Referência:</span>{" "}
                        {new Date(resultado.data_referencia + "T00:00:00").toLocaleDateString(
                          "pt-BR",
                        )}
                      </p>
                    )}
                    {resultado.historico_id && (
                      <p>
                        <span className="font-medium">ID do Histórico:</span> #
                        {resultado.historico_id}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Resumo dos Valores */}
          <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <svg
                className="h-6 w-6 text-blue-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
              Resumo da Validação em Cascata
            </h3>

            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-xs text-blue-600 font-medium mb-1">1️⃣ Recebimentos Detalhados</p>
                <p className="text-2xl font-bold text-blue-900">
                  R$ {resultado.valor_total_recebimentos?.toFixed(2)}
                </p>
                <p className="text-xs text-blue-600 mt-1">
                  {resultado.recebimentos_salvos} transações
                </p>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-xs text-green-600 font-medium mb-1">2️⃣ Comprovante (Lotes)</p>
                <p className="text-2xl font-bold text-green-900">
                  R$ {resultado.valor_total_lotes?.toFixed(2)}
                </p>
                <p className="text-xs text-green-600 mt-1">{resultado.lotes_count} lotes</p>
              </div>

              <div className="bg-purple-50 rounded-lg p-4">
                <p className="text-xs text-purple-600 font-medium mb-1">
                  3️⃣ Extrato Bancário (OFX)
                </p>
                <p className="text-2xl font-bold text-purple-900">
                  R$ {resultado.valor_total_ofx?.toFixed(2)}
                </p>
                <p className="text-xs text-purple-600 mt-1">{resultado.ofx_count} créditos</p>
              </div>
            </div>
          </div>

          {/* Status: Sem Divergências */}
          {!resultado.tem_divergencias && (
            <div className="bg-green-50 border-l-4 border-green-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-800">
                    ✅ Validação Perfeita! Nenhuma divergência encontrada.
                  </h3>
                  <p className="mt-1 text-sm text-green-700">
                    Todas as 3 somas estão idênticas. As {resultado.recebimentos_salvos} vendas
                    foram confirmadas na conta.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Status: Com Divergências (Informativo) */}
          {resultado.tem_divergencias &&
            resultado.divergencias &&
            resultado.divergencias.length > 0 && (
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-5 w-5 text-yellow-400"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3 flex-1">
                    <h3 className="text-sm font-medium text-yellow-800">
                      ⚠️ Divergências Detectadas
                    </h3>
                    <p className="mt-1 text-sm text-yellow-700">
                      Foram encontradas diferenças entre os arquivos. Analise abaixo e decida se
                      aceita ou não.
                    </p>

                    {/* Divergências Detalhadas */}
                    <div className="mt-4 space-y-3">
                      {resultado.divergencias.map((div, idx) => {
                        const isArredondamento = div.nivel === "arredondamento";
                        const bgColor = isArredondamento
                          ? "bg-blue-50 border-blue-200"
                          : "bg-orange-50 border-orange-200";
                        const textColor = isArredondamento ? "text-blue-900" : "text-orange-900";
                        const badgeColor = isArredondamento
                          ? "bg-blue-100 text-blue-800"
                          : "bg-orange-100 text-orange-800";

                        return (
                          <div key={idx} className={`border rounded-lg p-4 ${bgColor}`}>
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span
                                  className={`text-xs font-semibold px-2 py-1 rounded ${badgeColor}`}
                                >
                                  {isArredondamento ? "🔵 Arredondamento" : "🟠 Atenção"}
                                </span>
                                <p className={`text-sm font-medium ${textColor}`}>
                                  {div.tipo === "recebimentos_vs_lotes"
                                    ? "Recebimentos × Lotes"
                                    : "Lotes × OFX"}
                                </p>
                              </div>
                              <div className={`text-right ${textColor}`}>
                                <p className="text-lg font-bold">
                                  R$ {Math.abs(div.diferenca).toFixed(2)}
                                </p>
                                <p className="text-xs">{div.percentual?.toFixed(3)}%</p>
                              </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3 text-xs">
                              <div>
                                <p className="text-gray-600">
                                  {div.tipo === "recebimentos_vs_lotes"
                                    ? "Recebimentos:"
                                    : "Lotes:"}
                                </p>
                                <p className={`font-semibold ${textColor}`}>
                                  R${" "}
                                  {(div.tipo === "recebimentos_vs_lotes"
                                    ? div.soma_recebimentos
                                    : div.soma_lotes
                                  )?.toFixed(2)}
                                </p>
                              </div>
                              <div>
                                <p className="text-gray-600">
                                  {div.tipo === "recebimentos_vs_lotes" ? "Lotes:" : "OFX:"}
                                </p>
                                <p className={`font-semibold ${textColor}`}>
                                  R${" "}
                                  {(div.tipo === "recebimentos_vs_lotes"
                                    ? div.soma_lotes
                                    : div.soma_ofx
                                  )?.toFixed(2)}
                                </p>
                              </div>
                            </div>

                            <p className="text-xs text-gray-600 mt-2 italic">{div.mensagem}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}

          {/* Botões de Ação */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="text-sm text-gray-600">
              {resultado.tem_divergencias ? (
                <p>⚠️ Analise as divergências e decida se aceita a validação</p>
              ) : (
                <p>✅ Validação perfeita! Pode avançar para a Aba 3.</p>
              )}
            </div>
            <div className="flex gap-3">
              {resultado.tem_divergencias && (
                <button
                  onClick={resetarTudo}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium"
                >
                  ✕ Cancelar e Recomeçar
                </button>
              )}
              <button
                onClick={() => {
                  console.log("🖱️ Botão Aceitar e Avançar clicado");
                  handleAvancar();
                }}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  resultado.tem_divergencias
                    ? "bg-yellow-600 hover:bg-yellow-700 text-white"
                    : "bg-green-600 hover:bg-green-700 text-white"
                }`}
              >
                {resultado.tem_divergencias ? "✓ Aceitar e Avançar →" : "Avançar para Aba 3 →"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
