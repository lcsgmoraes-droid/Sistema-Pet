import { X } from "lucide-react";

export default function PDVComissaoCard({
  buscaFuncionario,
  funcionarioComissao,
  funcionariosSugeridos,
  modoVisualizacao,
  onBuscaFuncionarioChange,
  onBuscaFuncionarioFocus,
  onRemoverFuncionario,
  onSelecionarFuncionario,
  onToggleVendaComissionada,
  vendaComissionada,
}) {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Comissão</h2>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={vendaComissionada}
            onChange={(e) => onToggleVendaComissionada(e.target.checked)}
            disabled={modoVisualizacao}
            className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed"
          />
          <span className="text-sm font-medium text-gray-700">
            Venda comissionada?
          </span>
        </label>
      </div>

      {vendaComissionada && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Funcionário/Veterinário *{" "}
            <span className="text-xs text-gray-500">
              (apenas com comissão configurada)
            </span>
          </label>

          {!funcionarioComissao ? (
            <>
              <input
                type="text"
                value={buscaFuncionario}
                placeholder="Buscar funcionário ou veterinário..."
                disabled={modoVisualizacao}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
                onFocus={onBuscaFuncionarioFocus}
                onChange={(e) => onBuscaFuncionarioChange(e.target.value)}
              />

              {funcionariosSugeridos.length > 0 && (
                <div className="mt-2 border border-gray-200 rounded-lg max-h-48 overflow-y-auto">
                  {funcionariosSugeridos.map((func) => (
                    <button
                      key={func.id}
                      onClick={() => onSelecionarFuncionario(func)}
                      className="w-full px-4 py-2 text-left hover:bg-gray-50 border-b last:border-b-0"
                    >
                      <div className="font-medium">{func.nome}</div>
                      <div className="text-xs text-gray-500 capitalize">
                        {func.cargo}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="p-4 bg-green-50 border-2 border-green-300 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white font-bold">
                  {funcionarioComissao.nome.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="font-semibold text-green-900">
                    {funcionarioComissao.nome}
                  </div>
                  <div className="text-sm text-green-700 capitalize">
                    {funcionarioComissao.cargo}
                  </div>
                </div>
              </div>
              <button
                onClick={onRemoverFuncionario}
                disabled={modoVisualizacao}
                className="p-2 text-green-600 hover:bg-green-100 rounded-lg transition-colors disabled:cursor-not-allowed"
                title="Remover seleção"
              >
                <X size={20} />
              </button>
            </div>
          )}

          <p className="text-xs text-gray-500 mt-2">
            ℹ️ A comissão será calculada automaticamente conforme configurado no
            módulo de comissões
          </p>
        </div>
      )}
    </div>
  );
}
