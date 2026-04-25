import {
  STATUS_COLOR,
  TIPO_BADGE,
  TIPO_LABEL,
  isoDate,
  normalizarTipoAgendamento,
} from "./agendaUtils";

export default function AgendaMesView({
  diasMes,
  dataRef,
  agsDia,
  abrindoAgendamentoId,
  onAbrirNovo,
  onGerenciarAgendamento,
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <div className="grid grid-cols-7 border-b border-gray-200 bg-gray-50">
        {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"].map((nomeDia) => (
          <div key={nomeDia} className="px-3 py-2 text-center text-xs font-semibold text-gray-600">
            {nomeDia}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7">
        {diasMes.map((dia) => {
          const ags = agsDia(dia);
          const ehHoje = isoDate(dia) === isoDate(new Date());
          const foraDoMes = dia.getMonth() !== dataRef.getMonth();

          return (
            <div
              key={isoDate(dia)}
              onClick={() => onAbrirNovo(dia)}
              className={`min-h-[110px] cursor-pointer border-b border-r border-gray-100 p-2 transition-colors hover:bg-blue-50 ${
                foraDoMes ? "bg-gray-50" : "bg-white"
              }`}
            >
              <div className="mb-1 flex items-center justify-between">
                <span
                  className={`text-xs font-medium ${
                    ehHoje ? "text-blue-700" : foraDoMes ? "text-gray-400" : "text-gray-700"
                  }`}
                >
                  {String(dia.getDate()).padStart(2, "0")}
                </span>
                {ags.length > 0 && (
                  <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-700">
                    {ags.length}
                  </span>
                )}
              </div>

              <div className="space-y-1">
                {ags.slice(0, 2).map((ag) => {
                  const tipoAgendamento = normalizarTipoAgendamento(ag.tipo);

                  return (
                    <button
                      key={ag.id}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onGerenciarAgendamento(ag);
                      }}
                      className={`w-full rounded border-l-2 px-1.5 py-1 text-left text-[11px] ${
                        STATUS_COLOR[ag.status] ?? "border-l-gray-200 bg-white"
                      }`}
                    >
                      <p className="truncate">
                        {String(ag.data_hora || "").slice(11, 16)} -{" "}
                        {ag.pet_nome ?? `Pet #${String(ag.pet_id ?? "").slice(0, 6)}`}
                      </p>
                      <p className="mt-0.5 truncate text-[10px] text-gray-500">
                        {[ag.veterinario_nome, ag.consultorio_nome].filter(Boolean).join(" • ") ||
                          "Sem profissional/sala"}
                      </p>
                      <div className="mt-1 flex items-center gap-1">
                        <span
                          className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                            TIPO_BADGE[tipoAgendamento] ?? "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {TIPO_LABEL[tipoAgendamento] ?? "Consulta"}
                        </span>
                        {abrindoAgendamentoId === ag.id && (
                          <span className="text-[10px] text-blue-600">Abrindo...</span>
                        )}
                      </div>
                    </button>
                  );
                })}
                {ags.length > 2 && <p className="text-[10px] text-gray-400">+{ags.length - 2} mais</p>}
                {ags.length === 0 && <p className="pt-1 text-[10px] text-gray-300">Clique para agendar</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
