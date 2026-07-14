import { FiActivity, FiAlertTriangle, FiCheckCircle, FiClock } from "react-icons/fi";

import OpsTenantsBadge from "./OpsTenantsBadge";
import OpsTenantsMetricCard from "./OpsTenantsMetricCard";
import { formatDate, formatNumber, shortId } from "./opsTenantsFormatters";

const STATUS = {
  active: {
    label: "ativo acompanhado",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  ready: {
    label: "pronto para iniciar",
    className: "border-blue-200 bg-blue-50 text-blue-700",
  },
  blocked: {
    label: "bloqueado",
    className: "border-rose-200 bg-rose-50 text-rose-700",
  },
  pending: {
    label: "preparacao pendente",
    className: "border-amber-200 bg-amber-50 text-amber-800",
  },
};

function Milestone({ checked, children }) {
  return (
    <div className="flex items-center gap-2 text-xs text-slate-600">
      <FiCheckCircle className={checked ? "h-4 w-4 text-emerald-600" : "h-4 w-4 text-slate-300"} />
      <span>{children}</span>
    </div>
  );
}

export default function OpsTenantsPilotTab({ items, summaries, loading }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <OpsTenantsMetricCard
          icon={FiActivity}
          label="Pilotos ativos"
          value={formatNumber(summaries.pilot.active)}
          detail="Com acesso e atividade operacional"
          tone="green"
        />
        <OpsTenantsMetricCard
          icon={FiClock}
          label="Em preparacao"
          value={formatNumber(summaries.pilot.pending)}
          detail="Pendentes ou prontos para iniciar"
          tone="blue"
        />
        <OpsTenantsMetricCard
          icon={FiAlertTriangle}
          label="Bloqueados"
          value={formatNumber(summaries.pilot.blocked)}
          detail="Com alerta critico aberto"
          tone={summaries.pilot.blocked ? "amber" : "green"}
        />
      </div>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">Acompanhamento dos pilotos</h2>
            <p className="text-sm text-slate-500">
              Evidencias automaticas de acesso, configuracao, operacao e incidentes.
            </p>
          </div>
          {loading ? (
            <OpsTenantsBadge className="border-blue-200 bg-blue-50 text-blue-700">
              carregando
            </OpsTenantsBadge>
          ) : (
            <OpsTenantsBadge className="border-slate-200 bg-slate-50 text-slate-700">
              somente leitura
            </OpsTenantsBadge>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[1280px] w-full divide-y divide-slate-200 text-left">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3 font-bold">Tenant / piloto</th>
                <th className="px-4 py-3 font-bold">Situacao</th>
                <th className="px-4 py-3 font-bold">Ultima atividade</th>
                <th className="px-4 py-3 font-bold">Operacao</th>
                <th className="px-4 py-3 font-bold">Saude 7 dias</th>
                <th className="px-4 py-3 font-bold">Marcos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.length === 0 && !loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-500">
                    Nenhum tenant encontrado para o filtro atual.
                  </td>
                </tr>
              ) : (
                items.map((tenant) => {
                  const pilot = tenant.pilot || {};
                  const status = STATUS[pilot.status] || STATUS.pending;
                  const milestones = pilot.milestones || {};
                  return (
                    <tr key={tenant.id} className="bg-white align-top hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="text-sm font-bold text-slate-900">{tenant.name}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {pilot.kind === "veterinario" ? "Piloto veterinario" : "Plano Basico"}
                          {pilot.days_since_start != null ? ` · D+${pilot.days_since_start}` : ""}
                        </div>
                        <div className="mt-1 font-mono text-[11px] text-slate-400">
                          {shortId(tenant.id)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <OpsTenantsBadge className={status.className}>
                          {status.label}
                        </OpsTenantsBadge>
                        <div className="mt-2 text-xs text-slate-500">
                          Acesso {pilot.access_confirmed ? "confirmado" : "pendente"}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        {formatDate(pilot.last_activity_at)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        <div>{formatNumber(pilot.operational_events)} evento(s)</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {formatNumber(pilot.setup_records)} cadastros base
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        <div>{formatNumber(pilot.errors_7d)} erro(s) 5xx</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {formatNumber(pilot.critical_alerts_open)} alerta(s) critico(s)
                        </div>
                      </td>
                      <td className="space-y-1.5 px-4 py-3">
                        <Milestone checked={milestones.day_1_access}>D1 acesso</Milestone>
                        <Milestone checked={milestones.day_3_setup}>D3 configuracao</Milestone>
                        <Milestone checked={milestones.day_7_operation}>
                          D7 operacao saudavel
                        </Milestone>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
