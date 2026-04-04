const CAMPANHAS_TABS = [
  { id: "dashboard", label: "\u{1F4CA} Dashboard" },
  { id: "campanhas", label: "\u{1F4CB} Campanhas" },
  { id: "retencao", label: "\u{1F504} Retencao" },
  { id: "destaque", label: "\u{1F31F} Destaque Mensal" },
  { id: "sorteios", label: "\u{1F3B2} Sorteios" },
  { id: "ranking", label: "\u{1F3C6} Ranking" },
  { id: "cupons", label: "\u{1F39F}\uFE0F Cupons" },
  { id: "unificacao", label: "\u{1F517} Unificacao" },
  { id: "relatorios", label: "\u{1F4C8} Relatorios" },
  { id: "gestor", label: "\u{1F6E0}\uFE0F Gestor" },
  { id: "config", label: "\u2699\uFE0F Configuracoes" },
  { id: "canais", label: "\u{1F3F7}\uFE0F Descontos por Canal" },
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
