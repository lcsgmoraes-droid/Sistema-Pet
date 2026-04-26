import AgendamentoDiaCard from "./AgendamentoDiaCard";

export default function CompromissosDiaSection({
  abrindoAgendamentoId,
  agendaDiaModal,
  carregandoAgendaDiaModal,
  onOpenAgendamento,
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="mb-3 text-sm font-semibold text-gray-800">Compromissos do dia selecionado</p>
      {carregandoAgendaDiaModal ? (
        <div className="text-sm text-gray-500">Carregando agenda do dia...</div>
      ) : agendaDiaModal.length === 0 ? (
        <div className="rounded-lg border border-dashed border-emerald-200 bg-emerald-50 px-3 py-4 text-sm text-emerald-700">
          Nenhum compromisso neste dia. A agenda esta livre.
        </div>
      ) : (
        <div className="max-h-[300px] space-y-2 overflow-y-auto pr-1">
          {agendaDiaModal.map((agendamento) => (
            <AgendamentoDiaCard
              key={agendamento.id}
              abrindoAgendamentoId={abrindoAgendamentoId}
              agendamento={agendamento}
              onOpenAgendamento={onOpenAgendamento}
            />
          ))}
        </div>
      )}
    </div>
  );
}
