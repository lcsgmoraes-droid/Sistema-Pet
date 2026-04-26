import { ATALHOS_DASHBOARD_VET } from "./dashboardConfig";

export default function AtalhosRapidos({ onNavigate }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {ATALHOS_DASHBOARD_VET.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.path}
            onClick={() => onNavigate(item.path)}
            className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-colors text-left"
          >
            <Icon size={18} className="text-blue-500" />
            <span className="text-sm font-medium text-gray-700">{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}
