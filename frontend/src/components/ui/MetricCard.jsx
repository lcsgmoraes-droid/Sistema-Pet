const INTENTS = {
  blue: "border-blue-200 bg-blue-50 text-blue-700",
  cyan: "border-cyan-200 bg-cyan-50 text-cyan-700",
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
  red: "border-red-200 bg-red-50 text-red-700",
  slate: "border-slate-200 bg-slate-50 text-slate-700",
  violet: "border-violet-200 bg-violet-50 text-violet-700",
  amber: "border-amber-200 bg-amber-50 text-amber-700",
};

export default function MetricCard({
  className = "",
  icon,
  intent = "slate",
  label,
  subtitle,
  value,
}) {
  return (
    <article
      className={[
        "flex min-h-[92px] flex-col justify-between rounded-lg border p-4",
        INTENTS[intent] || INTENTS.slate,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-wide">{label}</div>
        {icon ? <div className="shrink-0 opacity-80">{icon}</div> : null}
      </div>
      <div>
        <div className="mt-2 text-2xl font-bold leading-tight text-slate-950">
          {value ?? "-"}
        </div>
        {subtitle ? (
          <p className="mt-1 text-xs leading-snug opacity-80">{subtitle}</p>
        ) : null}
      </div>
    </article>
  );
}
