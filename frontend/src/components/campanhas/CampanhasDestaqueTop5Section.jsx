import { formatBRL } from "../../utils/formatters";

const TOP_LISTAS = [
  ["maior_gasto", "top5_maior_gasto", "Top 5 - Maior Gasto"],
  ["mais_compras", "top5_mais_compras", "Top 5 - Mais Compras"],
];

export default function CampanhasDestaqueTop5Section({ destaque }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {TOP_LISTAS.map(([categoria, chave, titulo]) => (
        <div
          key={categoria}
          className="bg-white rounded-xl border shadow-sm overflow-hidden"
        >
          <div className="px-4 py-3 border-b bg-gray-50">
            <p className="font-semibold text-gray-800 text-sm">{titulo}</p>
          </div>
          <ul className="divide-y">
            {(destaque[chave] || []).map((cliente, index) => (
              <li key={index} className="px-4 py-3 flex items-center gap-3">
                <span className="text-lg font-bold text-gray-300 w-6 text-center">
                  {index + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{cliente.nome}</p>
                  <p className="text-xs text-gray-500">
                    {categoria === "maior_gasto"
                      ? `R$ ${formatBRL(cliente.total_spent)}`
                      : `${cliente.total_purchases} compra(s)`}
                  </p>
                </div>
                {destaque.vencedores[categoria]?.customer_id ===
                  cliente.customer_id && (
                  <span className="text-yellow-500 text-lg">{"\u{1F3C6}"}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
