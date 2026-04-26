export default function BanhoTosaCapacidadePanel({ capacidade }) {
  const recursos = capacidade?.recursos || [];
  const alertas = capacidade?.alertas || [];

  return (
    <section className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-500">
            Capacidade do dia
          </p>
          <h3 className="mt-2 text-lg font-black text-slate-900">
            {capacidade?.janela_inicio || "08:00"} as {capacidade?.janela_fim || "18:00"}
          </h3>
        </div>
        <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-bold text-sky-700">
          {capacidade?.total_agendamentos || 0} agenda(s)
        </span>
      </div>

      {alertas.length > 0 && (
        <div className="mt-4 space-y-2">
          {alertas.map((alerta) => (
            <div
              key={alerta}
              className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800"
            >
              {alerta}
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {recursos.map((recurso) => (
          <RecursoOcupacao key={recurso.recurso_id} recurso={recurso} />
        ))}
        {recursos.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 p-5 text-center text-sm font-semibold text-slate-500 md:col-span-2">
            Cadastre recursos para visualizar a ocupacao.
          </div>
        )}
      </div>
    </section>
  );
}

function RecursoOcupacao({ recurso }) {
  const percentual = Math.min(Number(recurso.ocupacao_percentual || 0), 100);
  const excedido = recurso.capacidade_excedida;

  return (
    <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-black text-slate-900">{recurso.recurso_nome}</p>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
            {recurso.recurso_tipo}
          </p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-bold ${
            excedido ? "bg-red-100 text-red-700" : "bg-white text-slate-600"
          }`}
        >
          pico {recurso.pico_simultaneo}/{recurso.capacidade_simultanea}
        </span>
      </div>

      <div className="mt-4 h-3 overflow-hidden rounded-full bg-white">
        <div
          className={`h-full rounded-full ${excedido ? "bg-red-500" : "bg-sky-500"}`}
          style={{ width: `${percentual}%` }}
        />
      </div>

      <div className="mt-3 flex justify-between text-xs font-bold text-slate-500">
        <span>{recurso.agendamentos} agenda(s)</span>
        <span>{recurso.ocupacao_percentual}% ocupado</span>
      </div>
    </article>
  );
}
