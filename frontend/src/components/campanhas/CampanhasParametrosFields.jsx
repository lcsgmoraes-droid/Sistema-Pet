export function CampanhaField({
  label,
  id,
  type = "number",
  step = "any",
  min,
  value,
  onChange,
  placeholder,
  colSpan,
}) {
  return (
    <div className={colSpan ? `col-span-${colSpan}` : ""}>
      <label
        htmlFor={id}
        className="block text-xs font-medium text-gray-600 mb-1"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        step={step}
        min={min}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
        className="w-full border rounded-lg px-3 py-1.5 text-sm"
      />
    </div>
  );
}

export function CampanhaSel({ label, id, value, onChange, children }) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-xs font-medium text-gray-600 mb-1"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={onChange}
        className="w-full border rounded-lg px-3 py-1.5 text-sm"
      >
        {children}
      </select>
    </div>
  );
}
