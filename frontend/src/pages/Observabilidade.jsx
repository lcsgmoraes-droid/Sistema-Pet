import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FiActivity,
  FiAlertTriangle,
  FiCheckCircle,
  FiClock,
  FiDatabase,
  FiFilter,
  FiRefreshCw,
  FiSearch,
  FiServer,
} from "react-icons/fi";

import api from "../api";

const PAGE_SIZE = 50;

const RANGE_OPTIONS = [
  { label: "Ultimas 2h", hours: 2 },
  { label: "24h", hours: 24 },
  { label: "7 dias", hours: 168 },
  { label: "30 dias", hours: 720 },
];

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

function shortValue(value, max = 120) {
  const text = String(value || "-");
  if (text.length <= max) return text;
  return `${text.slice(0, max - 3)}...`;
}

function statusTone(status) {
  const code = Number(status || 0);
  if (code >= 500) return "bg-rose-100 text-rose-700 border-rose-200";
  if (code >= 400) return "bg-amber-100 text-amber-700 border-amber-200";
  if (code >= 300) return "bg-sky-100 text-sky-700 border-sky-200";
  if (code >= 200) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  return "bg-slate-100 text-slate-600 border-slate-200";
}

function Badge({ children, className = "" }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${className}`}
    >
      {children}
    </span>
  );
}

function MetricCard({ icon: Icon, label, value, detail, tone = "slate" }) {
  const tones = {
    slate: "border-slate-200 bg-white text-slate-900",
    green: "border-emerald-200 bg-emerald-50 text-emerald-900",
    red: "border-rose-200 bg-rose-50 text-rose-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    blue: "border-blue-200 bg-blue-50 text-blue-900",
  };

  return (
    <div className={`rounded-lg border p-4 shadow-sm ${tones[tone] || tones.slate}`}>
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
      {detail ? <div className="mt-1 text-xs text-slate-500">{detail}</div> : null}
    </div>
  );
}

function RankingList({ title, items, emptyLabel = "Sem eventos" }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      <div className="mt-3 space-y-2">
        {items.length === 0 ? (
          <p className="text-sm text-slate-500">{emptyLabel}</p>
        ) : (
          items.map(([label, total]) => (
            <div
              key={label}
              className="flex items-center justify-between gap-3 rounded-md bg-slate-50 px-3 py-2"
            >
              <span className="truncate text-sm text-slate-700" title={label}>
                {label}
              </span>
              <span className="text-sm font-semibold text-slate-900">{total}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function Observabilidade() {
  const [rangeHours, setRangeHours] = useState(24);
  const [tenantId, setTenantId] = useState("");
  const [pathContains, setPathContains] = useState("");
  const [statusMin, setStatusMin] = useState("500");
  const [slowOnly, setSlowOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState({ items: [], total: 0, source: null });
  const [watchdog, setWatchdog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const since = useMemo(() => sinceFromHours(rangeHours), [rangeHours]);
  const totalPages = Math.max(1, Math.ceil(Number(events.total || 0) / PAGE_SIZE));

  const carregarDados = useCallback(async () => {
    setLoading(true);
    setError("");

    const commonParams = {
      since,
      tenant_id: tenantId.trim() || undefined,
    };

    const eventParams = {
      ...commonParams,
      page,
      page_size: PAGE_SIZE,
      path_contains: pathContains.trim() || undefined,
      status_min: statusMin === "" ? undefined : Number(statusMin),
      slow_only: slowOnly,
    };

    try {
      const [summaryResult, eventsResult, watchdogResult] = await Promise.allSettled([
        api.get("/admin/observabilidade/error-events/summary", { params: commonParams }),
        api.get("/admin/observabilidade/error-events", { params: eventParams }),
        api.get("/health/watchdog", { validateStatus: () => true }),
      ]);

      if (summaryResult.status === "rejected") throw summaryResult.reason;
      if (eventsResult.status === "rejected") throw eventsResult.reason;

      setSummary(summaryResult.value.data);
      setEvents(eventsResult.value.data);
      setWatchdog(
        watchdogResult.status === "fulfilled"
          ? watchdogResult.value.data
          : { status: "indisponivel", database: "desconhecido" },
      );
    } catch (err) {
      console.error("Erro ao carregar observabilidade:", err);
      setError(err?.response?.data?.detail || "Nao foi possivel carregar a observabilidade agora.");
    } finally {
      setLoading(false);
    }
  }, [page, pathContains, since, slowOnly, statusMin, tenantId]);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  function aplicarFiltros(event) {
    event.preventDefault();
    setPage(1);
    carregarDados();
  }

  const watchdogHealthy = watchdog?.status === "healthy";
  const source = events.source || summary?.source;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-[1500px] space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <FiActivity className="h-6 w-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-slate-900">Observabilidade Operacional</h1>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              Erros, lentidao e saude tecnica por tenant para investigar producao sem adivinhar.
            </p>
          </div>
          <button
            type="button"
            onClick={carregarDados}
            disabled={loading}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FiRefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Atualizar
          </button>
        </div>

        <form
          onSubmit={aplicarFiltros}
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        >
          <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_160px_120px]">
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Periodo
              </span>
              <select
                value={rangeHours}
                onChange={(event) => {
                  setRangeHours(Number(event.target.value));
                  setPage(1);
                }}
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                {RANGE_OPTIONS.map((option) => (
                  <option key={option.hours} value={option.hours}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Tenant
              </span>
              <input
                value={tenantId}
                onChange={(event) => {
                  setTenantId(event.target.value);
                  setPage(1);
                }}
                placeholder="ID do tenant"
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </label>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Rota contem
              </span>
              <div className="relative mt-1">
                <FiSearch className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                <input
                  value={pathContains}
                  onChange={(event) => {
                    setPathContains(event.target.value);
                    setPage(1);
                  }}
                  placeholder="/pdv, /login, /produtos..."
                  className="h-10 w-full rounded-lg border border-slate-300 pl-9 pr-3 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </div>
            </label>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Status min.
              </span>
              <select
                value={statusMin}
                onChange={(event) => {
                  setStatusMin(event.target.value);
                  setPage(1);
                }}
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Todos</option>
                <option value="400">400+</option>
                <option value="500">500+</option>
              </select>
            </label>

            <div className="flex items-end">
              <label className="flex h-10 w-full items-center gap-2 rounded-lg border border-slate-300 px-3 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={slowOnly}
                  onChange={(event) => {
                    setSlowOnly(event.target.checked);
                    setPage(1);
                  }}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                Lentos
              </label>
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <FiFilter className="h-4 w-4" />
              {source ? (
                <span>
                  Fonte: {source.path} | lento acima de {formatMs(source.slow_request_ms)}
                </span>
              ) : (
                <span>Filtros aplicados sobre os eventos recentes gravados no backend.</span>
              )}
            </div>
            <button
              type="submit"
              className="inline-flex h-9 items-center rounded-lg bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800"
            >
              Filtrar
            </button>
          </div>
        </form>

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            icon={FiActivity}
            label="Eventos"
            value={summary?.total ?? "-"}
            detail="No periodo filtrado"
            tone="blue"
          />
          <MetricCard
            icon={FiAlertTriangle}
            label="Erros 5xx"
            value={summary?.errors_5xx ?? "-"}
            detail="Falhas reais do servidor"
            tone={Number(summary?.errors_5xx || 0) > 0 ? "red" : "green"}
          />
          <MetricCard
            icon={FiClock}
            label="Requisicoes lentas"
            value={summary?.slow_requests ?? "-"}
            detail="Acima do limite tecnico"
            tone={Number(summary?.slow_requests || 0) > 0 ? "amber" : "green"}
          />
          <MetricCard
            icon={FiDatabase}
            label="Banco"
            value={watchdog?.database || "-"}
            detail={
              watchdog?.latency_ms ? `${formatMs(watchdog.latency_ms)} de latencia` : "Watchdog"
            }
            tone={watchdogHealthy ? "green" : "amber"}
          />
          <MetricCard
            icon={FiServer}
            label="Watchdog"
            value={watchdog?.status || "-"}
            detail={watchdog?.pool ? shortValue(watchdog.pool, 48) : "Saude operacional"}
            tone={watchdogHealthy ? "green" : "amber"}
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <RankingList title="Tenants com mais eventos" items={summary?.by_tenant || []} />
          <RankingList title="Rotas mais recorrentes" items={summary?.by_path || []} />
          <RankingList title="Status HTTP" items={summary?.by_status || []} />
        </div>

        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Eventos recentes</h2>
              <p className="text-xs text-slate-500">
                Mostrando {events.items.length} de {events.total || 0} evento(s)
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1 || loading}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                className="h-8 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Anterior
              </button>
              <span className="text-sm text-slate-500">
                {page} / {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages || loading}
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                className="h-8 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Proxima
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3">Tenant</th>
                  <th className="px-4 py-3">Rota</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Tempo</th>
                  <th className="px-4 py-3">Usuario</th>
                  <th className="px-4 py-3">Detalhe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                      Carregando observabilidade...
                    </td>
                  </tr>
                ) : events.items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                      Nenhum evento encontrado para os filtros atuais.
                    </td>
                  </tr>
                ) : (
                  events.items.map((event) => (
                    <tr
                      key={`${event.request_id}-${event.created_at}`}
                      className="hover:bg-slate-50"
                    >
                      <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                        {formatDate(event.created_at)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
                        {event.tenant_id || "sem_tenant"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Badge className="border-slate-200 bg-slate-100 text-slate-600">
                            {event.method || "-"}
                          </Badge>
                          <span
                            className="max-w-[360px] truncate font-mono text-xs text-slate-800"
                            title={event.path}
                          >
                            {event.path || "-"}
                          </span>
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <Badge className={statusTone(event.status_code)}>
                          {event.status_code || "erro"}
                        </Badge>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                        {formatMs(event.duration_ms)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                        {event.user_email || event.user_id || "-"}
                      </td>
                      <td
                        className="px-4 py-3 text-slate-600"
                        title={event.exception_message || event.user_agent || ""}
                      >
                        <div className="flex items-center gap-2">
                          {event.exception_type ? (
                            <FiAlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
                          ) : (
                            <FiCheckCircle className="h-4 w-4 shrink-0 text-slate-400" />
                          )}
                          <span>
                            {shortValue(
                              event.exception_message || event.exception_type || event.request_id,
                              110,
                            )}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
