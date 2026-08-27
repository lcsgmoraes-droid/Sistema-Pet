import { FiActivity, FiAlertTriangle, FiCheckCircle, FiClock } from "react-icons/fi";

import OpsTenantsBadge from "./OpsTenantsBadge";
import OpsTenantsMetricCard from "./OpsTenantsMetricCard";
import OpsTenantsOnboardingPanel from "./OpsTenantsOnboardingPanel";
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

const ATTENTION = {
  healthy: {
    label: "em dia",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  normal: {
    label: "acompanhar",
    className: "border-blue-200 bg-blue-50 text-blue-700",
  },
  high: {
    label: "acao necessaria",
    className: "border-amber-200 bg-amber-50 text-amber-800",
  },
  critical: {
    label: "urgente",
    className: "border-rose-200 bg-rose-50 text-rose-700",
  },
};

const SATISFACTION = {
  not_collected: "nao registrada",
  satisfied: "satisfeito",
  neutral: "neutro",
  dissatisfied: "insatisfeito",
};

function Milestone({ checked, children }) {
  return (
    <div className="flex items-center gap-2 text-xs text-slate-600">
      <FiCheckCircle className={checked ? "h-4 w-4 text-emerald-600" : "h-4 w-4 text-slate-300"} />
      <span>{children}</span>
    </div>
  );
}

export default function OpsTenantsPilotTab({
  items,
  summaries,
  loading,
  selectedTenant,
  form,
  error,
  success,
  saving,
  onSelectTenant,
  onChange,
  onSubmit,
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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
        <OpsTenantsMetricCard
          icon={FiClock}
          label="Com proxima acao"
          value={formatNumber(summaries.pilot.needFollowUp)}
          detail="Fila objetiva para o acompanhamento"
          tone={summaries.pilot.needFollowUp ? "amber" : "green"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
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
              <OpsTenantsBadge className="border-blue-200 bg-blue-50 text-blue-700">
                editavel
              </OpsTenantsBadge>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-[1480px] w-full divide-y divide-slate-200 text-left">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-bold">Tenant / piloto</th>
                  <th className="px-4 py-3 font-bold">Situacao</th>
                  <th className="px-4 py-3 font-bold">Ultima atividade</th>
                  <th className="px-4 py-3 font-bold">Operacao</th>
                  <th className="px-4 py-3 font-bold">Saude 7 dias</th>
                  <th className="px-4 py-3 font-bold">Marcos</th>
                  <th className="px-4 py-3 font-bold">Proxima acao</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.length === 0 && !loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-sm text-slate-500">
                      Nenhum tenant encontrado para o filtro atual.
                    </td>
                  </tr>
                ) : (
                  items.map((tenant) => {
                    const pilot = tenant.pilot || {};
                    const status = STATUS[pilot.status] || STATUS.pending;
                    const milestones = pilot.milestones || {};
                    const attention = ATTENTION[pilot.attention_level] || ATTENTION.normal;
                    const followUp = tenant.onboarding_follow_up || {};
                    const selected = tenant.id === selectedTenant?.id;
                    return (
                      <tr
                        key={tenant.id}
                        className={`align-top hover:bg-slate-50 ${
                          selected ? "bg-blue-50/60" : "bg-white"
                        }`}
                      >
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
                        <td className="px-4 py-3">
                          <OpsTenantsBadge className={attention.className}>
                            {attention.label}
                          </OpsTenantsBadge>
                          <div className="mt-2 max-w-xs text-xs font-semibold text-slate-700">
                            {pilot.next_action || "Revisar o onboarding desta empresa."}
                          </div>
                          {(pilot.overdue_milestones || []).length > 0 ? (
                            <div className="mt-1 text-xs text-rose-700">
                              Atrasado: {pilot.overdue_milestones.join(", ")}
                            </div>
                          ) : null}
                          <div className="mt-2 text-xs text-slate-500">
                            Responsavel: {followUp.owner_name || "nao definido"}
                          </div>
                          <div className="mt-1 text-xs text-slate-500">
                            Satisfacao: {SATISFACTION[followUp.satisfaction] || "nao registrada"}
                          </div>
                          <button
                            type="button"
                            onClick={() => onSelectTenant(tenant.id)}
                            className="mt-2 text-xs font-bold text-blue-700 hover:text-blue-900"
                          >
                            Editar acompanhamento
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>

        <OpsTenantsOnboardingPanel
          tenant={selectedTenant}
          form={form}
          error={error}
          success={success}
          saving={saving}
          onChange={onChange}
          onSubmit={onSubmit}
        />
      </div>
    </div>
  );
}
