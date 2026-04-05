import CampanhasRankingCuponsFiltrosBar from "./CampanhasRankingCuponsFiltrosBar";
import CampanhasRankingCuponsTable from "./CampanhasRankingCuponsTable";

const CUPOM_STATUS_OPTIONS = ["active", "used", "expired", "voided", "todos"];

const CUPOM_STATUS_LABELS = {
  active: "Ativos",
  used: "Usados",
  expired: "Expirados",
  voided: "Cancelados",
  todos: "Todos",
};

export default function CampanhasRankingCuponsSection({
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
  filtroCupomStatus,
  setFiltroCupomStatus,
  loadingCupons,
  cupons,
  cupomStatus,
  cupomDetalhes,
  setCupomDetalhes,
  anularCupom,
  anulando,
  formatarValorCupom,
}) {
  return (
    <>
      <CampanhasRankingCuponsFiltrosBar
        campanhas={campanhas}
        filtroCupomBusca={filtroCupomBusca}
        setFiltroCupomBusca={setFiltroCupomBusca}
        filtroCupomDataInicio={filtroCupomDataInicio}
        setFiltroCupomDataInicio={setFiltroCupomDataInicio}
        filtroCupomDataFim={filtroCupomDataFim}
        setFiltroCupomDataFim={setFiltroCupomDataFim}
        filtroCupomCampanha={filtroCupomCampanha}
        setFiltroCupomCampanha={setFiltroCupomCampanha}
        carregarCupons={carregarCupons}
      />

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between flex-wrap gap-2">
          <h2 className="font-semibold text-gray-800">Cupons gerados</h2>
          <div className="flex gap-2 flex-wrap">
            {CUPOM_STATUS_OPTIONS.map((statusFiltro) => (
              <button
                key={statusFiltro}
                onClick={() => setFiltroCupomStatus(statusFiltro)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  filtroCupomStatus === statusFiltro
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {CUPOM_STATUS_LABELS[statusFiltro]}
              </button>
            ))}
          </div>
        </div>

        <CampanhasRankingCuponsTable
          loadingCupons={loadingCupons}
          cupons={cupons}
          cupomStatus={cupomStatus}
          cupomDetalhes={cupomDetalhes}
          setCupomDetalhes={setCupomDetalhes}
          anularCupom={anularCupom}
          anulando={anulando}
          formatarValorCupom={formatarValorCupom}
        />
      </div>
    </>
  );
}
