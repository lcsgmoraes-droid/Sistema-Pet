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
    <div className="bg-white rounded-lg shadow">
      <div className="bg-gray-600 text-white px-4 py-2 rounded-t-lg font-semibold">
        Lista de Vendas com Analise de Rentabilidade
      </div>
      <div className="flex flex-col gap-3 border-b border-gray-100 px-4 py-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={limparFiltroStatusLista}
            className={`rounded-full px-3 py-1 text-sm font-semibold transition ${
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
            className={`rounded-full px-3 py-1 text-sm font-semibold transition ${
              filtroStatusLista === "em_aberto"
                ? "bg-red-600 text-white"
                : "bg-red-50 text-red-700 hover:bg-red-100"
            }`}
          >
            Em aberto
          </button>
          <label
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-semibold text-slate-700 shadow-sm"
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
        <div className="text-sm text-slate-500">
          Mostrando {listaVendasFiltrada.length} de {listaVendasVisiveis.length} venda(s)
        </div>
      </div>
      <MetricGrid className="border-b border-gray-100 bg-slate-50 px-4 py-3 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-8">
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
