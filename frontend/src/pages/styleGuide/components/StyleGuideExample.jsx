export default function StyleGuideExample({ label, note, code, children }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      {label ? (
        <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {label}
        </div>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">{children}</div>
      {note ? <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{note}</p> : null}
      {code ? (
        <pre className="mt-3 overflow-x-auto rounded-md bg-slate-950 px-3 py-2 text-xs text-slate-100">
          <code>{code}</code>
        </pre>
      ) : null}
    </div>
  );
}
