export default function CampanhasRelatoriosTab({
  relDataInicio,
  setRelDataInicio,
  relDataFim,
  setRelDataFim,
  relTipo,
  setRelTipo,
  relatorio,
  loadingRelatorio,
  formatBRL,
  formatarData,
}) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border shadow-sm p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label
            htmlFor="rel-data-inicio"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Data inicio
          </label>
          <input
            id="rel-data-inicio"
            type="date"
            value={relDataInicio}
            onChange={(e) => setRelDataInicio(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label
            htmlFor="rel-data-fim"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Data fim
          </label>
          <input
            id="rel-data-fim"
            type="date"
            value={relDataFim}
            onChange={(e) => setRelDataFim(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label
            htmlFor="rel-tipo"
            className="block text-xs font-medium text-gray-600 mb-1"
          >
            Tipo
          </label>
          <select
            id="rel-tipo"
            value={relTipo}
            onChange={(e) => setRelTipo(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm"
          >
            <option value="todos">Todos</option>
            <option value="credito">So creditos</option>
            <option value="resgate">So resgates</option>
          </select>
        </div>
      </div>

      {relatorio && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
            <p className="text-xs text-green-600 font-medium mb-1">
              Total Creditado
            </p>
            <p className="text-xl font-bold text-green-700">
              R$ {formatBRL(relatorio.total_creditado)}
            </p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
            <p className="text-xs text-red-600 font-medium mb-1">
              Total Resgatado
            </p>
            <p className="text-xl font-bold text-red-700">
              R$ {formatBRL(relatorio.total_resgatado)}
            </p>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
            <p className="text-xs text-blue-600 font-medium mb-1">
              Saldo Atual (Passivo)
            </p>
            <p className="text-xl font-bold text-blue-700">
              R$ {formatBRL(relatorio.saldo_total)}
            </p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50">
          <h2 className="font-semibold text-gray-800">
            Historico de Movimentacoes
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Creditos = cashback gerado ao cliente. Resgates = cashback usado
            como pagamento numa venda.
          </p>
        </div>
        {loadingRelatorio ? (
          <div className="p-8 text-center text-gray-400">
            Carregando relatorio...
          </div>
        ) : !relatorio || relatorio.transacoes.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <p className="text-2xl mb-2">-</p>
            <p>Nenhuma movimentacao no periodo.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Data
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Cliente
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Venda
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">
                    Valor
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Descricao
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {relatorio.transacoes.map((transacao) => (
                  <tr key={transacao.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {formatarData(transacao.data)}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {transacao.cliente_nome}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          transacao.tipo === "credito"
                            ? "bg-green-100 text-green-700"
                            : "bg-orange-100 text-orange-700"
                        }`}
                      >
                        {transacao.tipo === "credito"
                          ? "Credito"
                          : "Resgate"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {transacao.venda_id || "-"}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">
                      R$ {formatBRL(transacao.valor)}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs max-w-[200px] truncate">
                      {transacao.descricao || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
