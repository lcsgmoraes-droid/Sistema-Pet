function hasContent(value) {
  return value !== null && value !== undefined && value !== "";
}

export function EntityInfoRow({
  className = "",
  label,
  labelClassName = "",
  value,
  valueClassName = "",
}) {
  return (
    <div
      className={[
        "grid min-h-[22px] grid-cols-[72px_minmax(0,1fr)] items-start gap-2 text-sm",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span className={["font-medium text-slate-700", labelClassName].filter(Boolean).join(" ")}>
        {label}
      </span>
      <span
        className={[
          "min-h-[20px] min-w-0 break-words text-slate-900",
          valueClassName,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {hasContent(value) ? value : <span aria-hidden="true" className="invisible">-</span>}
      </span>
    </div>
  );
}

export default function EntityCard({
  actions,
  bodyClassName = "",
  children,
  className = "",
  inactive = false,
  media,
  statusIcon,
  subtitle,
  title,
}) {
  return (
    <article
      className={[
        "flex h-full min-h-[300px] flex-col rounded-lg border bg-white p-5 shadow-sm transition hover:shadow-md",
        inactive ? "border-red-200 bg-slate-50" : "border-slate-200",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <h3 className="truncate text-lg font-bold text-slate-950">{title}</h3>
            {statusIcon ? <span className="shrink-0">{statusIcon}</span> : null}
          </div>
          {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
        </div>
        {media ? <div className="shrink-0">{media}</div> : null}
      </div>

      <div className={["flex-1", bodyClassName].filter(Boolean).join(" ")}>{children}</div>

      {actions ? <div className="mt-4 flex gap-2">{actions}</div> : null}
    </article>
  );
}
