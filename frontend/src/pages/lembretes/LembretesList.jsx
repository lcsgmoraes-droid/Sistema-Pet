import { FiBell, FiSearch, FiSliders } from "react-icons/fi";
import LembreteCard from "./LembreteCard";
import { PRAZOS, TIPOS_LEMBRETE } from "./lembretesUtils";

export default function LembretesList({ controller }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-200 p-4 dark:border-slate-800 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
              Fila de recompra
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Cada faixa de prazo é exclusiva; atrasados não contam nos próximos 7 dias.
            </p>
          </div>
          <label className="relative block lg:w-80">
            <span className="sr-only">Buscar lembrete</span>
            <FiSearch
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm text-slate-800 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
              onChange={(event) => controller.setBusca(event.target.value)}
              placeholder="Cliente, pet ou produto"
              type="search"
              value={controller.busca}
            />
          </label>
        </div>
        <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-2" aria-label="Filtrar por prazo">
            {PRAZOS.map((prazo) => (
              <button
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ring-1 ring-inset transition ${
                  controller.filtroPrazo === prazo.id
                    ? "bg-teal-700 text-white ring-teal-700"
                    : "bg-white text-slate-600 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700 dark:hover:bg-slate-800"
                }`}
                key={prazo.id}
                onClick={() => controller.setFiltroPrazo(prazo.id)}
                type="button"
              >
                {prazo.label} · {controller.contadoresPrazo[prazo.id] || 0}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <FiSliders aria-hidden="true" />
            <span className="sr-only sm:not-sr-only">Tipo</span>
            <select
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-950"
              onChange={(event) => controller.setFiltroTipo(event.target.value)}
              value={controller.filtroTipo}
            >
              <option value="todos">Todos os tipos</option>
              {Object.entries(TIPOS_LEMBRETE).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {controller.loading ? (
        <EmptyState text="Carregando lembretes..." />
      ) : controller.lembretesFiltrados.length === 0 ? (
        <EmptyState
          text={
            controller.lembretes.length
              ? "Nenhum item corresponde aos filtros."
              : "Nenhuma recompra prevista."
          }
        />
      ) : (
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {controller.lembretesFiltrados.map((lembrete) => (
            <LembreteCard controller={controller} key={lembrete.id} lembrete={lembrete} />
          ))}
        </div>
      )}
    </section>
  );
}

function EmptyState({ text }) {
  return (
    <div className="px-5 py-14 text-center text-sm text-slate-500 dark:text-slate-400">
      <FiBell aria-hidden="true" className="mx-auto mb-3" size={24} />
      {text}
    </div>
  );
}
