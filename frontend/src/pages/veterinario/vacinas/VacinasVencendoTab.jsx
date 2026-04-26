import { CheckCircle } from "lucide-react";
import { badgeProxDose, formatData } from "./vacinaUtils";

export default function VacinasVencendoTab({ vacinasVencendo }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {vacinasVencendo.length === 0 ? (
        <div className="p-10 text-center">
          <CheckCircle size={36} className="mx-auto text-green-300 mb-3" />
          <p className="text-gray-400 text-sm">Nenhuma vacina a vencer nos próximos 30 dias. Ótimo!</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Pet</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Vacina</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Próxima dose</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {vacinasVencendo.map((vacina) => {
              const badge = badgeProxDose(vacina.proxima_dose);

              return (
                <tr key={vacina.id} className="hover:bg-orange-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{vacina.pet_nome ?? "-"}</td>
                  <td className="px-4 py-3 text-gray-700">{vacina.nome_vacina}</td>
                  <td className="px-4 py-3 text-gray-600">{formatData(vacina.proxima_dose)}</td>
                  <td className="px-4 py-3">
                    {badge && (
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
                        {badge.label}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
