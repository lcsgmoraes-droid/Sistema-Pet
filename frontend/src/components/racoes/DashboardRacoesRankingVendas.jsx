import React from 'react';
import { AlertCircle } from 'lucide-react';

const DashboardRacoesRankingVendas = ({ rankingVendas, loadingAnalise }) => {
  if (loadingAnalise) {
    return <div className="text-center py-8 text-gray-500">Carregando ranking...</div>;
  }

  if (rankingVendas.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
        Selecione um período nos filtros e clique em "Aplicar Filtros"
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">#</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Produto</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Marca</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Qtd Vendida</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Faturamento</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Margem Média</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">Preço Médio</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {rankingVendas.map((prod, idx) => (
            <tr key={prod.produto_id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm text-gray-600">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                    idx === 0
                      ? 'bg-yellow-100 text-yellow-700'
                      : idx === 1
                        ? 'bg-gray-200 text-gray-700'
                        : idx === 2
                          ? 'bg-orange-100 text-orange-700'
                          : 'bg-gray-50 text-gray-600'
                  }`}
                >
                  {idx + 1}
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-gray-900">{prod.nome}</td>
              <td className="px-4 py-3 text-sm text-gray-600">{prod.marca}</td>
              <td className="px-4 py-3 text-sm text-center font-semibold text-gray-900">{prod.quantidade_vendida}</td>
              <td className="px-4 py-3 text-sm text-center font-semibold text-green-600">
                R$ {prod.faturamento.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </td>
              <td className="px-4 py-3 text-sm text-center">
                <span
                  className={`font-semibold ${
                    prod.margem_media >= 30
                      ? 'text-green-600'
                      : prod.margem_media >= 20
                        ? 'text-yellow-600'
                        : 'text-red-600'
                  }`}
                >
                  {prod.margem_media}%
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-center text-gray-900">
                R$ {prod.preco_medio_venda.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DashboardRacoesRankingVendas;
