import PropTypes from 'prop-types';

function EntradaXmlResultadoLoteModal({
  aberto,
  onClose,
  resultadoLote,
  uploadingLote,
}) {
  if (!aberto) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white p-6">
          <h2 className="text-2xl font-bold">
            Resultado do Processamento em Lote
          </h2>
          {resultadoLote && (
            <p className="mt-2">
              {resultadoLote.sucessos} sucesso(s) | {resultadoLote.erros} erro(s) | Total: {resultadoLote.total_arquivos}
            </p>
          )}
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {uploadingLote && !resultadoLote && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-green-600 mb-4" />
              <p className="text-lg text-gray-600">Processando arquivos...</p>
            </div>
          )}

          {resultadoLote && (
            <>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-100 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-blue-600">{resultadoLote.total_arquivos}</div>
                  <div className="text-sm text-gray-600">Total</div>
                </div>
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-600">{resultadoLote.sucessos}</div>
                  <div className="text-sm text-gray-600">Sucessos</div>
                </div>
                <div className="bg-red-50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-600">{resultadoLote.erros}</div>
                  <div className="text-sm text-gray-600">Erros</div>
                </div>
              </div>

              <div className="space-y-3">
                {resultadoLote.resultados.map((resultado, idx) => (
                  <div
                    key={`${resultado.arquivo || 'resultado'}-${idx}`}
                    className={`border rounded-lg p-4 ${
                      resultado.sucesso
                        ? 'bg-green-50 border-green-200'
                        : 'bg-red-50 border-red-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`rounded px-2 py-1 text-xs font-semibold ${
                            resultado.sucesso
                              ? 'bg-green-100 text-green-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                          >
                            {resultado.sucesso ? 'OK' : 'ERRO'}
                          </span>
                          <span className="font-semibold text-gray-800">
                            {resultado.arquivo}
                          </span>
                        </div>

                        {resultado.sucesso ? (
                          <div className="text-sm space-y-1">
                            <p className="text-gray-700">
                              <strong>Nota:</strong> {resultado.numero_nota}
                            </p>
                            <p className="text-gray-700">
                              <strong>Fornecedor:</strong> {resultado.fornecedor}
                            </p>
                            <p className="text-gray-700">
                              <strong>Valor:</strong> R$ {resultado.valor_total?.toFixed(2)}
                            </p>
                            <p className="text-gray-700">
                              <strong>Produtos:</strong> {resultado.produtos_vinculados} vinculados, {resultado.produtos_nao_vinculados} nao vinculados
                            </p>
                          </div>
                        ) : (
                          <p className="text-sm text-red-700">{resultado.mensagem}</p>
                        )}
                      </div>
                      <span className="text-sm text-gray-500 ml-4">#{resultado.ordem}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="border-t p-6 bg-gray-50">
          <button
            onClick={onClose}
            disabled={uploadingLote}
            className="w-full px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold disabled:opacity-50 transition-colors"
          >
            {uploadingLote ? 'Processando...' : 'Fechar'}
          </button>
        </div>
      </div>
    </div>
  );
}

EntradaXmlResultadoLoteModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  resultadoLote: PropTypes.shape({
    sucessos: PropTypes.number,
    erros: PropTypes.number,
    total_arquivos: PropTypes.number,
    resultados: PropTypes.arrayOf(PropTypes.object),
  }),
  uploadingLote: PropTypes.bool.isRequired,
};

EntradaXmlResultadoLoteModal.defaultProps = {
  resultadoLote: null,
};

export default EntradaXmlResultadoLoteModal;
