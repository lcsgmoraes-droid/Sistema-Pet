import BuscaPessoa from "../../../components/v2/BuscaPessoa/BuscaPessoa";

const PERIODOS = [
  { id: "hoje", label: "Hoje" },
  { id: "semana", label: "Semana" },
  { id: "periodo", label: "Período" },
];

export default function ExamesAnexadosFiltros({
  periodo,
  dataInicio,
  dataFim,
  tutorBusca,
  carregando,
  onChangePeriodo,
  onChangeDataInicio,
  onChangeDataFim,
  onChangeTutorBusca,
  onAplicar,
  onLimpar,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <div className="flex flex-wrap gap-2">
        {PERIODOS.map((opcao) => (
          <button
            key={opcao.id}
            type="button"
            onClick={() => onChangePeriodo(opcao.id)}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              periodo === opcao.id
                ? "bg-orange-500 text-white border-orange-500"
                : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            }`}
          >
            {opcao.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="md:col-span-2">
          <label className="block text-xs font-medium text-gray-600 mb-1">Tutor (nome)</label>
          <div className="relative">
            <BuscaPessoa
              value={tutorBusca}
              onChange={(valor) => onChangeTutorBusca(valor)}
              placeholder="Digite o nome do tutor..."
              showSuggestions={false}
            />
          </div>
        </div>

        {periodo === "periodo" && (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Data início</label>
              <input
                type="date"
                value={dataInicio}
                onChange={(event) => onChangeDataInicio(event.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Data fim</label>
              <input
                type="date"
                value={dataFim}
                onChange={(event) => onChangeDataFim(event.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-300"
              />
            </div>
          </>
        )}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onAplicar}
          disabled={carregando}
          className="px-4 py-2 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-60"
        >
          {carregando ? "Carregando..." : "Aplicar filtros"}
        </button>
        <button
          type="button"
          onClick={onLimpar}
          className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          Limpar
        </button>
      </div>
    </div>
  );
}
