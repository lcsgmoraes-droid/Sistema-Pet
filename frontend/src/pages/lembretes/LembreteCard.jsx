import { FiCheckCircle, FiRefreshCw, FiTrash2 } from "react-icons/fi";
import PetIdentity from "../../components/ui/PetIdentity";
import { formatarMoeda } from "./lembretesFormatters";

export default function LembreteCard({ lembrete, onCompletar, onRenovar, onCancelar }) {
  const diasRestantes = lembrete.dias_restantes;
  const dataProxima = new Date(lembrete.data_proxima_dose);
  const status = diasRestantes < 0 ? "vencido" : diasRestantes <= 7 ? "proximo" : "futuro";
  const temDoseTotal = lembrete.dose_total && lembrete.dose_total > 0;
  const progressoPercentual = temDoseTotal ? (lembrete.dose_atual / lembrete.dose_total) * 100 : 0;

  return (
    <article className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h3 className="m-0 min-w-0 text-base font-semibold text-slate-900 dark:text-slate-100">
            {lembrete.produto_nome}
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            {temDoseTotal && (
              <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-500/30">
                Dose {lembrete.dose_atual}/{lembrete.dose_total}
              </span>
            )}
            <span className={statusClassName(status)}>
              {diasRestantes < 0
                ? "Vencido"
                : diasRestantes === 0
                  ? "Hoje"
                  : `${Math.abs(diasRestantes)} dia(s)`}
            </span>
          </div>
        </div>

        {temDoseTotal && (
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              className="h-full rounded-full bg-teal-600 transition-[width]"
              style={{ width: `${Math.min(100, progressoPercentual)}%` }}
            />
          </div>
        )}

        <dl className="mt-3 grid gap-x-5 gap-y-2 text-sm text-slate-600 dark:text-slate-400 sm:grid-cols-2 xl:grid-cols-4">
          <div className="flex min-w-0 gap-1.5">
            <dt className="font-medium text-slate-500 dark:text-slate-500">Pet:</dt>
            <dd className="m-0 min-w-0 text-slate-800 dark:text-slate-200">
              <PetIdentity
                fallback="Nao informado"
                layout="inline"
                nameClassName="font-medium"
                record={lembrete}
              />
            </dd>
          </div>
          <div className="flex gap-1.5">
            <dt className="font-medium text-slate-500 dark:text-slate-500">Previsao:</dt>
            <dd className="m-0 text-slate-800 dark:text-slate-200">
              {dataProxima.toLocaleDateString("pt-BR")}
            </dd>
          </div>
          <div className="flex gap-1.5">
            <dt className="font-medium text-slate-500 dark:text-slate-500">Quantidade:</dt>
            <dd className="m-0 text-slate-800 dark:text-slate-200">{lembrete.quantidade}</dd>
          </div>
          {lembrete.preco_estimado && (
            <div className="flex gap-1.5">
              <dt className="font-medium text-slate-500 dark:text-slate-500">Valor estimado:</dt>
              <dd className="m-0 text-slate-800 dark:text-slate-200">
                {formatarMoeda(lembrete.preco_estimado)}
              </dd>
            </div>
          )}
        </dl>
      </div>

      <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3 dark:border-slate-800 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-teal-700 bg-teal-700 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600"
          onClick={() => onCompletar(lembrete.id)}
          title="Marcar como completado"
          type="button"
        >
          <FiCheckCircle aria-hidden="true" /> Comprado
        </button>
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          onClick={() => onRenovar(lembrete.id)}
          title="Renovar lembrete"
          type="button"
        >
          <FiRefreshCw aria-hidden="true" /> Renovar
        </button>
        <button
          aria-label="Cancelar lembrete"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-red-200 bg-red-50 text-red-700 transition hover:bg-red-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200 dark:hover:bg-red-500/20"
          onClick={() => onCancelar(lembrete.id)}
          title="Cancelar lembrete"
          type="button"
        >
          <FiTrash2 aria-hidden="true" />
        </button>
      </div>
    </article>
  );
}

function statusClassName(status) {
  const base = "rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset";
  if (status === "vencido") {
    return `${base} bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-300 dark:ring-red-500/30`;
  }
  if (status === "proximo") {
    return `${base} bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30`;
  }
  return `${base} bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700`;
}
