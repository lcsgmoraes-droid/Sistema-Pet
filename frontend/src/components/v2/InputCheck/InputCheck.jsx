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
          "inline-flex h-9 items-center justify-center whitespace-nowrap rounded-lg border px-3.5 text-center text-sm font-medium transition-colors",
          "border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
          "peer-checked:border-blue-600 peer-checked:bg-blue-600 peer-checked:text-white peer-checked:hover:bg-blue-700",
          "peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2",
          "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
          "dark:peer-checked:border-blue-500 dark:peer-checked:bg-blue-500 dark:peer-checked:text-white dark:peer-checked:hover:bg-blue-600",
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
