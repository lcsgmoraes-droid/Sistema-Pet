import Panel from "../../../components/ui/Panel";

export default function BanhoTosaCapacidadePanel({ capacidade }) {
  const recursos = capacidade?.recursos || [];
  const alertas = capacidade?.alertas || [];

  return (
    <Panel
      actions={
        <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-bold text-sky-700">
          {capacidade?.total_agendamentos || 0} agenda(s)
        </span>
      }
      subtitle={`${capacidade?.janela_inicio || "08:00"} as ${capacidade?.janela_fim || "18:00"}`}
      title="Capacidade do dia"
    >

      {alertas.length > 0 && (
        <div className="space-y-2">
          {alertas.map((alerta) => (
            <div
              key={alerta}
              className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800"
            >
              {alerta}
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {recursos.map((recurso) => (
          <RecursoOcupacao key={recurso.recurso_id} recurso={recurso} />
        ))}
        {recursos.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 p-5 text-center text-sm font-semibold text-slate-500 md:col-span-2">
            Cadastre recursos para visualizar a ocupacao.
          </div>
        )}
      </div>
    </Panel>
  );
}

function RecursoOcupacao({ recurso }) {
  const percentual = Math.min(Number(recurso.ocupacao_percentual || 0), 100);
  const excedido = recurso.capacidade_excedida;

  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-900">{recurso.recurso_nome}</p>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
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

      <div className="mt-3 h-2 overflow-hidden rounded-full bg-white">
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
