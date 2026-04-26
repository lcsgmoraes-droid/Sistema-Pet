import { AlertCircle, Calendar } from "lucide-react";

import { STATUS_AGENDAMENTO_COLOR, STATUS_AGENDAMENTO_LABEL } from "./dashboardConfig";

export default function AgendaHojeCard({ agendamentos, onAbrirAgenda, onAbrirAgendamento }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <h2 className="font-semibold text-gray-700 flex items-center gap-2">
          <Calendar size={16} />
          Agenda de hoje
        </h2>
        <button onClick={onAbrirAgenda} className="text-sm text-blue-600 hover:underline">
          Ver completa →
        </button>
      </div>

      {agendamentos.length === 0 ? (
        <div className="p-8 text-center text-gray-400 text-sm">
          Nenhum agendamento para hoje.
        </div>
      ) : (
        <div className="divide-y divide-gray-50">
          {agendamentos.slice(0, 10).map((agendamento) => (
            <button
              key={agendamento.id}
              type="button"
              className="flex w-full items-center gap-4 px-5 py-3 text-left hover:bg-gray-50 transition-colors"
              onClick={() => onAbrirAgendamento(agendamento)}
            >
              <span className="text-sm font-mono text-gray-500 w-12">
                {agendamento.data_hora?.slice(11, 16)}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">
                  {agendamento.pet_nome ?? `Pet #${String(agendamento.pet_id ?? "").slice(0, 6)}`}
                </p>
                <p className="text-xs text-gray-400 truncate">{agendamento.motivo ?? "—"}</p>
              </div>
              {agendamento.emergencia && (
                <span className="flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                  <AlertCircle size={10} />
                  Emergência
                </span>
              )}
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  STATUS_AGENDAMENTO_COLOR[agendamento.status] ?? "bg-gray-100 text-gray-600"
                }`}
              >
                {STATUS_AGENDAMENTO_LABEL[agendamento.status] ?? agendamento.status}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
