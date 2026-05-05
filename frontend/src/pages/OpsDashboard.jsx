import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  FiActivity,
  FiAlertTriangle,
  FiCheckCircle,
  FiClock,
  FiDatabase,
  FiGitBranch,
  FiRefreshCw,
  FiServer,
  FiShield,
  FiZap,
} from "react-icons/fi";

import api from "../api";

const RANGE_HOURS = 24;

function sinceFromHours(hours) {
  return new Date(Date.now() - Number(hours || 24) * 60 * 60 * 1000).toISOString();
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  });
}

function formatMs(value) {
  const number = Number(value || 0);
  return `${number.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} ms`;
}

function shortHash(value) {
  const text = String(value || "");
  return text ? text.slice(0, 8) : "-";
}

function toneClasses(tone) {
  const tones = {
    blue: "border-blue-200 bg-blue-50 text-blue-900",
    green: "border-emerald-200 bg-emerald-50 text-emerald-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    red: "border-rose-200 bg-rose-50 text-rose-900",
    slate: "border-slate-200 bg-white text-slate-900",
  };
  return tones[tone] || tones.slate;
}

function statusTone(status) {
  if (status === "critical" || status === "unhealthy") return "red";
  if (status === "degraded" || status === "warning") return "amber";
  if (status === "healthy" || status === "ok") return "green";
  return "slate";
}

function statusLabel(status) {
  const labels = {
    critical: "critico",
    degraded: "degradado",
    healthy: "saudavel",
    unhealthy: "indisponivel",
    ok: "ok",
  };
  return labels[status] || status || "-";
}

