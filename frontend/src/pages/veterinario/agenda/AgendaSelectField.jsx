export default function AgendaSelectField({ alerta = "", disabled, label, onChange, options, placeholder, value }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
        disabled={disabled}
      >
        <option value="">{placeholder}</option>
        {options.map((item) => (
          <option key={item.id} value={item.id}>
            {item.nome}
          </option>
        ))}
      </select>
      {alerta && <p className="mt-1 text-xs text-amber-600">{alerta}</p>}
    </div>
  );
}
