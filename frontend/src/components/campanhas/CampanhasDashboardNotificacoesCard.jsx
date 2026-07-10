import {
  BellRing,
  CalendarClock,
  Gift,
  PackageCheck,
  Smartphone,
  Sparkles,
  Trophy,
} from "lucide-react";

const NOTIFICACOES_APP = [
  {
    title: "Produto voltou ao estoque",
    detail: "Push, central, badge e clique no produto",
    icon: PackageCheck,
    tone: "emerald",
  },
  {
    title: "Agendamentos",
    detail: "Banho & Tosa e Veterinario",
    icon: CalendarClock,
    tone: "cyan",
  },
  {
    title: "Aniversarios",
    detail: "Cliente e pet com cupom/brinde",
    icon: Gift,
    tone: "rose",
  },
  {
    title: "Campanhas automaticas",
    detail: "Boas-vindas, inatividade, cashback e recompra",
    icon: Sparkles,
    tone: "amber",
  },
  {
    title: "Ranking e premios",
    detail: "Nivel, lote, destaque e sorteios",
    icon: Trophy,
    tone: "amber",
  },
];

const TONE_CLASSES = {
  amber: "bg-amber-50 text-amber-700 border-amber-200",
  cyan: "bg-cyan-50 text-cyan-700 border-cyan-200",
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rose: "bg-rose-50 text-rose-700 border-rose-200",
};

export default function CampanhasDashboardNotificacoesCard() {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BellRing className="text-cyan-700" size={20} aria-hidden="true" />
            <h2 className="text-lg font-semibold text-gray-900">Notificacoes no app</h2>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Push e central do cliente usando o padrao novo.
          </p>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
          <Smartphone size={14} aria-hidden="true" />
          App + central
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {NOTIFICACOES_APP.map(({ title, detail, icon: Icon, tone }) => (
          <div key={title} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-start gap-3">
              <span className={`rounded-lg border p-2 ${TONE_CLASSES[tone]}`}>
                <Icon size={18} aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="font-semibold text-gray-900">{title}</p>
                <p className="mt-1 text-sm text-gray-500">{detail}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
