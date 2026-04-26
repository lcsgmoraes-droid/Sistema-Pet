export default function RepasseFiltros({
  dataFim,
  dataInicio,
  filtroStatus,
  filtroTipo,
  setDataFim,
  setDataInicio,
  setFiltroStatus,
  setFiltroTipo,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <CampoData label="Data inicio" value={dataInicio} onChange={setDataInicio} />
        <CampoData label="Data fim" value={dataFim} onChange={setDataFim} />
        <CampoSelect
          label="Status"
          value={filtroStatus}
          onChange={setFiltroStatus}
          options={[
            ["", "Todos"],
            ["pendente", "Pendente"],
            ["recebido", "Recebido"],
            ["vencido", "Vencido"],
          ]}
        />
        <CampoSelect
          label="Tipo de lancamento"
          value={filtroTipo}
          onChange={setFiltroTipo}
          options={[
            ["", "Todos"],
            ["repasse_empresa", "Repasse empresa"],
            ["liquido_vet", "Liquido veterinario"],
          ]}
        />
      </div>
    </div>
  );
}

function CampoData({ label, onChange, value }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <input
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-300"
      />
    </div>
  );
}

function CampoSelect({ label, onChange, options, value }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sky-300"
      >
        {options.map(([optionValue, labelOption]) => (
          <option key={optionValue || "todos"} value={optionValue}>{labelOption}</option>
        ))}
      </select>
    </div>
  );
}
