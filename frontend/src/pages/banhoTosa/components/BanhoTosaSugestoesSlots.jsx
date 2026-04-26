export default function BanhoTosaSugestoesSlots({
  sugestoes,
  loading,
  onUseSlot,
}) {
  return (
    <section className="mt-4 rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-500">
        Sugestao de horario
      </p>
      <h3 className="mt-2 text-lg font-black text-slate-900">
        Melhores encaixes por recurso
      </h3>

      <div className="mt-4 space-y-2">
        {loading && (
          <p className="rounded-2xl bg-slate-50 p-4 text-sm font-semibold text-slate-500">
            Procurando slots livres...
          </p>
        )}

        {!loading && sugestoes.length === 0 && (
          <p className="rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
            Nenhum slot livre encontrado para a duracao selecionada.
          </p>
        )}

        {!loading && sugestoes.slice(0, 6).map((slot) => (
          <button
            key={`${slot.recurso_id}-${slot.horario_inicio}`}
            type="button"
            onClick={() => onUseSlot(slot)}
            className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-emerald-300 hover:bg-emerald-50"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-black text-slate-900">
                  {hora(slot.horario_inicio)} - {hora(slot.horario_fim)}
                </p>
                <p className="text-sm font-semibold text-slate-600">
                  {slot.recurso_nome} ({slot.recurso_tipo})
                </p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-emerald-700">
                {slot.vagas_disponiveis} vaga(s)
              </span>
            </div>
            <p className="mt-2 text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
              {slot.motivo}
            </p>
          </button>
        ))}
      </div>
    </section>
  );
}

function hora(valor) {
  return String(valor || "").slice(11, 16);
}
