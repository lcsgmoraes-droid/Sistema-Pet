import {
  BarChart3,
  Dice5,
  Hourglass,
  LayoutDashboard,
  Link2,
  Megaphone,
  Repeat2,
  Settings,
  SlidersHorizontal,
  Sparkles,
  Tags,
  BadgePercent,
  Trophy,
  Wrench,
} from "lucide-react";

export const CAMPANHAS_TABS = [
  {
    group: "Visao geral",
    items: [
      { id: "dashboard", label: "Dashboard", labelText: "Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    group: "Campanhas",
    description: "Programas que geram desconto, brinde, cupom ou relacionamento.",
    items: [
      { id: "campanhas", label: "Todas", labelText: "Campanhas", icon: Megaphone },
      { id: "validade", label: "Validade", labelText: "Validade", icon: Hourglass },
      { id: "retencao", label: "Retencao", labelText: "Retencao", icon: Repeat2 },
      { id: "destaque", label: "Cliente destaque", labelText: "Cliente Destaque", icon: Sparkles },
      { id: "sorteios", label: "Sorteios", labelText: "Sorteios", icon: Dice5 },
      { id: "ranking", label: "Ranking", labelText: "Ranking", icon: Trophy },
      { id: "cupons", label: "Cupons", labelText: "Cupons e Brindes", icon: BadgePercent },
    ],
  },
  {
    group: "Operacao",
    items: [
      { id: "gestor", label: "Gestor", labelText: "Gestor", icon: Wrench },
      { id: "relatorios", label: "Relatorios", labelText: "Relatorios", icon: BarChart3 },
      { id: "unificacao", label: "Unificacao", labelText: "Unificacao", icon: Link2 },
    ],
  },
  {
    group: "Configuracao",
    items: [
      { id: "config", label: "Configuracoes", labelText: "Configuracoes", icon: Settings },
      { id: "canais", label: "Canais", labelText: "Descontos por Canal", icon: Tags },
    ],
  },
];

const FLAT_TABS = CAMPANHAS_TABS.flatMap((group) => group.items);

function TabButton({ active, tab, onChange }) {
  const Icon = tab.icon || SlidersHorizontal;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={() => onChange?.(tab.id)}
      className={[
        "flex min-h-[48px] min-w-0 items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm font-semibold leading-tight transition-colors",
        active
          ? "border-cyan-300 bg-cyan-50 text-cyan-800 shadow-sm"
          : "border-slate-200 bg-white text-gray-600 hover:border-slate-300 hover:bg-slate-50 hover:text-gray-900",
      ].join(" ")}
    >
      <Icon size={17} className="shrink-0" aria-hidden="true" />
      <span className="min-w-0 break-words">{tab.label}</span>
    </button>
  );
}

export default function CampanhasTabsBar({ aba, onChange }) {
  return (
    <nav
      aria-label="Abas de campanhas"
      className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
    >
      <div role="tablist" aria-label="Abas de campanhas" className="space-y-3">
        {CAMPANHAS_TABS.map((group) => (
          <div key={group.group} className="grid gap-2 md:grid-cols-[150px_1fr] md:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                {group.group}
              </p>
              {group.description && (
                <p className="mt-1 hidden text-xs leading-snug text-gray-400 lg:block">
                  {group.description}
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {group.items.map((tab) => (
                <TabButton key={tab.id} active={aba === tab.id} tab={tab} onChange={onChange} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </nav>
  );
}

export function getCampanhasTabLabel(id) {
  return FLAT_TABS.find((tab) => tab.id === id)?.labelText || id;
}
