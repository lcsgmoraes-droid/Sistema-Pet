import { AlertTriangle, Dice5, Gift, Mail, ShoppingBag } from "lucide-react";
import CustomerIdentity from "../ui/CustomerIdentity";

function AlertaCard({ count, label, icon: Icon, tone, children }) {
  const ativo = Number(count || 0) > 0;
  const toneClasses = {
    amber: ativo
      ? "border-amber-200 bg-amber-50 text-amber-700"
      : "border-slate-200 bg-slate-50 text-slate-400",
    orange: ativo
      ? "border-orange-200 bg-orange-50 text-orange-700"
      : "border-slate-200 bg-slate-50 text-slate-400",
    rose: ativo
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : "border-slate-200 bg-slate-50 text-slate-400",
    slate: ativo
      ? "border-slate-300 bg-slate-100 text-slate-700"
      : "border-slate-200 bg-slate-50 text-slate-400",
  };

  return (
    <article className={`min-h-[148px] rounded-lg border p-4 ${toneClasses[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-3xl font-bold">{count}</p>
          <p className="mt-1 text-sm font-medium text-gray-600">{label}</p>
        </div>
        <span className="rounded-lg border border-current/20 bg-white/60 p-2">
          <Icon size={20} aria-hidden="true" />
        </span>
      </div>
      {children}
    </article>
  );
}

export default function CampanhasDashboardAlertasSection({
  dashboard,
  onAbrirEnvioInativos,
  onAbrirAba,
}) {
  if (!dashboard.alertas) return null;

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Alertas do dia</h2>
        <p className="text-sm text-gray-500">Pontos que pedem acao operacional.</p>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {[
          {
            dias: 30,
            count: dashboard.alertas.inativos_30d,
            label: "Clientes sem compra ha +30 dias",
            tone: "orange",
            icon: ShoppingBag,
          },
          {
            dias: 60,
            count: dashboard.alertas.inativos_60d,
            label: "Clientes sem compra ha +60 dias",
            tone: "rose",
            icon: AlertTriangle,
          },
        ].map(({ dias, count, label, tone, icon }) => (
          <AlertaCard key={dias} count={count} label={label} tone={tone} icon={icon}>
            {count > 0 && (
              <button
                onClick={() => onAbrirEnvioInativos(dias)}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-orange-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-orange-700"
              >
                <Mail size={14} aria-hidden="true" />
                Enviar reativacao
              </button>
            )}
          </AlertaCard>
        ))}

        <AlertaCard
          count={dashboard.alertas.total_sorteios_pendentes}
          label="Sorteios nao executados"
          tone="amber"
          icon={Dice5}
        />
      </div>

      {dashboard.alertas.sorteios_pendentes?.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-amber-50 px-5 py-3">
            <p className="text-sm font-semibold text-amber-900">Sorteios pendentes</p>
            <button
              onClick={() => onAbrirAba("sorteios")}
              className="text-xs font-semibold text-amber-800 hover:underline"
            >
              Ver todos
            </button>
          </div>
          <div className="divide-y divide-slate-200">
            {dashboard.alertas.sorteios_pendentes.map((sorteio) => (
              <div key={sorteio.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">{sorteio.name}</p>
                  <p className="text-xs text-gray-500">
                    Status: {sorteio.status}
                    {sorteio.draw_date
                      ? ` - Data: ${new Date(sorteio.draw_date).toLocaleDateString("pt-BR")}`
                      : ""}
                  </p>
                </div>
                <button
                  onClick={() => onAbrirAba("sorteios")}
                  className="shrink-0 text-xs font-semibold text-cyan-700 hover:underline"
                >
                  Abrir
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {dashboard.alertas?.total_brindes_pendentes > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-amber-50 px-5 py-3">
            <div className="flex items-center gap-2">
              <Gift className="text-amber-800" size={18} aria-hidden="true" />
              <p className="text-sm font-semibold text-amber-900">
                Brindes pendentes de retirada ({dashboard.alertas.total_brindes_pendentes})
              </p>
            </div>
            <button
              onClick={() => onAbrirAba("cupons")}
              className="text-xs font-semibold text-amber-800 hover:underline"
            >
              Ver cupons
            </button>
          </div>
          <div className="divide-y divide-slate-200">
            {dashboard.alertas.brindes_pendentes.slice(0, 5).map((brinde, index) => (
              <div key={index} className="flex items-start justify-between gap-3 px-5 py-3">
                <div className="min-w-0 flex-1">
                  <CustomerIdentity
                    code={brinde.customer_id}
                    fallback="Cliente nao informado"
                    name={brinde.nome_cliente}
                    nameClassName="font-medium text-gray-900"
                    record={brinde}
                  />
                  <p className="text-xs text-gray-500">
                    {brinde.categoria === "maior_gasto"
                      ? "Maior gasto"
                      : brinde.categoria === "mais_compras"
                        ? "Mais compras"
                        : brinde.categoria}
                    {brinde.periodo ? ` - ${brinde.periodo}` : ""}
                  </p>
                  {brinde.mensagem && (
                    <p className="mt-0.5 truncate text-xs text-amber-700">{brinde.mensagem}</p>
                  )}
                </div>
                {brinde.retirar_ate && (
                  <span className="shrink-0 text-xs text-gray-400">
                    ate {new Date(brinde.retirar_ate).toLocaleDateString("pt-BR")}
                  </span>
                )}
              </div>
            ))}
            {dashboard.alertas.total_brindes_pendentes > 5 && (
              <div className="px-5 py-2 text-center text-xs text-gray-400">
                +{dashboard.alertas.total_brindes_pendentes - 5} mais
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
