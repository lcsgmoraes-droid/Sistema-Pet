import BanhoTosaDefaultsPanel from "./BanhoTosaDefaultsPanel";
import BanhoTosaMetricCard from "./BanhoTosaMetricCard";
import BanhoTosaSimulador from "./BanhoTosaSimulador";

export default function BanhoTosaDashboardView({
  dashboard,
  config,
  parametros,
  onChanged,
}) {
  const parametrosAtivos = parametros.filter((item) => item.ativo).length;

  return (
    <div className="space-y-6">
      <BanhoTosaDefaultsPanel onApplied={onChanged} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <BanhoTosaMetricCard
          label="Agenda do dia"
          value={dashboard?.agendamentos_abertos}
          detail="Agendamentos ainda nao finalizados"
          tone="amber"
        />
        <BanhoTosaMetricCard
          label="Em execucao"
          value={dashboard?.atendimentos_em_execucao}
          detail="Pets em banho, secagem ou tosa"
          tone="sky"
        />
        <BanhoTosaMetricCard
          label="Prontos"
          value={dashboard?.atendimentos_prontos}
          detail="Aguardando retirada ou taxi dog"
          tone="emerald"
        />
        <BanhoTosaMetricCard
          label="Entregues hoje"
          value={dashboard?.atendimentos_entregues}
          detail="Atendimentos encerrados no dia"
          tone="slate"
        />
        <BanhoTosaMetricCard
          label="Sem venda"
          value={dashboard?.atendimentos_prontos_sem_venda}
          detail="Prontos aguardando envio ao PDV"
          tone="amber"
        />
        <BanhoTosaMetricCard
          label="Cobranca pend."
          value={dashboard?.cobrancas_pendentes}
          detail="Prontos/entregues com venda aberta"
          tone="amber"
        />
        <BanhoTosaMetricCard
          label="NPS hoje"
          value={formatNps(dashboard?.nps_hoje)}
          detail={`${dashboard?.avaliacoes_hoje || 0} avaliacao(es)`}
          tone="emerald"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
                Fluxo operacional
              </p>
              <h2 className="mt-2 text-xl font-black text-slate-900">
                Da agenda ao custo real por atendimento
              </h2>
            </div>
            <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-bold text-white">
              MVP controlado
            </span>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-4">
            {[
              "Agendado",
              "Check-in",
              "Banho / Tosa",
              "Pronto / Entregue",
            ].map((etapa, index) => (
              <div
                key={etapa}
                className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-500 text-sm font-black text-white">
                  {index + 1}
                </span>
                <p className="mt-3 font-bold text-slate-900">{etapa}</p>
                <p className="mt-1 text-sm text-slate-500">
                  Cada etapa vai alimentar tempos, consumo, mao de obra e margem.
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Parametrizacao
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-900">
            Base pronta para precificar
          </h2>
          <dl className="mt-5 space-y-4 text-sm">
            <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
              <dt className="text-slate-500">Servicos ativos</dt>
              <dd className="font-black text-slate-900">
                {dashboard?.servicos_ativos ?? 0}
              </dd>
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
              <dt className="text-slate-500">Portes ativos</dt>
              <dd className="font-black text-slate-900">{parametrosAtivos}</dd>
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
              <dt className="text-slate-500">Horario base</dt>
              <dd className="font-black text-slate-900">
                {config?.horario_inicio || "08:00"} - {config?.horario_fim || "18:00"}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <BanhoTosaSimulador config={config} />
    </div>
  );
}

function formatNps(value) {
  const numero = Number(value || 0);
  return Number.isFinite(numero) ? numero.toFixed(0) : "0";
}
