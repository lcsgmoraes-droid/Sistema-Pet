import { ArrowRight, CheckCircle2, RefreshCw } from "lucide-react";

const METRIC_STYLES = {
  violet:
    "border-violet-200 bg-violet-50 text-violet-900 dark:border-violet-500/30 dark:bg-violet-500/10 dark:text-violet-100",
  emerald:
    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100",
  rose: "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100",
  cyan: "border-cyan-200 bg-cyan-50 text-cyan-900 dark:border-cyan-500/30 dark:bg-cyan-500/10 dark:text-cyan-100",
  blue: "border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-100",
};

export function MetricCard({ icon: Icon, label, value, detail, tone, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-md ${METRIC_STYLES[tone]}`}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <span className="rounded-xl bg-white/70 p-2 shadow-sm dark:bg-slate-950/40">
          <Icon className="h-5 w-5" />
        </span>
        <ArrowRight className="h-4 w-4 opacity-40 transition group-hover:translate-x-0.5 group-hover:opacity-80" />
      </div>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 text-2xl font-bold leading-tight">{value}</p>
      <p className="mt-2 text-xs leading-snug opacity-70">{detail}</p>
    </button>
  );
}

export function PriorityCard({ icon: Icon, label, value, detail, hasIssue, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group flex min-h-32 flex-col rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-md ${
        hasIssue
          ? "border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10"
          : "border-emerald-200 bg-emerald-50/70 dark:border-emerald-500/30 dark:bg-emerald-500/10"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <Icon
          className={`h-5 w-5 ${
            hasIssue
              ? "text-amber-700 dark:text-amber-300"
              : "text-emerald-700 dark:text-emerald-300"
          }`}
        />
        {hasIssue ? (
          <ArrowRight className="h-4 w-4 text-amber-500 transition group-hover:translate-x-0.5" />
        ) : (
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
        )}
      </div>
      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white">{value}</p>
      <p className="mt-auto pt-2 text-xs text-slate-600 dark:text-slate-400">{detail}</p>
    </button>
  );
}

export function DashboardLoading() {
  return (
    <div className="flex min-h-[65vh] items-center justify-center">
      <div className="text-center">
        <RefreshCw className="mx-auto h-8 w-8 animate-spin text-[#0f8b8d]" />
        <p className="mt-3 text-sm font-medium text-slate-600 dark:text-slate-300">
          Organizando os principais números...
        </p>
      </div>
    </div>
  );
}
