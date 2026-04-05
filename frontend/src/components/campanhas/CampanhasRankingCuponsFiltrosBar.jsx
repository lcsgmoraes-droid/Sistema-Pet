export default function CampanhasRankingCuponsFiltrosBar({
  campanhas,
  filtroCupomBusca,
  setFiltroCupomBusca,
  filtroCupomDataInicio,
  setFiltroCupomDataInicio,
  filtroCupomDataFim,
  setFiltroCupomDataFim,
  filtroCupomCampanha,
  setFiltroCupomCampanha,
  carregarCupons,
}) {
  const temFiltrosAtivos =
    filtroCupomBusca ||
    filtroCupomDataInicio ||
    filtroCupomDataFim ||
    filtroCupomCampanha;

  return (
    <div className="bg-white rounded-xl border shadow-sm p-4 flex flex-wrap gap-3 items-end">
      <div className="flex-1 min-w-[200px]">
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Busca (codigo ou cliente)
        </label>
        <input
          type="text"
          value={filtroCupomBusca}
          onChange={(e) => setFiltroCupomBusca(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && carregarCupons()}
          placeholder="Ex: ANIV ou Joao Silva"
          className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-300"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Criado a partir de
        </label>
        <input
          type="date"
          value={filtroCupomDataInicio}
          onChange={(e) => setFiltroCupomDataInicio(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Criado ate
        </label>
        <input
          type="date"
          value={filtroCupomDataFim}
          onChange={(e) => setFiltroCupomDataFim(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Campanha
        </label>
        <select
          value={filtroCupomCampanha}
          onChange={(e) => setFiltroCupomCampanha(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Todas as campanhas</option>
          {campanhas.map((campanha) => (
            <option key={campanha.id} value={campanha.id}>
              {campanha.name}
            </option>
          ))}
        </select>
      </div>

      <button
        onClick={carregarCupons}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
      >
        Filtrar
      </button>

      {temFiltrosAtivos && (
        <button
          onClick={() => {
            setFiltroCupomBusca("");
            setFiltroCupomDataInicio("");
            setFiltroCupomDataFim("");
            setFiltroCupomCampanha("");
          }}
          className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 underline"
        >
          Limpar
        </button>
      )}
    </div>
  );
}
