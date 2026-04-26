import { Loader2 } from "lucide-react";
import { formatLista, LinhaAcoes } from "./shared";

export default function MedicamentosTabela({ buscando, lista, onEditar, onExcluir, removendoId }) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      {buscando ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
        </div>
      ) : lista.length === 0 ? (
        <div className="p-8 text-center text-sm text-gray-400">Nenhum medicamento cadastrado.</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-gray-100 bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Medicamento</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Especies</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Posologia base</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Dose</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Acoes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {lista.map((item) => (
              <LinhaMedicamento
                key={item.id}
                item={item}
                onEditar={onEditar}
                onExcluir={onExcluir}
                removendo={removendoId === item.id}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function LinhaMedicamento({ item, onEditar, onExcluir, removendo }) {
  return (
    <tr className="hover:bg-teal-50">
      <td className="px-4 py-3">
        <p className="font-medium text-gray-800">{item.nome}</p>
        <p className="text-xs text-gray-500">{item.nome_comercial || item.principio_ativo || item.fabricante || "-"}</p>
      </td>
      <td className="px-4 py-3 text-gray-600">{formatLista(item.especies_indicadas)}</td>
      <td className="px-4 py-3 text-gray-600">{item.posologia_referencia || "-"}</td>
      <td className="px-4 py-3 text-gray-600">
        {item.dose_min_mgkg || item.dose_max_mgkg
          ? `${item.dose_min_mgkg ?? "-"} a ${item.dose_max_mgkg ?? "-"} mg/kg`
          : "-"}
      </td>
      <td className="px-4 py-3">
        <LinhaAcoes onEditar={() => onEditar(item)} onExcluir={() => onExcluir(item)} removendo={removendo} />
      </td>
    </tr>
  );
}
