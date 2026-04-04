export default function CampanhasRankingDistribuicao({ rankLabels, ranking }) {
  if (!ranking?.distribuicao) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {["bronze", "silver", "gold", "diamond", "platinum"].map((nivel) => {
        const rankLabel = rankLabels[nivel];
        const quantidade = ranking.distribuicao[nivel] || 0;
        return (
          <div
            key={nivel}
            className={`rounded-xl border p-3 text-center ${rankLabel.color} ${rankLabel.border}`}
          >
            <p className="text-2xl">{rankLabel.emoji}</p>
            <p className="font-bold text-lg">{quantidade}</p>
            <p className="text-xs font-medium">{rankLabel.label}</p>
          </div>
        );
      })}
    </div>
  );
}
