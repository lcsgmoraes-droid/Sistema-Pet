import { formatBRL } from "../../utils/formatters";

function DashboardMetricCard({
  value,
  label,
  className = "text-blue-700",
  extra,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-4 text-center">
      <p className={`text-3xl font-bold ${className}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
      {extra}
    </div>
  );
}

export default function CampanhasDashboardMetricasGrid({ dashboard }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      <DashboardMetricCard
        value={dashboard.campanhas_ativas?.total ?? dashboard.campanhas_ativas}
        label={"\uD83D\uDCE2 Campanhas ativas"}
        extra={
          dashboard.campanhas_ativas?.nomes?.length > 0 ? (
            <div className="mt-2 text-left space-y-0.5">
              {dashboard.campanhas_ativas.nomes.map((nome, i) => (
                <p key={i} className="text-xs text-gray-600 truncate">
                  - {nome}
                </p>
              ))}
            </div>
          ) : null
        }
      />
      <DashboardMetricCard
        value={dashboard.cupons_emitidos_hoje}
        label={"\uD83C\uDF9F\uFE0F Cupons emitidos hoje"}
        className="text-green-700"
      />
      <DashboardMetricCard
        value={dashboard.cupons_usados_hoje}
        label={"\u2705 Cupons usados hoje"}
        className="text-orange-700"
      />
      <DashboardMetricCard
        value={`R$ ${formatBRL(dashboard.saldo_passivo_cashback || 0)}`}
        label={"\uD83D\uDCB0 Saldo passivo (cashback)"}
        className="text-2xl text-purple-700"
      />
      <div
        className={`rounded-xl border shadow-sm p-4 text-center ${
          dashboard.proximos_eventos?.dias_ate_fim_mes <= 3
            ? "bg-yellow-50 border-yellow-300"
            : "bg-white"
        }`}
      >
        <p
          className={`text-3xl font-bold ${
            dashboard.proximos_eventos?.dias_ate_fim_mes <= 3
              ? "text-yellow-700"
              : "text-indigo-700"
          }`}
        >
          {dashboard.proximos_eventos?.dias_ate_fim_mes ?? "-"}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {"\u{1F31F}"}{" "}
          {dashboard.proximos_eventos?.dias_ate_fim_mes === 0
            ? "Ultimo dia - calcule o destaque!"
            : "dia(s) p/ Destaque Mensal"}
        </p>
      </div>
      {(dashboard.cupons_expirados_hoje ?? 0) > 0 && (
        <div className="bg-red-50 rounded-xl border border-red-200 shadow-sm p-4 text-center">
          <p className="text-3xl font-bold text-red-700">
            {dashboard.cupons_expirados_hoje}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {"\u23F0"} Cupons expiram hoje
          </p>
        </div>
      )}
      <DashboardMetricCard
        value={dashboard.cupons_ativos_total ?? 0}
        label={"\uD83D\uDCE6 Cupons ativos no total"}
        className="text-teal-700"
      />
    </div>
  );
}
