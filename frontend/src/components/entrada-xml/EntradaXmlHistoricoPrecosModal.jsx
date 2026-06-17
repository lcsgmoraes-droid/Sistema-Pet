import PropTypes from "prop-types";

const formatCurrency = (value) => Number(value || 0).toFixed(2);

const motivoLabel = {
  nfe_entrada: "Entrada NF-e",
  nfe_revisao_precos: "Revisao de Precos",
  manual: "Ajuste Manual",
};

const motivoIcon = {
  nfe_entrada: "NF",
  nfe_revisao_precos: "R$",
  manual: "Edit",
};

function EntradaXmlHistoricoPrecosModal({
  aberto,
  carregandoHistorico,
  historicoPrecos,
  produtoHistorico,
  onClose,
}) {
  if (!aberto) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6">
          <h2 className="text-2xl font-bold">Historico de Alteracoes de Precos</h2>
          {produtoHistorico && <p className="mt-2 text-purple-100">{produtoHistorico.nome}</p>}
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {carregandoHistorico ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-600" />
            </div>
          ) : historicoPrecos.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">Nenhuma alteracao de preco registrada</p>
            </div>
          ) : (
            <div className="space-y-4">
              {historicoPrecos.map((hist) => (
                <div
                  key={hist.id}
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="inline-flex min-w-10 justify-center rounded bg-purple-50 px-2 py-1 text-sm font-semibold text-purple-700">
                          {motivoIcon[hist.motivo] || "Log"}
                        </span>
                        <span className="font-semibold text-gray-800">
                          {motivoLabel[hist.motivo] || hist.motivo}
                        </span>
                      </div>
                      {hist.referencia && (
                        <p className="text-sm text-gray-600 mt-1">{hist.referencia}</p>
                      )}
                      {hist.nota_numero && (
                        <p className="text-sm text-blue-600 mt-1">Nota: {hist.nota_numero}</p>
                      )}
                    </div>
                    <div className="text-right text-sm text-gray-500">
                      {new Date(hist.data).toLocaleString("pt-BR")}
                      {hist.usuario && <div className="text-xs mt-1">{hist.usuario}</div>}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {hist.preco_custo_anterior !== null && hist.preco_custo_novo !== null && (
                      <div className="bg-blue-50 rounded-lg p-3">
                        <div className="text-xs text-gray-600 font-semibold mb-2">CUSTO</div>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm text-gray-500">Anterior</div>
                            <div className="text-lg font-bold">
                              R$ {formatCurrency(hist.preco_custo_anterior)}
                            </div>
                          </div>
                          <div className="text-2xl">-&gt;</div>
                          <div>
                            <div className="text-sm text-gray-500">Novo</div>
                            <div className="text-lg font-bold text-blue-700">
                              R$ {formatCurrency(hist.preco_custo_novo)}
                            </div>
                          </div>
                        </div>
                        {hist.variacao_custo_percentual !== null &&
                          hist.variacao_custo_percentual !== 0 && (
                            <div
                              className={`mt-2 text-sm font-semibold text-center ${
                                hist.variacao_custo_percentual > 0
                                  ? "text-red-600"
                                  : "text-green-600"
                              }`}
                            >
                              {hist.variacao_custo_percentual > 0 ? "+" : "-"}{" "}
                              {Math.abs(hist.variacao_custo_percentual).toFixed(2)}%
                            </div>
                          )}
                      </div>
                    )}

                    {hist.preco_venda_anterior !== null && hist.preco_venda_novo !== null && (
                      <div className="bg-green-50 rounded-lg p-3">
                        <div className="text-xs text-gray-600 font-semibold mb-2">
                          PRECO DE VENDA
                        </div>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm text-gray-500">Anterior</div>
                            <div className="text-lg font-bold">
                              R$ {formatCurrency(hist.preco_venda_anterior)}
                            </div>
                          </div>
                          <div className="text-2xl">-&gt;</div>
                          <div>
                            <div className="text-sm text-gray-500">Novo</div>
                            <div className="text-lg font-bold text-green-700">
                              R$ {formatCurrency(hist.preco_venda_novo)}
                            </div>
                          </div>
                        </div>
                        {hist.variacao_venda_percentual !== null &&
                          hist.variacao_venda_percentual !== 0 && (
                            <div
                              className={`mt-2 text-sm font-semibold text-center ${
                                hist.variacao_venda_percentual > 0
                                  ? "text-green-600"
                                  : "text-red-600"
                              }`}
                            >
                              {hist.variacao_venda_percentual > 0 ? "+" : "-"}{" "}
                              {Math.abs(hist.variacao_venda_percentual).toFixed(2)}%
                            </div>
                          )}
                      </div>
                    )}
                  </div>

                  {hist.margem_anterior !== null && hist.margem_nova !== null && (
                    <div className="mt-3 bg-purple-50 rounded-lg p-3">
                      <div className="text-xs text-gray-600 font-semibold mb-2">
                        MARGEM DE LUCRO
                      </div>
                      <div className="flex items-center justify-around">
                        <div className="text-center">
                          <div className="text-sm text-gray-500">Anterior</div>
                          <div className="text-xl font-bold">
                            {hist.margem_anterior.toFixed(1)}%
                          </div>
                        </div>
                        <div className="text-2xl">-&gt;</div>
                        <div className="text-center">
                          <div className="text-sm text-gray-500">Nova</div>
                          <div className="text-xl font-bold text-purple-700">
                            {hist.margem_nova.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {hist.observacoes && (
                    <div className="mt-3 text-sm text-gray-600 italic bg-gray-50 rounded p-2">
                      {hist.observacoes}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t p-6 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

EntradaXmlHistoricoPrecosModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  carregandoHistorico: PropTypes.bool.isRequired,
  historicoPrecos: PropTypes.arrayOf(PropTypes.object).isRequired,
  produtoHistorico: PropTypes.shape({
    nome: PropTypes.string,
  }),
  onClose: PropTypes.func.isRequired,
};

EntradaXmlHistoricoPrecosModal.defaultProps = {
  produtoHistorico: null,
};

export default EntradaXmlHistoricoPrecosModal;
