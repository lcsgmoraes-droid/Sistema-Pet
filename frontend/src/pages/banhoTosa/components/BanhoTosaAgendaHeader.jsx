export default function BanhoTosaAgendaHeader({ dataRef, onAtualizar }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
          Dia selecionado
        </p>
        <h2 className="mt-2 text-xl font-black text-slate-900">
          Agendamentos de {dataRef}
        </h2>
      </div>
      <button
        type="button"
        onClick={onAtualizar}
        className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-600 transition hover:border-orange-300 hover:text-orange-700"
      >
        Atualizar
      </button>
    </div>
  );
}
