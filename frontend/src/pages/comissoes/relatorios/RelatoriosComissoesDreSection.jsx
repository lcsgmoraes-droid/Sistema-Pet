import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function RelatoriosComissoesDreSection({
  dadosDRE,
  formatarMoeda,
  formatarPercentual,
}) {
  if (!dadosDRE) return <div className="text-center py-12">Carregando...</div>;

  return (
    <div className="space-y-6">
      {/* Aviso Informativo */}
      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-blue-800">
              <strong className="font-semibold">Regime de competência:</strong> as comissões são
              reconhecidas como despesa na data da venda, independentemente do pagamento. Inclui
              comissões pendentes e pagas.
            </p>
          </div>
        </div>
      </div>

      {/* Resumo Anual */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-sm text-blue-600 font-medium">Receita Bruta (Ano)</div>
          <div className="text-2xl font-bold text-blue-800">
            {formatarMoeda(dadosDRE.total_ano.receita_bruta)}
          </div>
        </div>

        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <div className="text-sm text-orange-600 font-medium">Despesa Comissão (Ano)</div>
          <div className="text-2xl font-bold text-orange-800">
            {formatarMoeda(dadosDRE.total_ano.despesa_comissao)}
          </div>
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="text-sm text-green-600 font-medium">Margem Líquida (Ano)</div>
          <div className="text-2xl font-bold text-green-800">
            {formatarMoeda(dadosDRE.total_ano.margem_liquida)}
          </div>
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="text-sm text-purple-600 font-medium">% Comissão sobre Receita</div>
          <div className="text-2xl font-bold text-purple-800">
            {formatarPercentual(dadosDRE.total_ano.percentual_comissao)}
          </div>
        </div>
      </div>

      {/* Gráfico de Linha - Evolução Mensal */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-4">Evolução Mensal - DRE</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={dadosDRE.dados_mensais}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="mes_nome" />
            <YAxis />
            <Tooltip formatter={(value) => formatarMoeda(value)} />
            <Legend />
            <Line
              type="monotone"
              dataKey="receita_bruta"
              stroke="#8884d8"
              name="Receita Bruta"
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="despesa_comissao"
              stroke="#ff7c7c"
              name="Despesa Comissão"
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="margem_liquida"
              stroke="#82ca9d"
              name="Margem Líquida"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Tabela Mensal */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Mês
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Receita Bruta
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Custo
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Comissão
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Margem Bruta
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                Margem Líquida
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                % Comissão
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {dadosDRE.dados_mensais.map((mes) => (
              <tr key={mes.mes}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {mes.mes_nome}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-blue-600 font-medium">
                  {formatarMoeda(mes.receita_bruta)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                  {formatarMoeda(mes.custo_total)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-orange-600 font-medium">
                  {formatarMoeda(mes.despesa_comissao)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-700">
                  {formatarMoeda(mes.margem_bruta)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-green-600">
                  {formatarMoeda(mes.margem_liquida)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-purple-600">
                  {formatarPercentual(mes.percentual_comissao_sobre_receita)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
