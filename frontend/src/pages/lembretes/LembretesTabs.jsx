import { FiBarChart2, FiCalendar, FiRepeat, FiUsers } from "react-icons/fi";

const tabs = [
  { id: "recompras", label: "Recompras", icon: FiRepeat, count: "lembretes" },
  { id: "validade", label: "Validade", icon: FiCalendar, count: "validadePendencias" },
  { id: "relacionamento", label: "Relacionamento", icon: FiUsers },
  { id: "relatorios", label: "Histórico e relatórios", icon: FiBarChart2 },
];

export default function LembretesTabs({ controller }) {
  return (
    <nav
      aria-label="Áreas da central de lembretes"
      className="lembretes-tabs mb-5 overflow-x-auto border-b border-slate-200 dark:border-slate-700"
    >
      <div className="flex min-w-max gap-1" role="tablist">
        {tabs.map(({ count, icon: Icon, id, label }) => {
          const active = controller.abaAtiva === id;
          const total = count ? controller[count].length : null;
          return (
            <button
              aria-selected={active}
              className={`inline-flex items-center gap-2 border-b-2 px-3 py-3 text-sm font-semibold transition sm:px-4 ${
                active
                  ? "border-teal-600 text-teal-700 dark:text-teal-300"
                  : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
              key={id}
              onClick={() => controller.setAbaAtiva(id)}
              role="tab"
              type="button"
            >
              <Icon aria-hidden="true" />
              {label}
              {total != null && (
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    active
                      ? "bg-teal-50 text-teal-700 dark:bg-teal-500/10 dark:text-teal-200"
                      : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                  }`}
                >
                  {total}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
