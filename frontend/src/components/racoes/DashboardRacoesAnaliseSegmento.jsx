import { AlertCircle } from "lucide-react";

const DashboardRacoesAnaliseSegmento = ({
  analiseSegmento,
  loadingAnalise,
  onTipoSegmentoChange,
  tipoSegmento,
}) => {
  if (loadingAnalise) {
    return <div className="text-center py-8 text-gray-500">Carregando análise...</div>;
  }

  if (analiseSegmento.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
        Nenhum dado encontrado. Aplique filtros e clique em "Aplicar Filtros"
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <label className="text-sm font-medium text-gray-700">Analisar por:</label>
        <select
          value={tipoSegmento}
          onChange={(event) => onTipoSegmentoChange(event.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
        >
          <option value="porte">Porte</option>
          <option value="fase">Fase</option>
          <option value="sabor">Sabor</option>
          <option value="linha">Linha</option>
          <option value="especie">Espécie</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                Segmento
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">
                Produtos
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">
                Margem Média
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">
                Margem Min/Max
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">
                Preço/Kg Médio
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase">
                Faturamento
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {analiseSegmento.map((seg, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-semibold text-gray-900">{seg.segmento}</td>
                <td className="px-4 py-3 text-sm text-center text-gray-600">
                  {seg.total_produtos}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  <span
                    className={`font-semibold ${
                      seg.margem_media >= 30
                        ? "text-green-600"
                        : seg.margem_media >= 20
                          ? "text-yellow-600"
                          : "text-red-600"
                    }`}
                  >
                    {seg.margem_media}%
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-600">
                  {seg.margem_minima}% - {seg.margem_maxima}%
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-600">
                  R$ {seg.preco_medio_kg.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-center font-semibold text-gray-900">
                  R$ {seg.faturamento.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DashboardRacoesAnaliseSegmento;
