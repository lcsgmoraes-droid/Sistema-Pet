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
  return (
    <div className="w-full">
      <label
        className={[
          "inline-flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200",
          disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
        ].join(" ")}
      >
        <input
          id={id}
          name={name || id}
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange?.(event.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-blue-600 accent-blue-600 dark:border-slate-600"
        />
        {label}
      </label>
      {error || help ? (
        <span
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
