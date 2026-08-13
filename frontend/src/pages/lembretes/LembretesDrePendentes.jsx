import { FiBarChart2 } from "react-icons/fi";

export default function LembretesDrePendentes({ dresPendentes, onAbrirDre }) {
  if (dresPendentes <= 0) return null;

  return (
    <section className="mb-5 overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-sm dark:border-indigo-500/30 dark:bg-slate-900">
      <header className="flex items-center gap-3 border-b border-indigo-200 bg-indigo-50 px-5 py-4 dark:border-indigo-500/30 dark:bg-indigo-500/10">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-200 dark:bg-slate-900 dark:text-indigo-300 dark:ring-indigo-500/30">
          <FiBarChart2 aria-hidden="true" />
        </span>
        <div>
          <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
            DRE - lancamentos pendentes
          </h2>
          <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">
            Valores ainda sem classificacao financeira.
          </p>
        </div>
      </header>
      <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="text-3xl font-bold text-indigo-700 dark:text-indigo-300">
            {dresPendentes}
          </span>
          <p className="m-0 text-sm leading-5 text-slate-600 dark:text-slate-400">
            lancamento{dresPendentes !== 1 ? "s" : ""} sem categoria DRE.
            <br />O demonstrativo pode ficar incompleto ate a classificacao.
          </p>
        </div>
        <button
          type="button"
          onClick={onAbrirDre}
          className="inline-flex items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-700 shadow-sm transition hover:bg-indigo-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-200 dark:hover:bg-indigo-500/20"
        >
          Ir para o DRE e classificar
        </button>
      </div>
    </section>
  );
}
