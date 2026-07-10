import { BadgePercent, Gift, ShieldCheck, Ticket } from "lucide-react";
import CampanhasRankingCuponsSection from "./CampanhasRankingCuponsSection";

function ResumoCupom({ label, value, detail, icon: Icon, tone }) {
  const toneClasses = {
    blue: "bg-blue-50 text-blue-700 border-blue-100",
    green: "bg-emerald-50 text-emerald-700 border-emerald-100",
    amber: "bg-amber-50 text-amber-700 border-amber-100",
    slate: "bg-slate-50 text-slate-700 border-slate-100",
  };

  return (
    <div className={`rounded-lg border p-4 ${toneClasses[tone] || toneClasses.slate}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide opacity-75">{label}</p>
          <p className="mt-1 text-2xl font-bold">{value}</p>
        </div>
        <Icon className="h-5 w-5 opacity-70" aria-hidden="true" />
      </div>
      <p className="mt-2 text-xs opacity-80">{detail}</p>
    </div>
  );
}

export default function CampanhasCuponsTab(props) {
  const cupons = props.cupons || [];
  const total = cupons.length;
  const ativos = cupons.filter((cupom) => cupom.status === "active").length;
  const usados = cupons.filter((cupom) => cupom.status === "used").length;
  const brindes = cupons.filter((cupom) => cupom.coupon_type === "gift").length;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-blue-700">
              <BadgePercent className="h-4 w-4" aria-hidden="true" />
              Auditoria de beneficios
            </div>
            <h2 className="text-xl font-bold text-slate-900">Cupons e brindes de campanhas</h2>
            <p className="mt-1 text-sm text-slate-500">
              Acompanhe o que foi emitido por aniversario, ranking, sorteios, destaque mensal,
              cashback e acoes manuais.
            </p>
          </div>

          <div className="grid min-w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:min-w-[520px] lg:grid-cols-4">
            <ResumoCupom
              label="Total"
              value={total}
              detail="No filtro atual"
              icon={BadgePercent}
              tone="blue"
            />
            <ResumoCupom
              label="Ativos"
              value={ativos}
              detail="Podem ser usados"
              icon={ShieldCheck}
              tone="green"
            />
            <ResumoCupom
              label="Usados"
              value={usados}
              detail="Ja resgatados"
              icon={Ticket}
              tone="slate"
            />
            <ResumoCupom
              label="Brindes"
              value={brindes}
              detail="Premios e mimos"
              icon={Gift}
              tone="amber"
            />
          </div>
        </div>
      </div>

      <CampanhasRankingCuponsSection {...props} />
    </div>
  );
}
