export default function InputCheck({
  checked = false,
  disabled = false,
  error = "",
  help = "",
  id,
  label,
  name,
  onChange,
}) {
  const descricaoId = id && (error || help) ? `${id}-descricao` : undefined;

  return (
    <div className="inline-block">
      <span aria-hidden="true" className="invisible block text-xs font-medium">
        &nbsp;
      </span>
      <input
        id={id}
        name={name || id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(evento) => onChange?.(evento.target.checked)}
        aria-invalid={Boolean(error)}
        aria-describedby={descricaoId}
        className="peer sr-only"
      />
      <label
        htmlFor={id}
        className={[
          "mt-1 inline-flex h-9 items-center justify-center whitespace-nowrap rounded-lg border px-3.5 text-center text-sm font-medium transition-colors",
          error ? "border-red-500 dark:border-red-500" : "border-slate-300 dark:border-slate-700",
          "bg-white text-slate-700 hover:bg-slate-50",
          "peer-checked:border-blue-600 peer-checked:bg-blue-600 peer-checked:text-white peer-checked:hover:bg-blue-700",
          "peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2",
          "dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
          "dark:peer-checked:border-blue-500 dark:peer-checked:bg-blue-600 dark:peer-checked:text-white dark:peer-checked:hover:bg-blue-700",
          disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
        ].join(" ")}
      >
        {label}
      </label>
      {error || help ? (
        <span
          id={descricaoId}
          className={[
            "mt-1 block text-xs",
            error ? "text-red-600 dark:text-red-400" : "text-slate-500 dark:text-slate-400",
          ].join(" ")}
        >
          {error || help}
        </span>
      ) : null}
    </div>
  );
}
