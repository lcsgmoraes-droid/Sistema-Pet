import { ATALHOS_DASHBOARD_VET } from "./dashboardConfig";

export default function AtalhosRapidos({ onNavigate }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
      {ATALHOS_DASHBOARD_VET.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.path}
            onClick={() => onNavigate(item.path)}
            className="flex min-h-[64px] items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 text-left transition-colors hover:border-blue-300 hover:bg-blue-50"
          >
            <Icon size={18} className="shrink-0 text-blue-500" />
            <span className="min-w-0 text-sm font-medium text-gray-700">{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}
