import { FiActivity, FiClock, FiShield } from "react-icons/fi";

const JOURNEY_LABELS = {
  "auth.login": "Login",
  "auth.tenant_selection": "Seleção da empresa",
  "sale.finalization": "Finalização de venda",
};

const STATUS_LABELS = {
  no_measurement: "sem medição",
  baseline_low: "amostra pequena",
  measured: "medido",
  healthy: "dentro da meta",
  breached: "fora da meta",
};

function toneClasses(status) {
  if (status === "healthy") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  if (status === "breached") return "border-rose-200 bg-rose-50 text-rose-900";
  if (status === "baseline_low") return "border-amber-200 bg-amber-50 text-amber-900";
  if (status === "measured") return "border-blue-200 bg-blue-50 text-blue-900";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function formatPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${number.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
}

function formatMs(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${number.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} ms`;
}

export default function JourneySloPanel({ journeys }) {
  const items = journeys?.by_journey || [];
  const overall = journeys?.overall || {};

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <FiActivity className="h-5 w-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">Jornadas e SLOs</h2>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Tentativas, sucesso e tempo sem copiar dados de clientes ou vendas.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-lg bg-slate-50 px-3 py-2">
            <div className="font-semibold uppercase text-slate-500">Tentativas</div>
            <div className="mt-1 text-base font-bold text-slate-900">
              {overall.total_attempts ?? 0}
            </div>
          </div>
          <div className="rounded-lg bg-emerald-50 px-3 py-2">
            <div className="font-semibold uppercase text-emerald-700">Elegíveis</div>
            <div className="mt-1 text-base font-bold text-emerald-900">
              {overall.eligible_attempts ?? 0}
            </div>
          </div>
          <div className="rounded-lg bg-amber-50 px-3 py-2">
            <div className="font-semibold uppercase text-amber-700">Rejeições</div>
            <div className="mt-1 text-base font-bold text-amber-900">
              {overall.expected_rejections ?? 0}
            </div>
          </div>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-600">
          Sem medição ainda. A linha de base começa depois que a coleta for publicada.
        </div>
      ) : (
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {items.map((item) => {
            const objective = item.objective || {};
            return (
              <article
                key={item.journey}
                className={`rounded-lg border p-4 ${toneClasses(item.objective_status)}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-bold">
                      {JOURNEY_LABELS[item.journey] || item.journey}
                    </div>
                    <div className="mt-1 text-xs opacity-70">
                      {item.eligible_attempts || 0} elegíveis de {item.total_attempts || 0}
                    </div>
                  </div>
                  <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] font-bold">
                    {STATUS_LABELS[item.objective_status] || item.objective_status}
                  </span>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <div className="rounded-lg bg-white/70 px-3 py-2">
                    <div className="flex items-center gap-1 text-[11px] font-semibold uppercase opacity-70">
                      <FiShield className="h-3.5 w-3.5" /> Sucesso
                    </div>
                    <div className="mt-1 text-lg font-black">
                      {formatPercent(item.success_rate_percent)}
                    </div>
                    <div className="text-[11px] opacity-70">
                      Meta {formatPercent(objective.success_rate_percent)}
                    </div>
                  </div>
                  <div className="rounded-lg bg-white/70 px-3 py-2">
                    <div className="flex items-center gap-1 text-[11px] font-semibold uppercase opacity-70">
                      <FiClock className="h-3.5 w-3.5" /> p95
                    </div>
                    <div className="mt-1 text-lg font-black">{formatMs(item.latency_ms?.p95)}</div>
                    <div className="text-[11px] opacity-70">
                      Meta até {formatMs(objective.p95_ms)}
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="mt-3 text-xs text-slate-500">
        Menos de 100 operações aparece como amostra pequena. Rejeições esperadas não viram falha do
        sistema.
      </div>
    </section>
  );
}
