import Panel from "./Panel";

export function FilterRow({ children, className = "" }) {
  return (
    <div className={["flex flex-wrap gap-3", className].filter(Boolean).join(" ")}>{children}</div>
  );
}

export function FilterAdvanced({ children, className = "" }) {
  return (
    <div
      className={["border-t border-slate-200 pt-4 dark:border-slate-700", className]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}

export default function FilterBar({ children, className = "", onSubmit, ...props }) {
  return (
    <Panel className={className} {...props}>
      <form onSubmit={onSubmit} className="space-y-4">
        {children}
      </form>
    </Panel>
  );
}
