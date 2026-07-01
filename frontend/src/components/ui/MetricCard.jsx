const INTENTS = {
  blue: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-200",
  cyan: "border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-400/30 dark:bg-cyan-500/10 dark:text-cyan-200",
  emerald:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-500/10 dark:text-emerald-200",
  red: "border-red-200 bg-red-50 text-red-700 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-200",
  slate:
    "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300",
  violet:
    "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-400/30 dark:bg-violet-500/10 dark:text-violet-200",
  amber:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-200",
};

const SIZES = {
  compact: {
    card: "min-h-[58px] p-3",
    value: "mt-1 text-sm",
    subtitle: "mt-0.5",
  },
  md: {
    card: "min-h-[92px] p-4",
    value: "mt-2 text-2xl",
    subtitle: "mt-1",
  },
};

export default function MetricCard({
  className = "",
  icon,
  intent = "slate",
  label,
  size = "md",
  subtitle,
  value,
}) {
  const sizeClasses = SIZES[size] || SIZES.md;

  return (
    <article
      className={[
        "flex flex-col justify-between rounded-lg border",
        sizeClasses.card,
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
        <div
          className={[
            "font-bold leading-tight text-slate-950 dark:text-slate-100",
            sizeClasses.value,
          ].join(" ")}
        >
          {value ?? "-"}
        </div>
        {subtitle ? (
          <p className={["text-xs leading-snug opacity-80", sizeClasses.subtitle].join(" ")}>
            {subtitle}
          </p>
        ) : null}
      </div>
    </article>
  );
}
