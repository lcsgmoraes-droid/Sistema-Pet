export default function DashboardKpiGrid({ cards }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.label}
            className={`bg-gradient-to-br ${card.cor} rounded-xl p-4 text-white shadow-sm`}
          >
            <div className="flex items-center justify-between mb-2">
              <Icon size={20} className="opacity-80" />
            </div>
            <p className="text-3xl font-bold">{card.valor}</p>
            <p className="text-xs opacity-80 mt-1">{card.label}</p>
          </div>
        );
      })}
    </div>
  );
}
