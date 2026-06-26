import {
  FiAlertTriangle,
  FiCheckCircle,
  FiClock,
  FiFilter,
  FiRefreshCw,
  FiSearch,
  FiUser,
} from "react-icons/fi";

import {
  ActionableAlertsPanel,
  Badge,
  EventDetail,
  RANGE_OPTIONS,
  RouteCard,
  TenantCard,
  formatDate,
  formatMs,
  shortText,
  statusTone,
} from "./OpsIncidentesCards";

export default function OpsIncidentesView({
  loadData,
  loading,
  error,
  rangeHours,
  setRangeHours,
  setPage,
  statusMin,
  setStatusMin,
  slowOnly,
  setSlowOnly,
  requestIdFilter,
  setRequestIdFilter,
  query,
  setQuery,
  selectedTenant,
  tenantNameById,
  selectedPath,
  clearFilters,
  summary,
  applyAlertFilter,
  setSelectedTenant,
  setSelectedPath,
  filteredEvents,
  events,
  page,
  totalPages,
  setSelectedEvent,
  selectedEvent,
  auditTrail,
  auditLoading,
}) {
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
          <div className="grid gap-3 lg:grid-cols-[180px_160px_150px_minmax(220px,0.8fr)_1fr_auto]">
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
                className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900"
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
                Status
              </span>
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
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Request ID
              </span>
              <div className="relative mt-1">
                <FiSearch className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                <input
                  value={requestIdFilter}
                  onChange={(event) => {
                    setRequestIdFilter(event.target.value);
                    setPage(1);
                  }}
                  placeholder="request_id exato"
                  className="h-10 w-full rounded-lg border border-slate-300 pl-9 pr-3 font-mono text-sm text-slate-900"
                />
              </div>
            </label>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Buscar no resultado
              </span>
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
            {selectedTenant ? (
              <Badge className="border-blue-200 bg-blue-50 text-blue-700">
                Tenant: {tenantNameById.get(selectedTenant) || selectedTenant}
              </Badge>
            ) : null}
            {selectedPath ? (
              <Badge className="border-blue-200 bg-blue-50 text-blue-700">
                Rota: {selectedPath}
              </Badge>
            ) : null}
            {requestIdFilter ? (
              <Badge className="border-blue-200 bg-blue-50 font-mono text-blue-700">
                Request: {requestIdFilter}
              </Badge>
            ) : null}
            {!selectedTenant && !selectedPath ? (
              <span>Selecione um card abaixo para afunilar a investigacao.</span>
            ) : null}
          </div>
        </section>

        <ActionableAlertsPanel
          alerts={summary?.actionable_alerts || []}
          notifications={summary?.ops_notifications}
          recoveryActions={summary?.recovery_actions || []}
          onApply={applyAlertFilter}
        />

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
                <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">
                  Nenhum tenant com incidente.
                </div>
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
                <div className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">
                  Nenhuma rota com incidente.
                </div>
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

            <div className="divide-y divide-slate-100">
              {loading ? (
                <div className="px-4 py-10 text-center text-sm text-slate-500">
                  Carregando incidentes...
                </div>
              ) : filteredEvents.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-slate-500">
                  Nenhum evento encontrado.
                </div>
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
                            <Badge className={statusTone(event.status_code)}>
                              {event.status_code || "erro"}
                            </Badge>
                            <Badge className="border-slate-200 bg-slate-100 text-slate-600">
                              {event.method || "-"}
                            </Badge>
                            <span
                              className="truncate font-mono text-xs font-semibold text-slate-900"
                              title={event.path}
                            >
                              {event.path || "-"}
                            </span>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                            <span>{formatDate(event.created_at)}</span>
                            <span>{formatMs(event.duration_ms)}</span>
                            <span>{tenantName || event.tenant_id || "sem_tenant"}</span>
                            <span>{event.user_email || event.user_id || "-"}</span>
                          </div>
                          <div className="mt-1 font-mono text-[11px] text-slate-400">
                            {event.request_id}
                          </div>
                        </div>
                        {event.exception_type ? (
                          <FiAlertTriangle className="mt-1 h-5 w-5 shrink-0 text-rose-500" />
                        ) : (
                          <FiCheckCircle className="mt-1 h-5 w-5 shrink-0 text-slate-400" />
                        )}
                      </div>
                      <div className="mt-2 text-xs text-slate-600">
                        {shortText(
                          event.exception_message || event.exception_type || event.user_agent,
                          160,
                        )}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <EventDetail event={selectedEvent} auditTrail={auditTrail} auditLoading={auditLoading} />
        </div>
      </div>
    </div>
  );
}
