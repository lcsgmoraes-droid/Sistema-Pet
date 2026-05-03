const toneClasses = {
  default: {
    label: "text-xs font-medium text-slate-600",
    control:
      "mt-1 h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400",
  },
  warm: {
    label: "text-xs font-bold uppercase tracking-[0.12em] text-slate-500",
    control:
      "mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100 disabled:cursor-not-allowed disabled:text-slate-400",
  },
};

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

export function FormField({
  children,
  className = "",
  error = "",
  help = "",
  label,
  labelClassName = "",
  required = false,
  tone = "default",
}) {
  const styles = toneClasses[tone] || toneClasses.default;

  return (
    <label className={cx("block", className)}>
      {label && (
        <span className={cx(styles.label, labelClassName)}>
          {label}
          {required && <span className="ml-0.5 text-red-500">*</span>}
        </span>
      )}
      {children}
      {error ? (
        <span className="mt-1 block text-xs text-red-600">{error}</span>
      ) : help ? (
        <span className="mt-1 block text-xs text-slate-500">{help}</span>
      ) : null}
    </label>
  );
}

export function TextField({
  className = "",
  disabled = false,
  error = "",
  help = "",
  inputClassName = "",
  label,
  onChange,
  placeholder,
  required = false,
  step,
  tone = "default",
  type = "text",
  value,
}) {
  const styles = toneClasses[tone] || toneClasses.default;

  return (
    <FormField
      className={className}
      error={error}
      help={help}
      label={label}
      required={required}
      tone={tone}
    >
      <input
        type={type}
        step={step ?? (type === "number" ? "0.01" : undefined)}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(event) => onChange?.(event.target.value)}
        className={cx(styles.control, inputClassName)}
      />
    </FormField>
  );
}

export function SelectField({
  children,
  className = "",
  disabled = false,
  error = "",
  help = "",
  label,
  onChange,
  required = false,
  selectClassName = "",
  tone = "default",
  value,
}) {
  const styles = toneClasses[tone] || toneClasses.default;

  return (
    <FormField
      className={className}
      error={error}
      help={help}
      label={label}
      required={required}
      tone={tone}
    >
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange?.(event.target.value)}
        className={cx(styles.control, selectClassName)}
      >
        {children}
      </select>
    </FormField>
  );
}

export default FormField;
