export default function DashboardKpiGrid({ cards }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 xl:gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.label}
            className={`bg-gradient-to-br ${card.cor} rounded-xl p-3 text-white shadow-sm sm:p-4`}
          >
            <div className="flex items-center justify-between mb-2">
              <Icon size={20} className="opacity-80" />
            </div>
            <p className="text-2xl font-bold sm:text-3xl">{card.valor}</p>
            <p className="mt-1 text-xs opacity-80">{card.label}</p>
          </div>
        );
      })}
    </div>
  );
}
