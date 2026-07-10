import { BadgePercent, BellRing, Gift, Megaphone } from "lucide-react";
import { getCampanhasTabLabel } from "./CampanhasTabsBar";

function resumoValor(valor, fallback = "-") {
  if (valor === null || valor === undefined || valor === "") return fallback;
  return valor;
}

export default function CampanhasPageHeader({ aba, dashboard, loadingDashboard }) {
  const abaAtual = getCampanhasTabLabel(aba);
  const campanhasAtivas = dashboard?.campanhas_ativas?.total ?? dashboard?.campanhas_ativas;
  const alertasTotal =
    Number(dashboard?.alertas?.inativos_30d || 0) +
    Number(dashboard?.alertas?.inativos_60d || 0) +
    Number(dashboard?.alertas?.total_sorteios_pendentes || 0);

  const indicadores = [
    {
      label: "Campanhas ativas",
      value: loadingDashboard ? "..." : resumoValor(campanhasAtivas, 0),
      icon: Megaphone,
      className: "text-cyan-700",
    },
    {
      label: "Cupons ativos",
      value: loadingDashboard ? "..." : resumoValor(dashboard?.cupons_ativos_total, 0),
      icon: BadgePercent,
      className: "text-emerald-700",
    },
    {
      label: "Alertas hoje",
      value: loadingDashboard ? "..." : alertasTotal,
      icon: BellRing,
      className: alertasTotal > 0 ? "text-amber-700" : "text-slate-500",
    },
  ];

  return (
    <header className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-800">
            <Gift size={14} aria-hidden="true" />
            Campanhas
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Central de Campanhas</h1>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">
            Fidelidade, cupons, ranking e notificacoes do app em uma visao unica.
          </p>
          {abaAtual && (
            <p className="mt-3 text-xs font-medium uppercase tracking-wide text-gray-400">
              Agora em {abaAtual}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:min-w-[520px]">
          {indicadores.map(({ label, value, icon: Icon, className }) => (
            <div
              key={label}
              className="min-h-[82px] rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-medium text-gray-500">{label}</span>
                <Icon className={className} size={18} aria-hidden="true" />
              </div>
              <p className={`mt-2 text-2xl font-bold ${className}`}>{value}</p>
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}
