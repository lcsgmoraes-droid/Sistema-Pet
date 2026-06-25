import { formatarMoeda } from "../../../api/produtos";
import { TabContent } from "../../../components/ResponsiveTabs";

export default function ProdutosFormVariacoesTab({
  loadingVariacoes,
  onEditarVariacao,
  onNovaVariacao,
  variacoes,
}) {
  return (
    <TabContent>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Variações do Produto</h2>
            <p className="text-sm text-gray-500 mt-1">
              Gerencie as variações deste produto (cor, tamanho, etc.)
            </p>
          </div>

          <button
            onClick={onNovaVariacao}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
          >
            <span>➕</span> Nova Variação
          </button>
        </div>

        {loadingVariacoes ? (
          <div className="text-center py-12 text-gray-500">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4">Carregando variações...</p>
          </div>
        ) : variacoes.length === 0 ? (
          <div className="text-center py-12 text-gray-500 border-2 border-dashed border-gray-300 rounded-lg">
            <p className="text-lg mb-2">🔹 Nenhuma variação cadastrada</p>
            <p className="text-sm mb-4">Este produto não possui variações ainda</p>
            <button onClick={onNovaVariacao} className="text-blue-600 hover:underline font-medium">
              Criar primeira variação →
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Tabela de Variações */}
            <div className="overflow-x-auto border border-gray-200 rounded-lg">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Variação
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Código
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Preço
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Estoque
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Ações
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {variacoes.map((variacao) => (
                    <tr key={variacao.id} className="hover:bg-gray-50 transition">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900">{variacao.nome}</span>
                        </div>
                        {variacao.variation_signature && (
                          <div className="text-xs text-gray-500 mt-1">
                            {variacao.variation_signature.split("|").join(" • ")}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-sm font-mono text-gray-600">{variacao.codigo}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-sm font-semibold text-gray-900">
                          {formatarMoeda(variacao.preco_venda)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            (variacao.estoque_atual || 0) > 0
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {variacao.estoque_atual || 0}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            variacao.ativo
                              ? "bg-green-100 text-green-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {variacao.ativo ? "Ativo" : "Inativo"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex justify-center gap-2">
                          <button
                            onClick={() => onEditarVariacao(variacao.id)}
                            className="text-blue-600 hover:text-blue-900 transition"
                            title="Editar variação"
                          >
                            ✏️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Informações */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <strong>💡 Dica:</strong> Cada variação funciona como um produto independente com
                preço e estoque próprios. O produto pai serve apenas como agrupador e não pode ser
                vendido diretamente.
              </p>
            </div>
          </div>
        )}
      </div>
    </TabContent>
  );
}
