import { Activity, Clock } from "lucide-react";
import {
  STATUS_BADGE,
  STATUS_COLOR,
  STATUS_LABEL,
  TIPO_BADGE,
  TIPO_LABEL,
  isoDate,
  normalizarTipoAgendamento,
} from "./agendaUtils";

export default function AgendaDiasView({
  modo,
  diasVisiveis,
  agsDia,
  abrindoAgendamentoId,
  onAbrirNovo,
  onGerenciarAgendamento,
}) {
  return (
    <div className={`grid gap-4 ${modo === "semana" ? "grid-cols-7" : "grid-cols-1"}`}>
      {diasVisiveis.map((dia) => {
        const ags = agsDia(dia);
        const ehHoje = isoDate(dia) === isoDate(new Date());

        return (
          <div
            key={isoDate(dia)}
            onClick={() => onAbrirNovo(dia)}
            className={`cursor-pointer overflow-hidden rounded-xl border transition-colors hover:border-blue-300 ${
              ehHoje ? "border-blue-300" : "border-gray-200"
            } bg-white`}
          >
            <div
              className={`border-b px-3 py-2 text-xs font-semibold ${
                ehHoje ? "border-blue-600 bg-blue-600 text-white" : "border-gray-200 bg-gray-50 text-gray-600"
              }`}
            >
              <span className="capitalize">
                {dia.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit" })}
              </span>
              {ags.length > 0 && (
                <span
                  className={`ml-1 rounded-full px-1.5 py-0.5 text-xs ${
                    ehHoje ? "bg-white text-blue-700" : "bg-blue-100 text-blue-700"
                  }`}
                >
                  {ags.length}
                </span>
              )}
            </div>

            <div className="min-h-[80px] divide-y divide-gray-50">
              {ags.length === 0 && (
                <div className="px-3 py-4 text-center">
                  <p className="text-xs text-gray-300">Livre</p>
                  <p className="mt-1 text-[11px] text-blue-500">Clique para agendar</p>
                </div>
              )}
              {ags.map((ag) => {
                const tipoAgendamento = normalizarTipoAgendamento(ag.tipo);

                return (
                  <div
                    key={ag.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      onGerenciarAgendamento(ag);
                    }}
                    className={`cursor-pointer border-l-4 px-3 py-2 transition-opacity hover:opacity-80 ${
                      STATUS_COLOR[ag.status] ?? "border-l-gray-200 bg-white"
                    }`}
                  >
                    <div className="mb-0.5 flex items-center gap-1">
                      <Clock size={10} className="text-gray-400" />
                      <span className="text-xs text-gray-500">
                        {String(ag.data_hora || "").slice(11, 16)}
                      </span>
                      <span
                        className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                          TIPO_BADGE[tipoAgendamento] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {TIPO_LABEL[tipoAgendamento] ?? "Consulta"}
                      </span>
                      {ag.is_emergencia && <Activity size={10} className="ml-auto text-red-500" />}
                    </div>
                    <p className="truncate text-xs font-medium text-gray-700">
                      {ag.pet_nome ?? `Pet #${String(ag.pet_id ?? "").slice(0, 6)}`}
                    </p>
                    <p className="truncate text-[11px] text-gray-500">
                      {[ag.veterinario_nome, ag.consultorio_nome].filter(Boolean).join(" • ") ||
                        "Sem profissional/sala"}
                    </p>
                    <p className="truncate text-xs text-gray-400">{ag.motivo ?? "-"}</p>
                    <span
                      className={`mt-1 inline-flex rounded-full px-1.5 py-0.5 text-xs font-medium ${
                        STATUS_BADGE[ag.status] ?? "bg-gray-100"
                      }`}
                    >
                      {STATUS_LABEL[ag.status] ?? ag.status}
                    </span>
                    {abrindoAgendamentoId === ag.id && (
                      <span className="ml-2 text-[11px] font-medium text-blue-600">Abrindo...</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
