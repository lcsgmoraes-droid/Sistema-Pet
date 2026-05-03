export default function BanhoTosaSugestoesSlots({
  sugestoes,
  loading,
  onUseSlot,
}) {
  return (
    <section className="mt-4 border-t border-slate-200 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Sugestoes de horario
          </h3>
          <p className="text-sm text-slate-500">
            Melhores encaixes por recurso.
          </p>
        </div>
      </div>

      <div className="mt-3 grid gap-2 lg:grid-cols-2">
        {loading && (
          <p className="rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-500 lg:col-span-2">
            Procurando slots livres...
          </p>
        )}

        {!loading && sugestoes.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-500 lg:col-span-2">
            Nenhum slot livre encontrado para a duracao selecionada.
          </p>
        )}

        {!loading && sugestoes.slice(0, 6).map((slot) => (
          <button
            key={`${slot.recurso_id}-${slot.horario_inicio}`}
            type="button"
            onClick={() => onUseSlot(slot)}
            className="w-full rounded-lg border border-slate-200 bg-slate-50 p-3 text-left transition hover:border-emerald-300 hover:bg-emerald-50"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-slate-900">
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
