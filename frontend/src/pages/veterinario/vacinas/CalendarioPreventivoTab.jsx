import { CalendarDays, CheckCircle, RefreshCw } from "lucide-react";
import { classeFaseCalendario } from "./vacinaUtils";

export default function CalendarioPreventivoTab({
  calendario,
  especieCalendario,
  carregandoCalendario,
  onChangeEspecie,
  onCarregarCalendario,
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={especieCalendario}
          onChange={(event) => onChangeEspecie(event.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-300"
        >
          <option value="">Todas as espécies</option>
          <option value="cão">Cão</option>
          <option value="gato">Gato</option>
          <option value="coelho">Coelho</option>
        </select>
        <button
          type="button"
          onClick={onCarregarCalendario}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-60"
          disabled={carregandoCalendario}
        >
          <RefreshCw size={14} className={carregandoCalendario ? "animate-spin" : ""} />
          {carregandoCalendario ? "Carregando..." : "Carregar calendário"}
        </button>
      </div>

      {calendario.length === 0 && !carregandoCalendario && (
        <div className="bg-white border border-gray-200 rounded-xl p-10 text-center">
          <CalendarDays size={36} className="mx-auto text-orange-200 mb-3" />
          <p className="text-gray-400 text-sm">
            Clique em "Carregar calendário" para ver os protocolos preventivos por espécie.
          </p>
        </div>
      )}

      {calendario.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Vacina / Protocolo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Espécie</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fase</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Idade mín.</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Reforço anual</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Observações</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fonte</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {calendario.map((item) => (
                <tr
                  key={`${item.vacina || "vacina"}-${item.especie || "especie"}-${item.fase || "fase"}-${item.idade_semanas_min || "sem-idade"}`}
                  className="hover:bg-orange-50 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-gray-800">{item.vacina}</td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{item.especie ?? "-"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${classeFaseCalendario(item.fase)}`}>
                      {item.fase ?? "-"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {item.idade_semanas_min == null ? "-" : `${item.idade_semanas_min} sem.`}
                  </td>
                  <td className="px-4 py-3">
                    {item.reforco_anual ? (
                      <CheckCircle size={15} className="text-green-500" />
                    ) : (
                      <span className="text-gray-300">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{item.observacoes ?? "-"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        item.fonte === "personalizado"
                          ? "bg-violet-100 text-violet-700"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {item.fonte === "personalizado" ? "Personalizado" : "Padrão"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
