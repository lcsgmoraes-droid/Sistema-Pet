export default function HorariosSugeridosAgendaDia({ agendaDiaModal, formNovo, horariosAgendaModal, onChangeCampo }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-800">Agenda do dia</p>
          <p className="text-xs text-gray-500">
            {formNovo.data
              ? new Date(`${formNovo.data}T12:00:00`).toLocaleDateString("pt-BR", {
                  weekday: "long",
                  day: "2-digit",
                  month: "long",
                  year: "numeric",
                })
              : "Selecione uma data"}
          </p>
        </div>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gray-600">
          {agendaDiaModal.length} agendamento(s)
        </span>
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
          Horarios sugeridos
        </p>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {horariosAgendaModal.map((slot) => (
            <HorarioSugeridoButton
              key={slot.horario}
              formNovo={formNovo}
              onChangeCampo={onChangeCampo}
              slot={slot}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function HorarioSugeridoButton({ formNovo, onChangeCampo, slot }) {
  return (
    <button
      type="button"
      onClick={() => onChangeCampo("hora", slot.horario)}
      className={`rounded-lg border px-2 py-2 text-xs font-medium transition-colors ${
        formNovo.hora === slot.horario
          ? slot.livre
            ? "border-blue-600 bg-blue-600 text-white"
            : "border-amber-500 bg-amber-500 text-white"
          : slot.livre
          ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
          : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
      }`}
    >
      <div>{slot.horario}</div>
      <div className="mt-0.5 text-[10px] opacity-80">
        {slot.livre ? "Livre" : `${slot.ocupados.length} ocupado(s)`}
      </div>
    </button>
  );
}
