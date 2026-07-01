import { forwardRef } from "react";

const PADDING = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-4",
};

const Panel = forwardRef(function Panel(
  {
    actions,
    children,
    className = "",
    headerClassName = "",
    padding = "md",
    subtitle,
    title,
    ...props
  },
  ref,
) {
  return (
    <section
      ref={ref}
      {...props}
      className={[
        "rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100",
        PADDING[padding] || PADDING.md,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {(title || subtitle || actions) && (
        <div
          className={["mb-3 flex flex-wrap items-start justify-between gap-3", headerClassName]
            .filter(Boolean)
            .join(" ")}
        >
          <div>
            {title && (
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                {title}
              </h2>
            )}
            {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
          </div>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </div>
      )}
      {children}
    </section>
  );
});

export default Panel;
