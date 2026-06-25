import { formatDurationMs, formatNumber } from "../estoqueBlingUtils";
import { ISSUE_TONES } from "./estoqueBlingConfig";

export function SummaryCard({ label, value, hint, tone = "slate" }) {
  const toneClasses = ISSUE_TONES[tone] || ISSUE_TONES.slate;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-sm font-medium text-slate-500">{label}</div>
      <div className="mt-3 flex items-end gap-3">
        <div className="text-3xl font-semibold text-slate-900">{value}</div>
        {hint ? (
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${toneClasses.badge}`}>
            {hint}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function HealthMeter({ percent, label, detail, tone = "slate" }) {
  const toneMap = {
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    red: "bg-red-500",
    sky: "bg-sky-500",
    slate: "bg-slate-500",
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center justify-between gap-3 text-sm">
        <div className="font-semibold text-slate-900">{label}</div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {percent}%
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all ${toneMap[tone] || toneMap.slate}`}
          style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
        />
      </div>
      <div className="mt-2 text-sm text-slate-600">{detail}</div>
    </div>
  );
}

export function TabButton({ active, label, count, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
        active
          ? "bg-slate-900 text-white shadow-sm"
          : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
      }`}
    >
      <span>{label}</span>
      <span
        className={`rounded-full px-2 py-0.5 text-xs ${active ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"}`}
      >
        {count}
      </span>
    </button>
  );
}

export function DetailItem({ label, value, mono = false }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className={`mt-1 text-sm text-slate-800 ${mono ? "font-mono" : ""}`}>{value || "-"}</div>
    </div>
  );
}

export function PendingCard({
  title,
  subtitle,
  reason,
  tone = "slate",
  badges = [],
  details = [],
  actions = [],
  children = null,
}) {
  const toneClasses = ISSUE_TONES[tone] || ISSUE_TONES.slate;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 flex-1 space-y-4">
          <div className="space-y-1">
            <div className="text-base font-semibold text-slate-900">{title}</div>
            {subtitle ? <div className="text-sm text-slate-500">{subtitle}</div> : null}
          </div>

          {badges.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {badges.map((badge) => (
                <span
                  key={`${badge.label}-${badge.value}`}
                  className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
                >
                  {badge.label}:{" "}
                  <span className={badge.mono ? "font-mono" : ""}>{badge.value || "-"}</span>
                </span>
              ))}
            </div>
          ) : null}

          <div className={`rounded-xl border px-4 py-3 text-sm ${toneClasses.panel}`}>
            <div className="font-semibold">{reason.title}</div>
            <div className="mt-1">{reason.description}</div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            {details.map((detail) => (
              <DetailItem
                key={`${detail.label}-${detail.value}`}
                label={detail.label}
                value={detail.value}
                mono={detail.mono}
              />
            ))}
          </div>

          {children ? <div className="space-y-3">{children}</div> : null}
        </div>

        <div className="flex w-full flex-col gap-2 xl:w-56">
          {actions.map((action) => (
            <button
              key={action.label}
              onClick={action.onClick}
              disabled={action.disabled}
              className={`rounded-xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 ${action.className}`}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function MassLinkProgressPanel({ progress, onClose }) {
  if (!progress) return null;

  const initialTotal = Number(progress.initialTotal || 0);
  const remaining = Math.max(Number(progress.remaining || 0), 0);
  const completed = Math.max(initialTotal - remaining, 0);
  const percent =
    initialTotal > 0 ? Math.min(100, Math.round((completed / initialTotal) * 100)) : 0;

  return (
    <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 shadow-sm">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-sm font-semibold text-sky-900">Execucao do vinculo em lotes</div>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${progress.running ? "bg-sky-600 text-white" : "bg-emerald-100 text-emerald-700"}`}
            >
              {progress.running ? "Em andamento" : "Concluido"}
            </span>
          </div>

          <div className="text-sm text-slate-700">{progress.message}</div>

          <div className="grid gap-3 md:grid-cols-4">
            <DetailItem
              label="Lotes"
              value={`${progress.batchesCompleted || 0}/${progress.maxBatches || 0}`}
            />
            <DetailItem label="Tentados" value={formatNumber(progress.attempted || 0)} />
            <DetailItem label="Vinculados" value={formatNumber(progress.linked || 0)} />
            <DetailItem label="Restantes" value={formatNumber(remaining)} />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-sky-700">
              <span>Evolucao</span>
              <span>{percent}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white">
              <div
                className="h-full rounded-full bg-sky-600 transition-all"
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <DetailItem label="Sync OK" value={formatNumber(progress.syncOk || 0)} />
            <DetailItem label="Sync com erro" value={formatNumber(progress.syncErrors || 0)} />
            <DetailItem label="Nao encontrados" value={formatNumber(progress.notFound || 0)} />
            <DetailItem label="Duracao" value={formatDurationMs(progress.elapsedMs || 0)} />
          </div>

          {progress.history?.length ? (
            <div className="space-y-1 rounded-xl bg-white/70 px-3 py-3 text-sm text-slate-600">
              {progress.history.map((item) => (
                <div key={`batch-${item.batchNumber}`}>
                  Lote {item.batchNumber}: {item.linked} vinculados, {item.errors} erros,{" "}
                  {item.remaining} restantes, {formatDurationMs(item.elapsedMs)}
                </div>
              ))}
            </div>
          ) : null}
        </div>

        {!progress.running ? (
          <button
            onClick={onClose}
            className="rounded-xl border border-sky-200 bg-white px-4 py-2 text-sm font-semibold text-sky-700 transition hover:bg-sky-100"
          >
            Fechar resumo
          </button>
        ) : null}
      </div>
    </div>
  );
}
