import { AlertCircle, FileText } from "lucide-react";

import {
  formatDataConsulta,
  formatHoraConsulta,
  STATUS_COLOR,
  STATUS_LABEL,
} from "./consultasUtils";

export default function ConsultasTableCard({ carregando, consultas, erro, onAbrirConsulta }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {carregando ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      ) : erro ? (
        <div className="flex items-center gap-2 text-red-600 p-6">
          <AlertCircle size={18} />
          <span className="text-sm">{erro}</span>
        </div>
      ) : consultas.length === 0 ? (
        <div className="p-12 text-center">
          <FileText size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 text-sm">Nenhuma consulta encontrada.</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Codigo</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Data</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Pet</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Veterinario</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Motivo</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Diagnostico</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {consultas.map((consulta) => (
              <ConsultaTableRow
                key={consulta.id}
                consulta={consulta}
                onAbrirConsulta={onAbrirConsulta}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ConsultaTableRow({ consulta, onAbrirConsulta }) {
  return (
    <tr
      className="hover:bg-blue-50 transition-colors cursor-pointer"
      onClick={() => onAbrirConsulta(consulta.id)}
    >
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="font-semibold text-gray-800">#{consulta.id}</div>
        <div className="text-[11px] text-gray-400">Consulta</div>
      </td>
      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
        {formatDataConsulta(consulta.created_at)}
        <span className="text-xs ml-1 text-gray-400">{formatHoraConsulta(consulta.created_at)}</span>
      </td>
      <td className="px-4 py-3 font-medium text-gray-800">{consulta.pet_nome ?? "-"}</td>
      <td className="px-4 py-3 text-gray-600">{consulta.veterinario_nome ?? "-"}</td>
      <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{consulta.motivo_consulta ?? "-"}</td>
      <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{consulta.diagnostico ?? "-"}</td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[consulta.status] ?? "bg-gray-100"}`}>
          {STATUS_LABEL[consulta.status] ?? consulta.status}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={(event) => {
            event.stopPropagation();
            onAbrirConsulta(consulta.id);
          }}
          className="text-blue-500 hover:text-blue-700 text-xs underline"
        >
          Abrir
        </button>
      </td>
    </tr>
  );
}
