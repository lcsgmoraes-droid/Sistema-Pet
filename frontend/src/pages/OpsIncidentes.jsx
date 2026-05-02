import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FiAlertTriangle,
  FiCheckCircle,
  FiClock,
  FiCopy,
  FiFilter,
  FiRefreshCw,
  FiSearch,
  FiUser,
} from "react-icons/fi";

import api from "../api";

const PAGE_SIZE = 80;

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

function shortText(value, max = 120) {
  const text = String(value || "-");
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

function statusTone(status) {
  const code = Number(status || 0);
  if (code >= 500) return "border-rose-200 bg-rose-100 text-rose-700";
  if (code >= 400) return "border-amber-200 bg-amber-100 text-amber-700";
  if (code >= 200) return "border-emerald-200 bg-emerald-100 text-emerald-700";
  return "border-slate-200 bg-slate-100 text-slate-600";
}

function severityTone(severity) {
  if (severity === "critical") return "border-rose-200 bg-rose-50 text-rose-800";
  if (severity === "warning") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-slate-200 bg-white text-slate-800";
}

function Badge({ children, className = "" }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${className}`}>
      {children}
    </span>
  );
}

function copyToClipboard(value) {
  if (!value) return;
  navigator.clipboard?.writeText(String(value)).catch(() => {});
}

function TenantCard({ item, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(item.tenant_id || "sem_tenant")}
      className={[
        "w-full rounded-lg border px-3 py-3 text-left transition",
        selected ? "border-blue-400 bg-blue-50 shadow-sm" : severityTone(item.severity),
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-bold" title={item.tenant_name}>
            {item.tenant_name}
          </div>
          <div className="mt-1 truncate font-mono text-[11px] opacity-70">
            {item.tenant_id || "sem_tenant"}
          </div>
        </div>
        <Badge className="border-white bg-white/80 text-slate-900">{item.total}</Badge>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <span>5xx: <b>{item.errors_5xx}</b></span>
        <span>Lentas: <b>{item.slow_requests}</b></span>
        <span>{formatDate(item.latest_at)}</span>
      </div>
    </button>
  );
}

function RouteCard({ item, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(item.path)}
      className={[
        "w-full rounded-lg border px-3 py-3 text-left transition",
        selected ? "border-blue-400 bg-blue-50 shadow-sm" : severityTone(item.severity),
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-mono text-xs font-bold" title={item.path}>
            {item.path}
          </div>
          <div className="mt-1 text-[11px] opacity-70">
            {item.tenant_count} tenant(s) | max {formatMs(item.max_duration_ms)}
          </div>
        </div>
        <Badge className="border-white bg-white/80 text-slate-900">{item.total}</Badge>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <span>5xx: <b>{item.errors_5xx}</b></span>
        <span>Lentas: <b>{item.slow_requests}</b></span>
        <span>Media: <b>{formatMs(item.avg_duration_ms)}</b></span>
      </div>
    </button>
  );
}

function EventDetail({ event }) {
  if (!event) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-sm">
        Selecione um evento para ver request_id, rota, usuario e detalhes tecnicos.
      </div>
    );
  }

  const fields = [
    ["Request ID", event.request_id],
    ["Tenant", event.tenant_id || "sem_tenant"],
    ["Usuario", event.user_email || event.user_id || "-"],
    ["Rota", `${event.method || "-"} ${event.path || "-"}`],
    ["Status", event.status_code || "erro"],
    ["Duracao", formatMs(event.duration_ms)],
    ["IP", event.client_ip || "-"],
    ["Agente", event.user_agent || "-"],
  ];

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">Detalhe do evento</h2>
          <p className="mt-1 text-sm text-slate-500">{formatDate(event.created_at)}</p>
        </div>
        <button
          type="button"
          onClick={() => copyToClipboard(event.request_id)}
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          <FiCopy className="h-4 w-4" />
          Copiar request
        </button>
      </div>

      <div className="mt-4 grid gap-2">
        {fields.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[110px_1fr] gap-3 rounded-md bg-slate-50 px-3 py-2 text-sm">
            <span className="font-semibold text-slate-500">{label}</span>
            <span className="min-w-0 break-words font-mono text-xs text-slate-800">{value}</span>
          </div>
        ))}
      </div>

      {(event.exception_type || event.exception_message) ? (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <div className="font-bold">{event.exception_type || "Erro"}</div>
          <div className="mt-1 whitespace-pre-wrap text-xs">{event.exception_message || "Sem mensagem detalhada."}</div>
        </div>
      ) : null}
    </section>
  );
}

export default function OpsIncidentes() {
  const [rangeHours, setRangeHours] = useState(24);
  const [selectedTenant, setSelectedTenant] = useState("");
  const [selectedPath, setSelectedPath] = useState("");
  const [statusMin, setStatusMin] = useState("");
  const [slowOnly, setSlowOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState({ items: [], total: 0 });
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const since = useMemo(() => sinceFromHours(rangeHours), [rangeHours]);
  const totalPages = Math.max(1, Math.ceil(Number(events.total || 0) / PAGE_SIZE));

  const tenantNameById = useMemo(() => {
    const map = new Map();
    (summary?.tenant_incidents || []).forEach((item) => {
      map.set(item.tenant_id || "sem_tenant", item.tenant_name);
    });
    return map;
  }, [summary]);

  const filteredEvents = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return events.items;
    return events.items.filter((event) =>
      [
        event.request_id,
        event.path,
        event.tenant_id,
        event.user_email,
        event.user_id,
        event.exception_type,
        event.exception_message,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle)),
    );
  }, [events.items, query]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    const tenantParam = selectedTenant || undefined;
    const pathParam = selectedPath || undefined;

    try {
      const [summaryResult, eventsResult] = await Promise.all([
        api.get("/admin/observabilidade/ops-summary", { params: { since } }),
        api.get("/admin/observabilidade/error-events", {
          params: {
            since,
            page,
            page_size: PAGE_SIZE,
            tenant_id: tenantParam,
            path_contains: pathParam,
            status_min: statusMin === "" ? undefined : Number(statusMin),
            slow_only: slowOnly,
          },
        }),
      ]);

      setSummary(summaryResult.data);
      setEvents(eventsResult.data);
      setSelectedEvent((current) => {
        if (!current) return eventsResult.data.items?.[0] || null;
        return eventsResult.data.items?.find((item) => item.request_id === current.request_id) || eventsResult.data.items?.[0] || null;
      });
    } catch (err) {
      console.error("Erro ao carregar incidentes Ops:", err);
      setError(err?.response?.data?.detail || "Nao foi possivel carregar os incidentes agora.");
    } finally {
      setLoading(false);
    }
  }, [page, selectedPath, selectedTenant, since, slowOnly, statusMin]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function clearFilters() {
    setSelectedTenant("");
    setSelectedPath("");
    setStatusMin("");
    setSlowOnly(false);
    setQuery("");
    setPage(1);
  }

  return (
    <div className="p-6">
      <div className="mx-auto max-w-[1500px] space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-600">
              <FiAlertTriangle className="h-5 w-5" />
              Suporte operacional
            </div>
            <h1 className="mt-1 text-2xl font-bold text-slate-950">Incidentes por tenant</h1>
            <p className="mt-1 text-sm text-slate-500">
              Selecione um tenant ou rota para rastrear eventos, request_id e causa provavel.
            </p>
          </div>
          <button
            type="button"
            onClick={loadData}
            disabled={loading}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FiRefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Atualizar
          </button>
        </div>

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="grid gap-3 lg:grid-cols-[180px_160px_150px_1fr_auto]">
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Periodo</span>
              <select
                value={rangeHours}
                onChange={(event) => {
                  setRangeHours(Number(event.target.value));
                  setPage(1);
                }}
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900"
              >
                {RANGE_OPTIONS.map((option) => (
                  <option key={option.hours} value={option.hours}>{option.label}</option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</span>
              <select
                value={statusMin}
                onChange={(event) => {
                  setStatusMin(event.target.value);
                  setPage(1);
                }}
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900"
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
                  className="h-4 w-4 rounded border-slate-300 text-blue-600"
                />
                Lentos
              </label>
            </div>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Buscar no resultado</span>
              <div className="relative mt-1">
                <FiSearch className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="request_id, rota, usuario, mensagem..."
                  className="h-10 w-full rounded-lg border border-slate-300 pl-9 pr-3 text-sm text-slate-900"
                />
              </div>
            </label>

            <div className="flex items-end">
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                <FiFilter className="h-4 w-4" />
                Limpar
              </button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500">
            {selectedTenant ? <Badge className="border-blue-200 bg-blue-50 text-blue-700">Tenant: {tenantNameById.get(selectedTenant) || selectedTenant}</Badge> : null}
            {selectedPath ? <Badge className="border-blue-200 bg-blue-50 text-blue-700">Rota: {selectedPath}</Badge> : null}
            {!selectedTenant && !selectedPath ? <span>Selecione um card abaixo para afunilar a investigacao.</span> : null}
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Tenants</h2>
                <p className="text-sm text-slate-500">Clique para filtrar o historico.</p>
              </div>
              <FiUser className="h-5 w-5 text-slate-500" />
            </div>
            <div className="mt-4 grid gap-2 md:grid-cols-2">
              {(summary?.tenant_incidents || []).length === 0 ? (
                <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">Nenhum tenant com incidente.</div>
              ) : (
                summary.tenant_incidents.slice(0, 10).map((item) => (
                  <TenantCard
                    key={item.tenant_id || item.tenant_name}
                    item={item}
                    selected={(item.tenant_id || "sem_tenant") === selectedTenant}
                    onSelect={(tenant) => {
                      setSelectedTenant((current) => (current === tenant ? "" : tenant));
                      setPage(1);
                    }}
                  />
                ))
              )}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Rotas</h2>
                <p className="text-sm text-slate-500">Clique para isolar uma rota sensivel.</p>
              </div>
              <FiClock className="h-5 w-5 text-slate-500" />
            </div>
            <div className="mt-4 grid gap-2 md:grid-cols-2">
              {(summary?.route_incidents || []).length === 0 ? (
                <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">Nenhuma rota com incidente.</div>
              ) : (
                summary.route_incidents.slice(0, 10).map((item) => (
                  <RouteCard
                    key={item.path}
                    item={item}
                    selected={item.path === selectedPath}
                    onSelect={(path) => {
                      setSelectedPath((current) => (current === path ? "" : path));
                      setPage(1);
                    }}
                  />
                ))
              )}
            </div>
          </section>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Historico filtrado</h2>
                <p className="text-xs text-slate-500">
                  Mostrando {filteredEvents.length} de {events.total || 0} evento(s)
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
                <span className="text-sm text-slate-500">{page} / {totalPages}</span>
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

            <div className="divide-y divide-slate-100">
              {loading ? (
                <div className="px-4 py-10 text-center text-sm text-slate-500">Carregando incidentes...</div>
              ) : filteredEvents.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-slate-500">Nenhum evento encontrado.</div>
              ) : (
                filteredEvents.map((event) => {
                  const selected = selectedEvent?.request_id === event.request_id;
                  const tenantName = tenantNameById.get(event.tenant_id || "sem_tenant");
                  return (
                    <button
                      type="button"
                      key={`${event.request_id}-${event.created_at}`}
                      onClick={() => setSelectedEvent(event)}
                      className={`block w-full px-4 py-3 text-left transition ${selected ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge className={statusTone(event.status_code)}>{event.status_code || "erro"}</Badge>
                            <Badge className="border-slate-200 bg-slate-100 text-slate-600">{event.method || "-"}</Badge>
                            <span className="truncate font-mono text-xs font-semibold text-slate-900" title={event.path}>
                              {event.path || "-"}
                            </span>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                            <span>{formatDate(event.created_at)}</span>
                            <span>{formatMs(event.duration_ms)}</span>
                            <span>{tenantName || event.tenant_id || "sem_tenant"}</span>
                            <span>{event.user_email || event.user_id || "-"}</span>
                          </div>
                          <div className="mt-1 font-mono text-[11px] text-slate-400">{event.request_id}</div>
                        </div>
                        {event.exception_type ? (
                          <FiAlertTriangle className="mt-1 h-5 w-5 shrink-0 text-rose-500" />
                        ) : (
                          <FiCheckCircle className="mt-1 h-5 w-5 shrink-0 text-slate-400" />
                        )}
                      </div>
                      <div className="mt-2 text-xs text-slate-600">
                        {shortText(event.exception_message || event.exception_type || event.user_agent, 160)}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <EventDetail event={selectedEvent} />
        </div>
      </div>
    </div>
  );
}
