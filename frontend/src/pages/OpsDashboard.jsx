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

function buildAlerts({ errorSummary, deploySummary, watchdog }) {
  const alerts = [];
  const watchdogHealthy = watchdog?.status === "healthy";
  const errors5xx = Number(errorSummary?.errors_5xx || 0);
  const slowRequests = Number(errorSummary?.slow_requests || 0);
  const lastFailed = deploySummary?.last_failed;
  const lastSuccess = deploySummary?.last_success;

  if (!watchdogHealthy) {
    alerts.push({
      tone: "red",
      title: "Watchdog degradado",
      detail: "O health operacional nao retornou saudavel.",
    });
  }

  if (errors5xx > 0) {
    alerts.push({
      tone: "red",
      title: `${errors5xx} erro(s) 5xx nas ultimas 24h`,
      detail: "Priorize rotas e tenants com maior recorrencia.",
    });
  }

  if (slowRequests > 0) {
    alerts.push({
      tone: "amber",
      title: `${slowRequests} requisicao(oes) lenta(s)`,
      detail: `Acima de ${formatMs(errorSummary?.source?.slow_request_ms || 3000)}.`,
    });
  }

  if (lastFailed && (!lastSuccess || String(lastFailed.created_at) > String(lastSuccess.created_at))) {
    alerts.push({
      tone: "red",
      title: "Ultimo deploy falhou",
      detail: lastFailed.message || `Etapa: ${lastFailed.step || "-"}`,
    });
  }

  if (alerts.length === 0) {
    alerts.push({
      tone: "green",
      title: "Sem alerta critico no periodo",
      detail: "Watchdog, erros e deploys recentes nao indicam bloqueio imediato.",
    });
  }

  return alerts;
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
          <h2 className="text-base font-bold text-slate-900">Alertas automaticos</h2>
          <p className="text-sm text-slate-500">Calculados a partir de health, erros e deploys.</p>
        </div>
        <FiZap className="h-5 w-5 text-blue-600" />
      </div>
      <div className="mt-4 space-y-3">
        {alerts.map((alert) => (
          <div key={`${alert.title}-${alert.detail}`} className={`rounded-lg border px-4 py-3 ${toneClasses(alert.tone)}`}>
            <div className="flex items-start gap-3">
              {alert.tone === "green" ? (
                <FiCheckCircle className="mt-0.5 h-5 w-5 shrink-0" />
              ) : (
                <FiAlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              )}
              <div>
                <div className="text-sm font-bold">{alert.title}</div>
                <div className="mt-0.5 text-xs text-slate-600">{alert.detail}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RankingPanel({ title, items, emptyLabel }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-bold text-slate-900">{title}</h2>
      <div className="mt-4 space-y-2">
        {(items || []).length === 0 ? (
          <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">{emptyLabel}</div>
        ) : (
          items.slice(0, 8).map(([label, total]) => (
            <div key={label} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
              <span className="truncate text-sm text-slate-700" title={label}>
                {label}
              </span>
              <span className="rounded-full bg-white px-2 py-0.5 text-xs font-bold text-slate-900 shadow-sm">
                {total}
              </span>
            </div>
          ))
        )}
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
          <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">
            Nenhum deploy registrado ainda.
          </div>
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

export default function OpsDashboard() {
  const [errorSummary, setErrorSummary] = useState(null);
  const [deploySummary, setDeploySummary] = useState(null);
  const [watchdog, setWatchdog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const since = useMemo(() => sinceFromHours(RANGE_HOURS), []);
  const alerts = useMemo(
    () => buildAlerts({ errorSummary, deploySummary, watchdog }),
    [deploySummary, errorSummary, watchdog],
  );

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [errorResult, deployResult, watchdogResult] = await Promise.allSettled([
        api.get("/admin/observabilidade/error-events/summary", { params: { since } }),
        api.get("/admin/observabilidade/deploy-events/summary", { params: { since } }),
        api.get("/health/watchdog", { validateStatus: () => true }),
      ]);

      if (errorResult.status === "rejected") throw errorResult.reason;
      if (deployResult.status === "rejected") throw deployResult.reason;

      setErrorSummary(errorResult.value.data);
      setDeploySummary(deployResult.value.data);
      setWatchdog(
        watchdogResult.status === "fulfilled"
          ? watchdogResult.value.data
          : { status: "indisponivel", database: "desconhecido" },
      );
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

  const watchdogHealthy = watchdog?.status === "healthy";
  const lastDeploy = deploySummary?.latest?.[0];

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
              Ultimas 24h de erros, lentidao, watchdog e deploys.
            </p>
          </div>
          <div className="flex gap-2">
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

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            icon={FiCheckCircle}
            label="Watchdog"
            value={watchdog?.status || "-"}
            detail={watchdog?.latency_ms ? `${formatMs(watchdog.latency_ms)} no banco` : "Health operacional"}
            tone={watchdogHealthy ? "green" : "red"}
          />
          <MetricCard
            icon={FiAlertTriangle}
            label="Erros 5xx"
            value={errorSummary?.errors_5xx ?? "-"}
            detail="Falhas de servidor"
            tone={Number(errorSummary?.errors_5xx || 0) > 0 ? "red" : "green"}
          />
          <MetricCard
            icon={FiClock}
            label="Lentidao"
            value={errorSummary?.slow_requests ?? "-"}
            detail={`Acima de ${formatMs(errorSummary?.source?.slow_request_ms || 3000)}`}
            tone={Number(errorSummary?.slow_requests || 0) > 0 ? "amber" : "green"}
          />
          <MetricCard
            icon={FiActivity}
            label="Eventos"
            value={errorSummary?.total ?? "-"}
            detail="Eventos operacionais"
            tone="blue"
          />
          <MetricCard
            icon={FiGitBranch}
            label="Ultimo deploy"
            value={lastDeploy?.status || "-"}
            detail={lastDeploy ? `${shortHash(lastDeploy.head_after)} em ${formatDate(lastDeploy.created_at)}` : "Sem registro"}
            tone={lastDeploy?.status === "failed" ? "red" : "slate"}
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
          <AlertPanel alerts={alerts} />
          <DeployPanel deploys={deploySummary} />
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <RankingPanel
            title="Tenants com maior incidencia"
            items={errorSummary?.by_tenant || []}
            emptyLabel="Nenhum tenant com evento no periodo."
          />
          <RankingPanel
            title="Rotas mais sensiveis"
            items={errorSummary?.by_path || []}
            emptyLabel="Nenhuma rota com evento no periodo."
          />
        </div>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Banco e pool</h2>
              <p className="text-sm text-slate-500">Estado retornado pelo watchdog.</p>
            </div>
            <FiDatabase className="h-5 w-5 text-slate-500" />
          </div>
          <div className="mt-4 rounded-lg bg-slate-50 px-3 py-3 font-mono text-xs text-slate-700">
            {watchdog?.pool || "Sem dados de pool agora."}
          </div>
        </section>
      </div>
    </div>
  );
}
