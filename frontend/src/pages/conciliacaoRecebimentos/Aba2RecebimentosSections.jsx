export function Aba2RecebimentosModals({
  confiancaDeteccao,
  handleValidar,
  mostrarModalConfirmacao,
  mostrarModalDivergencia,
  operadoraDetectada,
  operadoraSelecionada,
  operadoras,
  resetarTudo,
  setIgnorarDivergenciaOperadora,
  setMostrarModalConfirmacao,
  setMostrarModalDivergencia,
  setOperadoraSelecionada,
  setProcessando,
}) {
  return (
    <>
      {/* Modal de Confirmação - Antes de Validar */}
      {mostrarModalConfirmacao && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            {/* Overlay */}
            <div
              className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
              onClick={() => setMostrarModalConfirmacao(false)}
            ></div>

            {/* Modal */}
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
                    <svg
                      className="h-6 w-6 text-blue-600"
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
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Confirmar Operadora
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        Você está prestes a validar recebimentos para a operadora:
                      </p>
                      <div className="mt-3 p-3 bg-blue-50 rounded border border-blue-200">
                        <p className="text-lg font-bold text-blue-900">
                          🏦 {operadoraSelecionada?.nome}
                        </p>
                      </div>
                      <p className="text-sm text-gray-500 mt-3">
                        ⚠️ <strong>Todos os lançamentos serão vinculados a esta operadora.</strong>
                      </p>
                      <p className="text-xs text-gray-400 mt-2">
                        O sistema detectará automaticamente se os arquivos correspondem a esta
                        operadora e alertará se houver divergência.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={handleValidar}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                >
                  ✓ Confirmar e Validar
                </button>
                <button
                  type="button"
                  onClick={() => setMostrarModalConfirmacao(false)}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Divergência de Operadora */}
      {mostrarModalDivergencia && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            {/* Overlay */}
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>

            {/* Modal */}
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-orange-100 sm:mx-0 sm:h-10 sm:w-10">
                    <svg
                      className="h-6 w-6 text-orange-600"
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
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
                    <h3 className="text-lg leading-6 font-bold text-orange-900">
                      ⚠️ Divergência de Operadora Detectada
                    </h3>
                    <div className="mt-4">
                      <p className="text-sm text-gray-700 mb-4">
                        <strong>
                          Os arquivos enviados parecem ser de uma operadora diferente da
                          selecionada.
                        </strong>
                      </p>

                      <div className="space-y-3">
                        {/* Operadora Selecionada */}
                        <div className="p-3 bg-red-50 border-2 border-red-300 rounded-lg">
                          <p className="text-xs text-red-600 font-medium mb-1">
                            Operadora Selecionada:
                          </p>
                          <p className="text-lg font-bold text-red-900">
                            {operadoraSelecionada?.nome}
                          </p>
                        </div>

                        {/* Operadora Detectada */}
                        <div className="p-3 bg-green-50 border-2 border-green-300 rounded-lg">
                          <p className="text-xs text-green-600 font-medium mb-1">
                            Operadora Detectada nos Arquivos:
                          </p>
                          <p className="text-lg font-bold text-green-900">{operadoraDetectada}</p>
                          <p className="text-xs text-green-700 mt-1">
                            Confiança da detecção: {(confiancaDeteccao * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                        <p className="text-sm text-yellow-800">
                          <strong>O que você deseja fazer?</strong>
                        </p>
                        <ul className="text-xs text-yellow-700 mt-2 space-y-1 list-disc list-inside">
                          <li>
                            <strong>Mudar para {operadoraDetectada}:</strong> Recomendado se os
                            arquivos estão corretos
                          </li>
                          <li>
                            <strong>Manter {operadoraSelecionada?.nome}:</strong> Use se você tem
                            certeza da operadora
                          </li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse gap-3">
                <button
                  type="button"
                  onClick={() => {
                    // Mudar para operadora detectada
                    const operadoraNova = operadoras.find((op) => op.nome === operadoraDetectada);
                    if (operadoraNova) {
                      setOperadoraSelecionada(operadoraNova);
                    }
                    setMostrarModalDivergencia(false);
                    // Processar com nova operadora
                    setTimeout(() => {
                      handleValidar();
                    }, 100);
                  }}
                  className="inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 focus:outline-none sm:text-sm"
                >
                  ✓ Mudar para {operadoraDetectada}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    // Manter operadora selecionada e continuar (ignorando divergência)
                    setIgnorarDivergenciaOperadora(true);
                    setMostrarModalDivergencia(false);

                    // Reprocessar com divergência ignorada
                    setTimeout(() => {
                      handleValidar();
                    }, 100);
                  }}
                  className="inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:text-sm"
                >
                  Manter {operadoraSelecionada?.nome}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMostrarModalDivergencia(false);
                    setProcessando(false);
                    resetarTudo();
                  }}
                  className="inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:text-sm"
                >
                  ✕ Cancelar Tudo
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
