import {
  BarChart3,
  Dice5,
  Hourglass,
  LayoutDashboard,
  Link2,
  Megaphone,
  Repeat2,
  Settings,
  Sparkles,
  Tags,
  BadgePercent,
  Medal,
  Trophy,
  Wrench,
  Wallet,
} from "lucide-react";
import AbasNavegacao from "../v2/AbasNavegacao/AbasNavegacao";

export const CAMPANHAS_TABS = [
  {
    group: "Visao geral",
    items: [{ id: "dashboard", label: "Dashboard", labelText: "Dashboard", icon: LayoutDashboard }],
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
      {
        id: "ranking-clientes",
        label: "Ranking de clientes",
        labelText: "Ranking de clientes",
        icon: Trophy,
      },
      { id: "cupons", label: "Cupons", labelText: "Cupons e Brindes", icon: BadgePercent },
    ],
  },
  {
    group: "Operacao",
    items: [
      {
        id: "cashback-crm",
        label: "Cashback e contatos",
        labelText: "Cashback e contatos",
        icon: Wallet,
      },
      { id: "gestor", label: "Gestor", labelText: "Gestor", icon: Wrench },
      { id: "relatorios", label: "Relatorios", labelText: "Relatorios", icon: BarChart3 },
      { id: "unificacao", label: "Unificacao", labelText: "Unificacao", icon: Link2 },
    ],
  },
  {
    group: "Configuracao",
    items: [
      { id: "ranking", label: "Niveis VIP", labelText: "Niveis VIP", icon: Medal },
      { id: "config", label: "Configuracoes", labelText: "Configuracoes", icon: Settings },
      { id: "canais", label: "Canais", labelText: "Descontos por Canal", icon: Tags },
    ],
  },
];

const FLAT_TABS = CAMPANHAS_TABS.flatMap((group) => group.items);

export default function CampanhasTabsBar({ aba, onChange }) {
  return (
    <nav
      aria-label="Abas de campanhas"
      className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="space-y-3">
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
            <AbasNavegacao
              abas={group.items}
              ativa={aba}
              onChange={onChange}
              ariaLabel={group.group}
              className="flex-wrap border-b-0 pb-0"
            />
          </div>
        ))}
      </div>
    </nav>
  );
}

export function getCampanhasTabLabel(id) {
  return FLAT_TABS.find((tab) => tab.id === id)?.labelText || id;
}
