import BanhoTosaAgendaCard from "./BanhoTosaAgendaCard";
import BanhoTosaAgendaHeader from "./BanhoTosaAgendaHeader";

export default function BanhoTosaAgendaList({
  agendamentos,
  dataRef,
  loading,
  onAtualizar,
  onCancelar,
  onCheckIn,
}) {
  return (
    <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <BanhoTosaAgendaHeader dataRef={dataRef} onAtualizar={onAtualizar} />
      <div className="mt-5 space-y-3">
        {loading && (
          <div className="rounded-2xl bg-slate-50 p-5 text-center text-sm font-semibold text-slate-500">
            Carregando agenda...
          </div>
        )}

        {!loading && agendamentos.map((agendamento) => (
          <BanhoTosaAgendaCard
            key={agendamento.id}
            agendamento={agendamento}
            onCheckIn={onCheckIn}
            onCancelar={onCancelar}
          />
        ))}

        {!loading && agendamentos.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500">
            Nenhum agendamento para esta data.
          </div>
        )}
      </div>
    </div>
  );
}
