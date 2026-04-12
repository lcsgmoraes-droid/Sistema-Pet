import CampanhasGestorSection from "./CampanhasGestorSection";

function getRankMeta(rankLabels, rankLevel) {
  return rankLabels[rankLevel] || rankLabels.bronze;
}

export default function CampanhasGestorRankingSection({
  gestorSaldo,
  gestorSecao,
  setGestorSecao,
  rankLabels,
  formatBRL,
}) {
  const isOpen = gestorSecao === "ranking";
  const rank = getRankMeta(rankLabels, gestorSaldo.rank_level);

  return (
    <CampanhasGestorSection
      icon={"\uD83C\uDFC6"}
      title="Ranking"
      subtitle={`${rank.emoji} ${rank.label}${gestorSaldo.rank_period ? ` - ${gestorSaldo.rank_period}` : ""}`}
      isOpen={isOpen}
      onToggle={() => setGestorSecao(isOpen ? null : "ranking")}
    >
      <div className="p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            {
              label: "Nivel",
              value: `${rank.emoji} ${rank.label}`,
            },
            {
              label: "Periodo",
              value: gestorSaldo.rank_period || "-",
            },
            {
              label: "Total Gasto (12m)",
              value: `R$ ${formatBRL(gestorSaldo.rank_total_spent || 0)}`,
            },
            {
              label: "Compras (12m)",
              value: String(gestorSaldo.rank_total_purchases || 0),
            },
          ].map((item) => (
            <div
              key={item.label}
              className="bg-gray-50 rounded-lg p-3 text-center"
            >
              <p className="text-xs text-gray-500 mb-1">{item.label}</p>
              <p className="font-semibold text-gray-800 text-sm">
                {item.value}
              </p>
            </div>
          ))}
        </div>

        <p className="text-xs text-gray-400 mt-4 text-center">
          O nivel de ranking e recalculado automaticamente no dia 1 de cada
          mes.
        </p>
      </div>
    </CampanhasGestorSection>
  );
}
