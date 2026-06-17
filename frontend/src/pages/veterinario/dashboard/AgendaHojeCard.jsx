import { AlertCircle, Calendar } from "lucide-react";
import PetIdentity from "../../../components/ui/PetIdentity";

import { STATUS_AGENDAMENTO_COLOR, STATUS_AGENDAMENTO_LABEL } from "./dashboardConfig";

export default function AgendaHojeCard({ agendamentos, onAbrirAgenda, onAbrirAgendamento }) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="flex flex-col gap-2 border-b border-gray-100 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <h2 className="flex items-center gap-2 font-semibold text-gray-700">
          <Calendar size={16} />
          Agenda de hoje
        </h2>
        <button
          onClick={onAbrirAgenda}
          className="self-start text-sm text-blue-600 hover:underline sm:self-auto"
        >
          Ver completa →
        </button>
      </div>

      {agendamentos.length === 0 ? (
        <div className="p-8 text-center text-gray-400 text-sm">Nenhum agendamento para hoje.</div>
      ) : (
        <div className="divide-y divide-gray-50">
          {agendamentos.slice(0, 10).map((agendamento) => (
            <button
              key={agendamento.id}
              type="button"
              className="flex w-full flex-col gap-2 px-4 py-3 text-left transition-colors hover:bg-gray-50 sm:flex-row sm:items-center sm:gap-4 sm:px-5"
              onClick={() => onAbrirAgendamento(agendamento)}
            >
              <span className="w-full text-sm font-mono text-gray-500 sm:w-12">
                {agendamento.data_hora?.slice(11, 16)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-800 truncate">
                  <PetIdentity
                    copyable={false}
                    fallback={`Pet #${String(agendamento.pet_id ?? "").slice(0, 6) || "-"}`}
                    layout="inline"
                    nameClassName="font-medium text-gray-800"
                    record={agendamento}
                  />
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
