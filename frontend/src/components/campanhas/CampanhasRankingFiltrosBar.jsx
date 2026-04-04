export default function CampanhasRankingFiltrosBar({
  rankLabels,
  filtroNivel,
  setFiltroNivel,
  onRecalcularRanking,
}) {
  return (
    <div className="flex gap-2 flex-wrap items-center">
      {["todos", "bronze", "silver", "gold", "diamond", "platinum"].map(
        (nivel) => {
          const rankLabel = nivel === "todos" ? null : rankLabels[nivel];
          return (
            <button
              key={nivel}
              onClick={() => setFiltroNivel(nivel)}
              className={`px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
                filtroNivel === nivel
                  ? rankLabel
                    ? `${rankLabel.color} ${rankLabel.border} border-2`
                    : "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}
            >
              {rankLabel ? `${rankLabel.emoji} ${rankLabel.label}` : "Todos"}
            </button>
          );
        },
      )}
      <button
        onClick={onRecalcularRanking}
        className="ml-auto px-4 py-2 bg-gray-700 text-white rounded-full text-sm font-medium hover:bg-gray-800 transition-colors"
      >
        Recalcular agora
      </button>
    </div>
  );
}
