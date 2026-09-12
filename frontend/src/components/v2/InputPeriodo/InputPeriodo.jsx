import InputData from "../InputData/InputData";

export default function InputPeriodo({
  disabled = false,
  error = "",
  help = "",
  label,
  onChange,
  required = false,
  value = {},
}) {
  const { inicio = "", fim = "" } = value;

  return (
    <div className="w-full">
      {label ? (
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
          {label}
          {required ? <span className="ml-0.5 text-red-500">*</span> : null}
        </span>
      ) : null}
      <div className="mt-1 flex items-center gap-2">
        <InputData
          disabled={disabled}
          help=""
          label={null}
          onChange={(novoInicio) => onChange?.({ inicio: novoInicio, fim })}
          value={inicio}
        />
        <span className="shrink-0 text-xs font-semibold text-slate-400">até</span>
        <InputData
          disabled={disabled}
          help=""
          label={null}
          onChange={(novoFim) => onChange?.({ inicio, fim: novoFim })}
          value={fim}
        />
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
