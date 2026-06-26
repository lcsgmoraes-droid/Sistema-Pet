import { formatarDataHora } from "./petDetalhesUtils";

export default function PetDetalhesConsultasTab({
  consultasFiltradas,
  filtroConsultas,
  limiteConsultas,
  loadingConsultas,
  onAbrirConsulta,
  onLoadMore,
  onNovaConsulta,
  setFiltroConsultas,
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">HistÃ³rico de Consultas</h2>
        <button
          onClick={onNovaConsulta}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
        >
          + Nova Consulta
        </button>
      </div>

      <input
        type="text"
        value={filtroConsultas}
        onChange={(e) => setFiltroConsultas(e.target.value)}
        placeholder="Filtrar por motivo, diagnÃ³stico, veterinÃ¡rio ou status..."
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
      />

      {loadingConsultas ? (
        <div className="text-center py-10 text-gray-500">Carregando histÃ³rico de consultas...</div>
      ) : consultasFiltradas.length === 0 ? (
        <div className="text-center py-12 text-gray-500 border border-gray-200 rounded-lg bg-gray-50">
          Nenhuma consulta encontrada com esse filtro.
        </div>
      ) : (
        <div className="space-y-3">
          {consultasFiltradas.slice(0, limiteConsultas).map((consulta) => (
            <div key={consulta.id} className="border border-gray-200 rounded-lg p-4 bg-white">
              <div className="flex items-center justify-between gap-3 mb-1">
                <p className="font-semibold text-gray-800">
                  {consulta.queixa_principal || consulta.motivo_consulta || "Consulta veterinÃ¡ria"}
                </p>
                <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                  {consulta.status || "registrada"}
                </span>
              </div>
              <p className="text-sm text-gray-600">
                Data: {formatarDataHora(consulta.inicio_atendimento || consulta.created_at)}
              </p>
              <p className="text-sm text-gray-600">
                VeterinÃ¡rio: {consulta.veterinario_nome || "-"}
              </p>
              <p className="text-sm text-gray-700 mt-1">
                DiagnÃ³stico: {consulta.diagnostico || "-"}
              </p>
              <div className="mt-2">
                <button
                  onClick={() => onAbrirConsulta(consulta.id)}
                  className="text-sm text-blue-600 hover:text-blue-700 underline"
                >
                  Abrir consulta completa
                </button>
              </div>
            </div>
          ))}

          {consultasFiltradas.length > limiteConsultas && (
            <div className="pt-1">
              <button
                onClick={onLoadMore}
                className="text-sm text-blue-600 hover:text-blue-700 underline"
              >
                Ver mais consultas ({consultasFiltradas.length - limiteConsultas} restantes)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
