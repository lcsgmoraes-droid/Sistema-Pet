import React from "react";

export default function ProdutosConflitoExclusaoModal({
  autoSelecionarConflito,
  bloqueiosExclusao,
  corrigirTextoQuebrado,
  isOpen,
  onCancelarConflito,
  onClose,
  onSelecionarTodasVariacoesDoPai,
  onSelecionarVariacaoConflito,
  onToggleAutoSelecionarConflito,
  onTogglePularConfirmacaoConflito,
  pularConfirmacaoConflito,
  resolvendoConflitoExclusao,
  variacoesSelecionadasConflito,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[85vh] overflow-y-auto">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Produtos com bloqueio para exclusao
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Selecione as variacoes que deseja desativar agora para o sistema tentar
              excluir os produtos pai automaticamente.
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <div className="border border-blue-100 bg-blue-50 rounded-lg p-3">
            <label className="flex items-center gap-2 text-sm text-blue-900">
              <input
                type="checkbox"
                checked={autoSelecionarConflito}
                onChange={(event) => onToggleAutoSelecionarConflito(event.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              Selecionar tudo automaticamente
            </label>
            <label className="flex items-center gap-2 text-sm text-blue-900 mt-2">
              <input
                type="checkbox"
                checked={pularConfirmacaoConflito}
                onChange={(event) => onTogglePularConfirmacaoConflito(event.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              Nao pedir confirmacao de novo nesta sessao
            </label>
          </div>

          {bloqueiosExclusao.map((bloqueio) => {
            const idsDoPai = bloqueio.variacoes.map((item) => item.id);
            const qtdSelecionada = idsDoPai.filter((id) =>
              variacoesSelecionadasConflito.includes(id),
            ).length;

            return (
              <div key={bloqueio.parentId} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {corrigirTextoQuebrado(bloqueio.parentNome)}
                    </h3>
                    <p className="text-xs text-gray-600 mt-1">
                      {corrigirTextoQuebrado(bloqueio.mensagem)}
                    </p>
                  </div>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    {qtdSelecionada}/{bloqueio.variacoes.length} selecionadas
                  </span>
                </div>

                {bloqueio.variacoes.length > 0 ? (
                  <>
                    <label className="inline-flex items-center gap-2 text-sm text-gray-700 mb-3">
                      <input
                        type="checkbox"
                        checked={idsDoPai.length > 0 && qtdSelecionada === idsDoPai.length}
                        onChange={(event) =>
                          onSelecionarTodasVariacoesDoPai(
                            bloqueio.parentId,
                            event.target.checked,
                          )
                        }
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      Selecionar todas variacoes deste produto
                    </label>

                    <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                      {bloqueio.variacoes.map((variacao) => (
                        <label
                          key={variacao.id}
                          className="flex items-center justify-between gap-3 border border-gray-100 rounded px-3 py-2 hover:bg-gray-50"
                        >
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={variacoesSelecionadasConflito.includes(variacao.id)}
                              onChange={(event) =>
                                onSelecionarVariacaoConflito(
                                  variacao.id,
                                  event.target.checked,
                                )
                              }
                              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                            />
                            <span className="text-sm text-gray-800">
                              {corrigirTextoQuebrado(
                                variacao.nome || `Variacao #${variacao.id}`,
                              )}
                            </span>
                          </div>
                          <span className="text-xs text-gray-500 font-mono">
                            {variacao.codigo || variacao.sku || `ID ${variacao.id}`}
                          </span>
                        </label>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                    Nao foi possivel listar variacoes automaticamente para este item.
                    Tente atualizar a tela e repetir.
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={resolvendoConflitoExclusao}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-60"
          >
            Cancelar
          </button>
          <button
            onClick={onCancelarConflito}
            disabled={resolvendoConflitoExclusao}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-60"
          >
            {resolvendoConflitoExclusao
              ? "Aplicando resolucao..."
              : "Resolver rapido e excluir"}
          </button>
        </div>
      </div>
    </div>
  );
}
