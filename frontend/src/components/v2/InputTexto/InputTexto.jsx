import { forwardRef } from "react";

const InputTexto = forwardRef(function InputTexto(
  {
    alinhamentoTexto = "left",
    autoFocus,
    disabled = false,
    error = "",
    help = "",
    id,
    inputMode,
    label,
    maxLength,
    name,
    onBlur,
    onChange,
    onFocus,
    onKeyDown,
    placeholder,
    readOnly = false,
    required = false,
    right = null,
    type = "text",
    value = "",
  },
  ref,
) {
  return (
    <label className="block w-full">
      {label ? (
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
          {label}
          {required ? <span className="ml-0.5 text-red-500">*</span> : null}
        </span>
      ) : null}
      <span className="relative mt-1 block">
        <input
          ref={ref}
          id={id}
          name={name || id}
          type={type}
          autoFocus={autoFocus}
          inputMode={inputMode}
          maxLength={maxLength}
          value={value}
          placeholder={placeholder}
          disabled={disabled}
          readOnly={readOnly}
          onChange={(event) => onChange?.(event.target.value)}
          onBlur={onBlur}
          onFocus={onFocus}
          onKeyDown={onKeyDown}
          aria-invalid={Boolean(error)}
          aria-describedby={error || help ? `${id}-descricao` : undefined}
          className={[
            "h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none transition-colors",
            "focus:border-transparent focus:ring-2 focus:ring-blue-500",
            "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400",
            "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500",
            "dark:focus:ring-cyan-400 dark:disabled:bg-slate-800 dark:disabled:text-slate-500",
            right ? "pr-9" : "",
            alinhamentoTexto === "direita" ? "text-right" : "",
          ].join(" ")}
        />
        {right ? (
          <span className="absolute inset-y-0 right-1 flex items-center">{right}</span>
        ) : null}
      </span>
      {error || help ? (
        <span
          id={`${id}-descricao`}
          className={[
            "mt-1 block text-xs",
            error ? "text-red-600 dark:text-red-400" : "text-slate-500 dark:text-slate-400",
          ].join(" ")}
        >
          {error || help}
        </span>
      ) : null}
    </label>
  );
});

export default InputTexto;
