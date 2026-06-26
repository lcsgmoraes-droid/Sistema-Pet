import { formatPercent } from "../../utils/formatters";

export default function PontoEquilibrioStatusSummary({ dados, percentualAtingido, statusResumo }) {
  return (
    <div
      className={`rounded-lg border p-4 ${
        statusResumo.tone === "green"
          ? "border-emerald-200 bg-emerald-50"
          : statusResumo.tone === "amber"
            ? "border-amber-200 bg-amber-50"
            : statusResumo.tone === "red"
              ? "border-red-200 bg-red-50"
              : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-lg font-bold text-slate-900">{statusResumo.title}</p>
          <p className="text-sm text-slate-700">{statusResumo.text}</p>
        </div>
        <div className="min-w-[220px]">
          <div className="flex justify-between text-xs font-semibold text-slate-600">
            <span>0%</span>
            <span>{formatPercent(dados.percentual_atingido || 0)}</span>
          </div>
          <div className="mt-1 h-3 overflow-hidden rounded-full bg-white/80">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all"
              style={{ width: `${percentualAtingido}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
