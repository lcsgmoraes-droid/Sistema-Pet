export default function HistoricoInternacoesFiltros({
  pessoas,
  petsHistoricoDaPessoa,
  filtroDataAltaInicio,
  filtroDataAltaFim,
  filtroPessoaHistorico,
  filtroPetHistorico,
  onChangeDataAltaInicio,
  onChangeDataAltaFim,
  onChangePessoaHistorico,
  onChangePetHistorico,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-sm font-semibold text-gray-700 mb-3">Filtros do histórico</p>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Alta de</label>
          <input
            type="date"
            value={filtroDataAltaInicio}
            onChange={(event) => onChangeDataAltaInicio(event.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Alta até</label>
          <input
            type="date"
            value={filtroDataAltaFim}
            onChange={(event) => onChangeDataAltaFim(event.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Pessoa (tutor)</label>
          <select
            value={filtroPessoaHistorico}
            onChange={(event) => onChangePessoaHistorico(event.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="">Todas</option>
            {pessoas.map((pessoa) => (
              <option key={pessoa.id} value={pessoa.id}>
                {pessoa.nome}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Pet</label>
          <select
            value={filtroPetHistorico}
            onChange={(event) => onChangePetHistorico(event.target.value)}
            disabled={!filtroPessoaHistorico}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white disabled:opacity-60"
          >
            <option value="">Todos</option>
            {petsHistoricoDaPessoa.map((pet) => (
              <option key={pet.id} value={pet.id}>
                {pet.nome}
                {pet.especie ? ` (${pet.especie})` : ""}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