function MetricCard({ icon: Icon, label, value, detail, tone = "slate" }) {
  return (
    <div className={`rounded-lg border p-4 shadow-sm ${toneClasses(tone)}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
        <Icon className="h-5 w-5 text-current opacity-70" />
      </div>
      <div className="mt-3 text-2xl font-bold">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{detail}</div>
    </div>
  );
}

function AlertPanel({ alerts }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">Alertas e resposta</h2>
          <p className="text-sm text-slate-500">Prioridade calculada no backend operacional.</p>
        </div>
        <FiZap className="h-5 w-5 text-blue-600" />
      </div>
      <div className="mt-4 space-y-3">
        {(alerts || []).map((alert) => (
          <div key={`${alert.title}-${alert.source}`} className={`rounded-lg border px-4 py-3 ${toneClasses(alert.tone)}`}>
            <div className="flex items-start gap-3">
              {alert.tone === "green" ? (
                <FiCheckCircle className="mt-0.5 h-5 w-5 shrink-0" />
              ) : (
                <FiAlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              )}
              <div className="min-w-0">
                <div className="text-sm font-bold">{alert.title}</div>
                <div className="mt-0.5 text-xs text-slate-600">{alert.detail}</div>
                {alert.action ? <div className="mt-2 text-xs font-semibold text-slate-800">{alert.action}</div> : null}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function DeployPanel({ deploys }) {
  const items = deploys?.latest || [];

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">Deploys recentes</h2>
          <p className="text-sm text-slate-500">Registrados pelo deploy seguro.</p>
        </div>
        <FiGitBranch className="h-5 w-5 text-slate-500" />
      </div>
      <div className="mt-4 space-y-2">
        {items.length === 0 ? (
          <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">Nenhum deploy registrado.</div>
        ) : (
          items.map((item) => {
            const success = item.status === "success";
            return (
              <div key={`${item.created_at}-${item.head_after}`} className="rounded-lg border border-slate-100 px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${success ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                    {success ? "sucesso" : "falha"}
                  </span>
                  <span className="text-xs text-slate-500">{formatDate(item.created_at)}</span>
                </div>
                <div className="mt-2 flex items-center justify-between gap-3 text-sm">
                  <span className="font-mono text-slate-700">{shortHash(item.head_after)}</span>
                  <span className="truncate text-xs text-slate-500">{item.step || "-"}</span>
                </div>
                {item.message ? <div className="mt-1 truncate text-xs text-slate-500">{item.message}</div> : null}
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

function TenantIncidentsPanel({ items }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-bold text-slate-900">Tenants sensiveis</h2>
      <p className="mt-1 text-sm text-slate-500">Quem mais sofreu erro ou lentidao no periodo.</p>
      <div className="mt-4 space-y-2">
        {(items || []).length === 0 ? (
          <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">Nenhum tenant com evento.</div>
        ) : (
          items.slice(0, 8).map((item) => (
            <div key={item.tenant_id || item.tenant_name} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="truncate text-sm font-bold text-slate-800" title={item.tenant_name}>
                  {item.tenant_name}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${toneClasses(statusTone(item.severity))}`}>
                  {item.total}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-600">
                <span>5xx: <b>{item.errors_5xx}</b></span>
                <span>Lentas: <b>{item.slow_requests}</b></span>
                <span>{formatDate(item.latest_at)}</span>
              </div>
              <div className="mt-2 truncate text-xs text-slate-500">
                {(item.top_paths || []).map((path) => `${path.path} (${path.total})`).join(" | ") || "Sem rota dominante"}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function RouteIncidentsPanel({ items }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-bold text-slate-900">Rotas sensiveis</h2>
      <p className="mt-1 text-sm text-slate-500">Onde atacar causa raiz primeiro.</p>
      <div className="mt-4 space-y-2">
        {(items || []).length === 0 ? (
          <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">Nenhuma rota com evento.</div>
        ) : (
          items.slice(0, 8).map((item) => (
            <div key={item.path} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="truncate font-mono text-xs text-slate-800" title={item.path}>
                  {item.path}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${toneClasses(statusTone(item.severity))}`}>
                  {item.total}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600 md:grid-cols-4">
                <span>5xx: <b>{item.errors_5xx}</b></span>
                <span>Lentas: <b>{item.slow_requests}</b></span>
                <span>Max: <b>{formatMs(item.max_duration_ms)}</b></span>
                <span>Tenants: <b>{item.tenant_count}</b></span>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function SelfHealingPanel({ selfHealing, watchdogEvents }) {
  const latest = watchdogEvents?.latest_recovery || [];

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">Auto-recuperacao</h2>
          <p className="text-sm text-slate-500">Como o sistema tenta se virar sozinho.</p>
        </div>
        <FiShield className="h-5 w-5 text-emerald-600" />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-lg bg-emerald-50 px-3 py-3 text-sm text-emerald-900">
          <div className="text-xs font-semibold uppercase text-emerald-700">Status</div>
          <div className="mt-1 font-bold">{selfHealing?.status || "-"}</div>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-800">
          <div className="text-xs font-semibold uppercase text-slate-500">Falhas ate reiniciar</div>
          <div className="mt-1 font-bold">{selfHealing?.failure_threshold ?? "-"}</div>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-800">
          <div className="text-xs font-semibold uppercase text-slate-500">Intervalo</div>
          <div className="mt-1 font-bold">{selfHealing?.interval_seconds ?? "-"}s</div>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-800">
          <div className="text-xs font-semibold uppercase text-slate-500">Recuperacoes</div>
          <div className="mt-1 font-bold">{watchdogEvents?.recoveries ?? 0}</div>
        </div>
      </div>
      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        <div className="rounded-lg bg-slate-50 px-3 py-3 text-xs text-slate-600">
          {(selfHealing?.capabilities || []).map((item) => (
            <div key={item} className="py-1">- {item}</div>
          ))}
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-3 text-xs text-slate-600">
          {latest.length === 0 ? (
            <div>Nenhuma recuperacao automatica registrada no periodo.</div>
          ) : (
            latest.map((item) => (
              <div key={`${item.created_at}-${item.event_type}`} className="flex justify-between gap-3 py-1">
                <span className="truncate">{item.event_type}: {item.message}</span>
                <span className="shrink-0">{formatDate(item.created_at)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

export default function OpsDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const since = useMemo(() => sinceFromHours(RANGE_HOURS), []);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/admin/observabilidade/ops-summary", { params: { since } });
      setDashboard(response.data);
    } catch (err) {
      console.error("Erro ao carregar cockpit Ops:", err);
      setError(err?.response?.data?.detail || "Nao foi possivel carregar o cockpit agora.");
    } finally {
      setLoading(false);
    }
  }, [since]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const watchdog = dashboard?.watchdog;
  const errors = dashboard?.errors;
  const deploys = dashboard?.deploys;
  const watchdogEvents = dashboard?.watchdog_events;
  const selfHealing = dashboard?.self_healing;
  const lastDeploy = deploys?.latest?.[0];
  const currentStatus = dashboard?.current_status;
  const periodStatus = dashboard?.period_status || dashboard?.status;

  return (
    <div className="p-6">
      <div className="mx-auto max-w-[1500px] space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-600">
              <FiServer className="h-5 w-5" />
              Cockpit operacional
            </div>
            <h1 className="mt-1 text-2xl font-bold text-slate-950">Saude da plataforma</h1>
            <p className="mt-1 text-sm text-slate-500">
              Estado atual do servidor separado do historico das ultimas 24h.
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              to="/ops/incidentes"
              className="inline-flex h-10 items-center rounded-lg border border-blue-200 bg-blue-50 px-4 text-sm font-semibold text-blue-700 hover:bg-blue-100"
            >
              Ver incidentes
            </Link>
            <Link
              to="/ops/observabilidade"
              className="inline-flex h-10 items-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Ver observabilidade
            </Link>
            <button
              type="button"
              onClick={loadDashboard}
              disabled={loading}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <FiRefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Atualizar
            </button>
          </div>
        </div>

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <MetricCard
            icon={FiCheckCircle}
            label="Estado atual"
            value={statusLabel(currentStatus?.status || watchdog?.status)}
            detail={currentStatus?.detail || "Health em tempo real"}
            tone={statusTone(currentStatus?.status || watchdog?.status)}
          />
          <MetricCard
            icon={FiActivity}
            label="Historico 24h"
            value={statusLabel(periodStatus)}
            detail="Erros, lentidao e recuperacoes do periodo"
            tone={statusTone(periodStatus)}
          />
          <MetricCard
            icon={FiDatabase}
            label="Watchdog"
            value={statusLabel(watchdog?.status)}
            detail={watchdog?.latency_ms ? `${formatMs(watchdog.latency_ms)} no banco` : "Health operacional"}
            tone={statusTone(watchdog?.status)}
          />
          <MetricCard
            icon={FiAlertTriangle}
            label="Erros 5xx"
            value={errors?.errors_5xx ?? "-"}
            detail="Falhas de servidor"
            tone={Number(errors?.errors_5xx || 0) > 0 ? "red" : "green"}
          />
          <MetricCard
            icon={FiClock}
            label="Lentidao"
            value={errors?.slow_requests ?? "-"}
            detail={`Acima de ${formatMs(errors?.source?.slow_request_ms || 3000)}`}
            tone={Number(errors?.slow_requests || 0) > 0 ? "amber" : "green"}
          />
          <MetricCard
            icon={FiGitBranch}
            label="Ultimo deploy"
            value={lastDeploy?.status || "-"}
            detail={lastDeploy ? `${shortHash(lastDeploy.head_after)} em ${formatDate(lastDeploy.created_at)}` : "Sem registro"}
            tone={lastDeploy?.status === "failed" ? "red" : "slate"}
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <AlertPanel alerts={dashboard?.alerts || []} />
          <DeployPanel deploys={deploys} />
        </div>

        <SelfHealingPanel selfHealing={selfHealing} watchdogEvents={watchdogEvents} />

        <div className="grid gap-4 xl:grid-cols-2">
          <TenantIncidentsPanel items={dashboard?.tenant_incidents || []} />
          <RouteIncidentsPanel items={dashboard?.route_incidents || []} />
        </div>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Banco e pool</h2>
              <p className="text-sm text-slate-500">Estado retornado pelo watchdog.</p>
            </div>
            <FiActivity className="h-5 w-5 text-slate-500" />
          </div>
          <div className="mt-4 rounded-lg bg-slate-50 px-3 py-3 font-mono text-xs text-slate-700">
            {watchdog?.pool || "Sem dados de pool agora."}
          </div>
        </section>
      </div>
    </div>
  );
}
