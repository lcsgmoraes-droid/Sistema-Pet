import { formatarData } from "./petDetalhesUtils";

function VaccineMetric({ label, tone, value }) {
  const tones = {
    default: "border-gray-200 bg-white text-gray-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    rose: "border-rose-200 bg-rose-50 text-rose-900",
  };

  return (
    <div className={`rounded-xl border p-4 ${tones[tone]}`}>
      <p className={`text-xs uppercase tracking-wide ${tone === "default" ? "text-gray-500" : ""}`}>
        {label}
      </p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

export default function PetDetalhesVacinasTab({
  carteirinha,
  filtroVacinas,
  limiteVacinas,
  loadingVacinas,
  onLoadMore,
  onRegistrarVacina,
  setFiltroVacinas,
  vacinasFiltradas,
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">Carteira de VacinaÃ§Ã£o</h2>
        <button
          onClick={onRegistrarVacina}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
        >
          + Registrar Vacina
        </button>
      </div>

      <div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <VaccineMetric
            label="Aplicadas"
            tone="default"
            value={carteirinha?.status_vacinal?.resumo?.total_aplicadas ?? vacinasFiltradas.length}
          />
          <VaccineMetric
            label="Pendentes"
            tone="amber"
            value={carteirinha?.status_vacinal?.resumo?.total_pendentes ?? 0}
          />
          <VaccineMetric
            label="Atrasadas"
            tone="rose"
            value={carteirinha?.status_vacinal?.resumo?.total_vencidas ?? 0}
          />
        </div>

        {Array.isArray(carteirinha?.status_vacinal?.pendentes) &&
          carteirinha.status_vacinal.pendentes.length > 0 && (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <h3 className="text-sm font-semibold text-amber-900 mb-2">Protocolos pendentes</h3>
              <div className="flex flex-wrap gap-2">
                {carteirinha.status_vacinal.pendentes.map((item) => (
                  <span
                    key={`pendente_${item.nome}`}
                    className="px-3 py-1 rounded-full bg-white border border-amber-200 text-sm text-amber-900"
                  >
                    {item.nome}
                  </span>
                ))}
              </div>
            </div>
          )}

        <input
          type="text"
          value={filtroVacinas}
          onChange={(e) => setFiltroVacinas(e.target.value)}
          placeholder="Filtrar por vacina, fabricante, lote ou veterinÃ¡rio..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
      </div>

      {loadingVacinas ? (
        <div className="text-center py-10 text-gray-500">Carregando histÃ³rico de vacinas...</div>
      ) : vacinasFiltradas.length === 0 ? (
        <div className="text-center py-12 text-gray-500 border border-gray-200 rounded-lg bg-gray-50">
          Nenhuma vacina encontrada com esse filtro.
        </div>
      ) : (
        <div className="space-y-3">
          {vacinasFiltradas.slice(0, limiteVacinas).map((vacina) => (
            <div key={vacina.id} className="border border-gray-200 rounded-lg p-4 bg-white">
              <div className="flex items-center justify-between gap-3 mb-1">
                <p className="font-semibold text-gray-800">{vacina.nome_vacina || "Vacina"}</p>
                <p className="text-xs text-gray-500">{formatarData(vacina.data_aplicacao)}</p>
              </div>
              <p className="text-sm text-gray-600">Fabricante: {vacina.fabricante || "-"}</p>
              <p className="text-sm text-gray-600">Lote: {vacina.lote || "-"}</p>
              <p className="text-sm text-gray-600">
                PrÃ³xima dose: {formatarData(vacina.proxima_dose || vacina.data_proxima_dose)}
              </p>
              <p className="text-sm text-gray-600">
                VeterinÃ¡rio: {vacina.veterinario_responsavel || vacina.veterinario_nome || "-"}
              </p>
              {vacina.observacoes && (
                <p className="text-sm text-gray-700 mt-1">Obs.: {vacina.observacoes}</p>
              )}
            </div>
          ))}

          {vacinasFiltradas.length > limiteVacinas && (
            <div className="pt-1">
              <button
                onClick={onLoadMore}
                className="text-sm text-blue-600 hover:text-blue-700 underline"
              >
                Ver mais vacinas ({vacinasFiltradas.length - limiteVacinas} restantes)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
