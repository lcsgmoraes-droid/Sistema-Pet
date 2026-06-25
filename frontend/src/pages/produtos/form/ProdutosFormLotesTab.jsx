import { formatarData, formatarMoeda } from "../../../api/produtos";
import { TabContent } from "../../../components/ResponsiveTabs";

export default function ProdutosFormLotesTab({ handleMovimentoEstoque, lotes }) {
  return (
    <TabContent>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Controle de Lotes (FIFO)</h2>

          <div className="flex gap-2">
            <button
              onClick={() => handleMovimentoEstoque("entrada")}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
            >
              ➕ Entrada
            </button>
            <button
              onClick={() => handleMovimentoEstoque("saida")}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
            >
              ➖ Saída
            </button>
          </div>
        </div>

        {lotes.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg mb-2">📦 Nenhum lote cadastrado</p>
            <p className="text-sm">Registre uma entrada de estoque para criar o primeiro lote</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Lote
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Qtd Atual
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Qtd Inicial
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Custo Unit.
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Validade
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Data Entrada
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {lotes.map((lote) => (
                  <tr key={lote.id} className={lote.quantidade_atual === 0 ? "opacity-50" : ""}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {lote.numero_lote}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center font-semibold">
                      {lote.quantidade_atual}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-center">
                      {lote.quantidade_inicial}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">
                      {formatarMoeda(lote.preco_custo)}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">
                      {lote.data_validade ? formatarData(lote.data_validade) : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-center">
                      {formatarData(lote.data_entrada)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800">
            <strong>FIFO:</strong> As saídas de estoque consomem automaticamente os lotes mais
            antigos primeiro (First In, First Out).
          </p>
        </div>
      </div>
    </TabContent>
  );
}
