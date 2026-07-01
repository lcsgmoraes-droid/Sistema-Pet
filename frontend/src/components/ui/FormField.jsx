const toneClasses = {
  default: {
    checkbox:
      "inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
    label: "text-xs font-medium text-slate-600 dark:text-slate-300",
    control:
      "mt-1 h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-cyan-400 dark:disabled:bg-slate-800 dark:disabled:text-slate-500",
  },
  warm: {
    checkbox:
      "flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
    label: "text-xs font-bold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400",
    control:
      "mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100 disabled:cursor-not-allowed disabled:text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:bg-slate-900 dark:focus:ring-orange-400/30 dark:disabled:bg-slate-800 dark:disabled:text-slate-500",
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
  labelAccessory = null,
  labelClassName = "",
  required = false,
  tone = "default",
}) {
  const styles = toneClasses[tone] || toneClasses.default;

  return (
    <label className={cx("block", className)}>
      {label && (
        <span
          className={cx(
            styles.label,
            labelAccessory && "inline-flex items-center gap-1",
            labelClassName,
          )}
        >
          {label}
          {required && <span className="ml-0.5 text-red-500">*</span>}
          {labelAccessory}
        </span>
      )}
      {children}
      {error ? (
        <span className="mt-1 block text-xs text-red-600">{error}</span>
      ) : help ? (
        <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">{help}</span>
      ) : null}
    </label>
  );
}

export function TextField({
  autoComplete,
  className = "",
  disabled = false,
  error = "",
  help = "",
  id,
  inputClassName = "",
  label,
  labelAccessory = null,
  name,
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
      labelAccessory={labelAccessory}
      required={required}
      tone={tone}
    >
      <input
        id={id}
        name={name || id}
        type={type}
        autoComplete={autoComplete}
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
  labelAccessory = null,
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
      labelAccessory={labelAccessory}
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

export function CheckboxField({
  checked = false,
  className = "",
  disabled = false,
  inputClassName = "",
  label,
  labelAccessory = null,
  onChange,
  tone = "default",
}) {
  const styles = toneClasses[tone] || toneClasses.default;

  return (
    <label className={cx(styles.checkbox, disabled && "opacity-60", className)}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange?.(event.target.checked)}
        className={cx(
          "h-4 w-4 rounded border-slate-300",
          tone === "warm" ? "accent-orange-500 text-orange-500" : "accent-blue-600 text-blue-600",
          inputClassName,
        )}
      />
      <span>{label}</span>
      {labelAccessory}
    </label>
  );
}

export default FormField;
