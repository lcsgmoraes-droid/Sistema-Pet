import { AlertCircle } from "lucide-react";

const DashboardRacoesComparacaoMarcas = ({ comparacaoMarcas, loadingAnalise }) => {
  if (loadingAnalise) {
    return <div className="text-center py-8 text-gray-500">Carregando comparação...</div>;
  }

  if (comparacaoMarcas.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
        Nenhum dado encontrado. Aplique filtros e clique em "Aplicar Filtros"
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
              Marca
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">
              Produtos
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">
              Preço/Kg Médio
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">
              Margem Média
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
              Mais Barato
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
              Mais Caro
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {comparacaoMarcas.map((marca) => (
            <tr key={marca.marca_id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm font-semibold text-gray-900">{marca.marca_nome}</td>
              <td className="px-4 py-3 text-sm text-center text-gray-600">
                {marca.total_produtos}
              </td>
              <td className="px-4 py-3 text-sm text-center font-semibold text-gray-900">
                R$ {marca.preco_medio_kg.toFixed(2)}
              </td>
              <td className="px-4 py-3 text-sm text-center">
                <span
                  className={`font-semibold ${
                    marca.margem_media >= 30
                      ? "text-green-600"
                      : marca.margem_media >= 20
                        ? "text-yellow-600"
                        : "text-red-600"
                  }`}
                >
                  {marca.margem_media}%
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-gray-700">
                {marca.produto_mais_barato?.nome?.substring(0, 30) || "-"}
                {marca.produto_mais_barato?.preco_kg && (
                  <div className="text-green-600 font-semibold">
                    R$ {marca.produto_mais_barato.preco_kg}/kg
                  </div>
                )}
              </td>
              <td className="px-4 py-3 text-xs text-gray-700">
                {marca.produto_mais_caro?.nome?.substring(0, 30) || "-"}
                {marca.produto_mais_caro?.preco_kg && (
                  <div className="text-red-600 font-semibold">
                    R$ {marca.produto_mais_caro.preco_kg}/kg
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DashboardRacoesComparacaoMarcas;
