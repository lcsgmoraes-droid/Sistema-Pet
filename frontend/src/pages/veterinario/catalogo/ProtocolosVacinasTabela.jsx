import { Loader2 } from "lucide-react";

import { LinhaAcoes } from "./shared";

export default function ProtocolosVacinasTabela({
  carregando,
  lista,
  removendoId,
  onEditar,
  onExcluir,
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      {carregando ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
        </div>
      ) : lista.length === 0 ? (
        <div className="p-8 text-center text-sm text-gray-400">Nenhum protocolo cadastrado.</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-gray-100 bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Protocolo</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Especie</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Inicio</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Serie</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Reforco</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Acoes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {lista.map((item) => (
              <ProtocoloVacinaLinha
                key={item.id}
                item={item}
                removendo={removendoId === item.id}
                onEditar={() => onEditar(item)}
                onExcluir={() => onExcluir(item)}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ProtocoloVacinaLinha({ item, removendo, onEditar, onExcluir }) {
  return (
    <tr className="hover:bg-teal-50">
      <td className="px-4 py-3">
        <p className="font-medium text-gray-800">{item.nome}</p>
        <p className="text-xs text-gray-500">{item.observacoes || "-"}</p>
      </td>
      <td className="px-4 py-3 text-gray-600">{item.especie || "-"}</td>
      <td className="px-4 py-3 text-gray-600">
        {item.dose_inicial_semanas ? `${item.dose_inicial_semanas} semana(s)` : "-"}
      </td>
      <td className="px-4 py-3 text-gray-600">
        {item.numero_doses_serie || 1}
        {item.intervalo_doses_dias ? ` x ${item.intervalo_doses_dias} dias` : ""}
      </td>
      <td className="px-4 py-3">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            item.reforco_anual ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-500"
          }`}
        >
          {item.reforco_anual ? "Anual" : "Nao anual"}
        </span>
      </td>
      <td className="px-4 py-3">
        <LinhaAcoes onEditar={onEditar} onExcluir={onExcluir} removendo={removendo} />
      </td>
    </tr>
  );
}
