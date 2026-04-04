import CampanhasDashboardAlertasSection from "./CampanhasDashboardAlertasSection";
import CampanhasDashboardAniversariosCard from "./CampanhasDashboardAniversariosCard";
import CampanhasDashboardMetricasGrid from "./CampanhasDashboardMetricasGrid";
import CampanhasDashboardProximosEventosSection from "./CampanhasDashboardProximosEventosSection";

export default function CampanhasDashboardTab({
  loadingDashboard,
  dashboard,
  onAbrirEnvioInativos,
  onAbrirAba,
}) {
  if (loadingDashboard) {
    return (
      <div className="p-8 text-center text-gray-400">
        Carregando dashboard...
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="p-8 text-center text-gray-400">
        Erro ao carregar dashboard.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <CampanhasDashboardMetricasGrid dashboard={dashboard} />
      <CampanhasDashboardAniversariosCard dashboard={dashboard} />
      <CampanhasDashboardAlertasSection
        dashboard={dashboard}
        onAbrirEnvioInativos={onAbrirEnvioInativos}
        onAbrirAba={onAbrirAba}
      />
      <CampanhasDashboardProximosEventosSection dashboard={dashboard} />
    </div>
  );
}
