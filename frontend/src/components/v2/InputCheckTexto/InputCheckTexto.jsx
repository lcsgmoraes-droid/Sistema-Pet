import { forwardRef } from "react";

// Checkbox com rótulo longo/rico (aceita texto com link no meio) — para aceite de termos,
// autorizações e afins. Para toggle curto em formato pill, usar InputCheck.
const InputCheckTexto = forwardRef(function InputCheckTexto(
  { checked = false, children, disabled = false, error = "", id, name, onChange, required = false },
  ref,
) {
  const descricaoId = id && error ? `${id}-descricao` : undefined;

  return (
    <div>
      <label
        htmlFor={id}
        className="flex items-start gap-3 text-sm text-slate-700 dark:text-slate-300"
      >
        <input
          ref={ref}
          id={id}
          name={name || id}
          type="checkbox"
          checked={checked}
          disabled={disabled}
          required={required}
          onChange={(evento) => onChange?.(evento.target.checked)}
          aria-invalid={Boolean(error)}
          aria-describedby={descricaoId}
          className={[
            "mt-0.5 h-4 w-4 flex-none rounded text-blue-600 focus:ring-2 focus:ring-blue-500",
            error ? "border-red-500" : "border-slate-300 dark:border-slate-600",
            "dark:bg-slate-900",
            disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
          ].join(" ")}
        />
        <span>{children}</span>
      </label>
      {error ? (
        <span id={descricaoId} className="mt-1 block text-xs text-red-600 dark:text-red-400">
          {error}
        </span>
      ) : null}
    </div>
  );
});

export default InputCheckTexto;
