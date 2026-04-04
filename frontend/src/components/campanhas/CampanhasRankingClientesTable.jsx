export default function CampanhasRankingClientesTable({
  ranking,
  rankLabels,
  formatBRL,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b bg-gray-50">
        <h2 className="font-semibold text-gray-800">Clientes no ranking</h2>
        <p className="text-xs text-gray-500">Periodo: {ranking.periodo}</p>
      </div>
      {ranking.clientes.length === 0 ? (
        <div className="p-8 text-center text-gray-400">
          Nenhum cliente neste nivel.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  #
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Cliente
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Nivel
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Gasto total
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">
                  Compras
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">
                  Meses ativos
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {ranking.clientes.map((cliente, index) => {
                const rankLabel =
                  rankLabels[cliente.rank_level] || rankLabels.bronze;
                return (
                  <tr key={cliente.customer_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-400 font-medium">
                      {index + 1}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">
                        {cliente.nome || `Cliente #${cliente.customer_id}`}
                      </p>
                      {cliente.telefone && (
                        <p className="text-xs text-gray-400">
                          {cliente.telefone}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${rankLabel.color} ${rankLabel.border}`}
                      >
                        {rankLabel.emoji} {rankLabel.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-900">
                      R$ {formatBRL(cliente.total_spent)}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600">
                      {cliente.total_purchases}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-500">
                      {cliente.active_months}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
