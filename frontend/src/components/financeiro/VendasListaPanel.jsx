import MetricCard from "../ui/MetricCard";
import MetricGrid from "../ui/MetricGrid";
import VendasFinanceiroListaTable from "./VendasFinanceiroListaTable";

export default function VendasListaPanel({
  abrirVendaNoPdv,
  cardsTotalizadoresLista,
  filtroStatusLista,
  formatarData,
  formatarMoeda,
  getStatusVendaMeta,
  limparFiltroStatusLista,
  listaVendasFiltrada,
  listaVendasVisiveis,
  mostrarImpostoTodasVendas,
  setFiltroStatusLista,
  setMostrarImpostoTodasVendas,
  toggleVendaExpandida,
  vendasExpandidas,
}) {
  return (
    <div className="rounded-lg bg-white shadow">
      <div className="rounded-t-lg bg-gray-600 px-3 py-2 font-semibold text-white sm:px-4">
        Lista de Vendas com Analise de Rentabilidade
      </div>
      <div className="flex flex-col gap-3 border-b border-gray-100 px-3 py-3 lg:flex-row lg:items-center lg:justify-between sm:px-4">
        <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          <button
            type="button"
            onClick={limparFiltroStatusLista}
            className={`w-full rounded-full px-3 py-2 text-sm font-semibold transition sm:w-auto sm:py-1 ${
              filtroStatusLista === ""
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            Todas
          </button>
          <button
            type="button"
            onClick={() => setFiltroStatusLista("em_aberto")}
            className={`w-full rounded-full px-3 py-2 text-sm font-semibold transition sm:w-auto sm:py-1 ${
              filtroStatusLista === "em_aberto"
                ? "bg-red-600 text-white"
                : "bg-red-50 text-red-700 hover:bg-red-100"
            }`}
          >
            Em aberto
          </button>
          <label
            className="col-span-2 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm sm:w-auto sm:py-1"
            title="Marcado: mostra imposto estimado em todas as vendas. Desmarcado: mostra imposto somente em vendas com NF/NFC-e vinculada."
          >
            <input
              type="checkbox"
              checked={mostrarImpostoTodasVendas}
              onChange={(event) => setMostrarImpostoTodasVendas(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            Mostrar TUDO com imposto
          </label>
        </div>
        <div className="text-xs text-slate-500 sm:text-sm">
          Mostrando {listaVendasFiltrada.length} de {listaVendasVisiveis.length} venda(s)
        </div>
      </div>
      <MetricGrid className="border-b border-gray-100 bg-slate-50 px-3 py-3 sm:grid-cols-2 sm:px-4 md:grid-cols-4 xl:grid-cols-8">
        {cardsTotalizadoresLista.map((card) => (
          <MetricCard
            key={card.label}
            intent={card.intent}
            label={card.label}
            size="compact"
            value={card.value}
          />
        ))}
      </MetricGrid>
      <VendasFinanceiroListaTable
        abrirVendaNoPdv={abrirVendaNoPdv}
        formatarData={formatarData}
        formatarMoeda={formatarMoeda}
        getStatusVendaMeta={getStatusVendaMeta}
        onToggleVenda={toggleVendaExpandida}
        vendas={listaVendasFiltrada}
        vendasExpandidas={vendasExpandidas}
      />
    </div>
  );
}
