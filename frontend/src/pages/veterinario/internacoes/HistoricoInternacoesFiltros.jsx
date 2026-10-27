import BuscaPessoa from "../../../components/v2/BuscaPessoa/BuscaPessoa";
import useBuscaEntidadeLocal from "../../../components/v2/BuscaEntidade/useBuscaEntidadeLocal";
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
  const buscaPessoa = useBuscaEntidadeLocal({
    itens: pessoas,
    valueId: filtroPessoaHistorico,
    onChangeId: onChangePessoaHistorico,
    tipo: "pessoa",
  });
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
          <BuscaPessoa {...buscaPessoa} placeholder="Código ou nome do tutor" />
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
