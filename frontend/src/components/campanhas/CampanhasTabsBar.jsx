const CAMPANHAS_TABS = [
  { id: "dashboard", label: "📊 Dashboard" },
  { id: "campanhas", label: "📋 Campanhas" },
  { id: "retencao", label: "🔄 Retenção" },
  { id: "destaque", label: "🌟 Destaque Mensal" },
  { id: "sorteios", label: "🎲 Sorteios" },
  { id: "ranking", label: "🏆 Ranking" },
  { id: "cupons", label: "🎟️ Cupons" },
  { id: "unificacao", label: "🔗 Unificação" },
  { id: "relatorios", label: "📈 Relatórios" },
  { id: "gestor", label: "🛠️ Gestor" },
  { id: "config", label: "⚙️ Configurações" },
  { id: "canais", label: "🏷️ Descontos por Canal" },
];

export default function CampanhasTabsBar({ aba, onChange }) {
  return (
    <div className="flex gap-1 border-b overflow-x-auto">
      {CAMPANHAS_TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`px-5 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors whitespace-nowrap ${
            aba === tab.id
              ? "border-blue-600 text-blue-700 bg-blue-50"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
