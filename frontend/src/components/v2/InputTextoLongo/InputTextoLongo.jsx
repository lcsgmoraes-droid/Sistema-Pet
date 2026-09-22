import { forwardRef } from "react";

const InputTextoLongo = forwardRef(function InputTextoLongo(
  {
    disabled = false,
    error = "",
    help = "",
    id,
    label,
    linhas = 3,
    maxLength,
    name,
    onBlur,
    onChange,
    onFocus,
    placeholder,
    required = false,
    value = "",
  },
  ref,
) {
  return (
    <label className="block w-full">
      {label ? (
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
          {label}
          {required ? (
            <span className="ml-0.5 text-red-500">
              *<span className="sr-only"> (obrigatório)</span>
            </span>
          ) : null}
        </span>
      ) : null}
      <textarea
        ref={ref}
        id={id}
        name={name || id}
        rows={linhas}
        maxLength={maxLength}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        aria-required={required}
        onChange={(event) => onChange?.(event.target.value)}
        onBlur={onBlur}
        onFocus={onFocus}
        aria-invalid={Boolean(error)}
        aria-describedby={id && (error || help) ? `${id}-descricao` : undefined}
        className={[
          "mt-1 w-full resize-y rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors",
          "focus:border-transparent focus:ring-2",
          "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400",
          "dark:!bg-slate-900 dark:!text-slate-100 dark:placeholder:!text-slate-500",
          "dark:disabled:!bg-slate-800 dark:disabled:!text-slate-500",
          error
            ? "border-red-500 focus:ring-red-500 dark:!border-red-500 dark:focus:ring-red-400"
            : "border-slate-300 focus:ring-blue-500 dark:!border-slate-700 dark:focus:ring-cyan-400",
        ].join(" ")}
      />
      {error || help ? (
        <span
          id={id ? `${id}-descricao` : undefined}
          className={[
            "mt-1 block text-xs",
            error ? "text-red-700 dark:text-red-400" : "text-slate-500 dark:text-slate-400",
          ].join(" ")}
        >
          {error || help}
        </span>
      ) : null}
    </label>
  );
});

export default InputTextoLongo;
