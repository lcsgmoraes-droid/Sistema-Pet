import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Megaphone,
  PackageCheck,
  BadgePercent,
  WalletCards,
} from "lucide-react";
import { formatBRL } from "../../utils/formatters";

const TONE_CLASSES = {
  cyan: {
    icon: "bg-cyan-50 text-cyan-700 border-cyan-200",
    value: "text-cyan-700",
    bar: "bg-cyan-500",
  },
  emerald: {
    icon: "bg-emerald-50 text-emerald-700 border-emerald-200",
    value: "text-emerald-700",
    bar: "bg-emerald-500",
  },
  amber: {
    icon: "bg-amber-50 text-amber-700 border-amber-200",
    value: "text-amber-700",
    bar: "bg-amber-500",
  },
  violet: {
    icon: "bg-violet-50 text-violet-700 border-violet-200",
    value: "text-violet-700",
    bar: "bg-violet-500",
  },
  rose: {
    icon: "bg-rose-50 text-rose-700 border-rose-200",
    value: "text-rose-700",
    bar: "bg-rose-500",
  },
  slate: {
    icon: "bg-slate-50 text-slate-700 border-slate-200",
    value: "text-slate-700",
    bar: "bg-slate-400",
  },
};

function DashboardMetricCard({ value, label, detail, icon: Icon, tone = "cyan", children }) {
  const classes = TONE_CLASSES[tone] || TONE_CLASSES.cyan;

  return (
    <article className="relative min-h-[142px] overflow-hidden rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <span className={`absolute inset-x-0 top-0 h-1 ${classes.bar}`} />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</p>
          <p className={`mt-2 text-3xl font-bold ${classes.value}`}>{value}</p>
        </div>
        <span className={`rounded-lg border p-2 ${classes.icon}`}>
          <Icon size={20} aria-hidden="true" />
        </span>
      </div>
      {detail && <p className="mt-2 text-sm text-gray-500">{detail}</p>}
      {children}
    </article>
  );
}

export default function CampanhasDashboardMetricasGrid({ dashboard }) {
  const campanhasAtivas = dashboard.campanhas_ativas?.total ?? dashboard.campanhas_ativas;
  const nomesCampanhas = dashboard.campanhas_ativas?.nomes || [];
  const diasDestaque = dashboard.proximos_eventos?.dias_ate_fim_mes;
  const cuponsExpirados = dashboard.cupons_expirados_hoje ?? 0;

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Resumo de hoje</h2>
          <p className="text-sm text-gray-500">Indicadores principais das campanhas ativas.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <DashboardMetricCard
          value={campanhasAtivas ?? 0}
          label="Campanhas ativas"
          detail="Programas rodando agora"
          icon={Megaphone}
          tone="cyan"
        >
          {nomesCampanhas.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {nomesCampanhas.slice(0, 3).map((nome, index) => (
                <span
                  key={`${nome}-${index}`}
                  className="max-w-full truncate rounded-md bg-slate-100 px-2 py-1 text-xs text-gray-600"
                >
                  {nome}
                </span>
              ))}
              {nomesCampanhas.length > 3 && (
                <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-gray-500">
                  +{nomesCampanhas.length - 3}
                </span>
              )}
            </div>
          )}
        </DashboardMetricCard>

        <DashboardMetricCard
          value={dashboard.cupons_emitidos_hoje ?? 0}
          label="Cupons emitidos"
          detail={`${dashboard.cupons_usados_hoje ?? 0} usados hoje`}
          icon={BadgePercent}
          tone="emerald"
        />

        <DashboardMetricCard
          value={`R$ ${formatBRL(dashboard.saldo_passivo_cashback || 0)}`}
          label="Cashback em aberto"
          detail="Saldo ainda nao resgatado"
          icon={WalletCards}
          tone="violet"
        />

        <DashboardMetricCard
          value={cuponsExpirados}
          label="Cupons vencendo"
          detail={cuponsExpirados > 0 ? "Pedem atencao hoje" : "Sem vencimento critico"}
          icon={cuponsExpirados > 0 ? AlertTriangle : CheckCircle2}
          tone={cuponsExpirados > 0 ? "rose" : "slate"}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <DashboardMetricCard
          value={dashboard.cupons_ativos_total ?? 0}
          label="Cupons ativos no total"
          detail="Disponiveis para clientes"
          icon={PackageCheck}
          tone="amber"
        />
        <DashboardMetricCard
          value={diasDestaque ?? "-"}
          label="Destaque mensal"
          detail={diasDestaque === 0 ? "Ultimo dia para calcular" : "dias ate o fechamento do mes"}
          icon={CalendarClock}
          tone={Number(diasDestaque) <= 3 ? "amber" : "cyan"}
        />
      </div>
    </section>
  );
}
