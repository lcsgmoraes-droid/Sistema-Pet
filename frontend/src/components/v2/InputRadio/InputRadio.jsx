export default function InputRadio({
  disabled = false,
  error = "",
  help = "",
  label,
  name,
  onChange,
  opcoes = [],
  required = false,
  value,
}) {
  return (
    <div className="w-full">
      {label ? (
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
          {label}
          {required ? <span className="ml-0.5 text-red-500">*</span> : null}
        </span>
      ) : null}
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-2">
        {opcoes.map((opcao) => (
          <label
            key={opcao.value}
            className={[
              "inline-flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200",
              disabled || opcao.disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
            ].join(" ")}
          >
            <input
              type="radio"
              name={name}
              value={opcao.value}
              checked={value === opcao.value}
              disabled={disabled || opcao.disabled}
              onChange={() => onChange?.(opcao.value)}
              className="h-4 w-4 border-slate-300 text-blue-600 accent-blue-600 dark:border-slate-600"
            />
            {opcao.label}
          </label>
        ))}
      </div>
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
