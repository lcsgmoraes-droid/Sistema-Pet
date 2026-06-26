import { useCallback, useEffect, useMemo, useState } from "react";

import api from "../api";

import { PAGE_SIZE, sinceFromHours } from "./opsIncidentes/OpsIncidentesCards";
import OpsIncidentesView from "./opsIncidentes/OpsIncidentesView";

export default function OpsIncidentes() {
  const [rangeHours, setRangeHours] = useState(24);
  const [selectedTenant, setSelectedTenant] = useState("");
  const [selectedPath, setSelectedPath] = useState("");
  const [statusMin, setStatusMin] = useState("");
  const [slowOnly, setSlowOnly] = useState(false);
  const [requestIdFilter, setRequestIdFilter] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState({ items: [], total: 0 });
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [auditTrail, setAuditTrail] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);
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
    const requestParam = requestIdFilter.trim() || undefined;

    try {
      const [summaryResult, eventsResult] = await Promise.all([
        api.get("/admin/observabilidade/ops-summary", { params: { since } }),
        api.get("/admin/observabilidade/error-events", {
          params: {
            since,
            page,
            page_size: PAGE_SIZE,
            tenant_id: tenantParam,
            request_id: requestParam,
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
        return (
          eventsResult.data.items?.find((item) => item.request_id === current.request_id) ||
          eventsResult.data.items?.[0] ||
          null
        );
      });
    } catch (err) {
      console.error("Erro ao carregar incidentes Ops:", err);
      setError(err?.response?.data?.detail || "Nao foi possivel carregar os incidentes agora.");
    } finally {
      setLoading(false);
    }
  }, [page, requestIdFilter, selectedPath, selectedTenant, since, slowOnly, statusMin]);

  useEffect(() => {
    const requestId = selectedEvent?.request_id;
    if (!requestId) {
      setAuditTrail([]);
      return undefined;
    }

    let cancelled = false;
    setAuditLoading(true);
    api
      .get("/admin/observabilidade/audit-events", {
        params: {
          request_id: requestId,
          tenant_id: selectedEvent.tenant_id || undefined,
          limit: 40,
        },
      })
      .then((response) => {
        if (!cancelled) setAuditTrail(response.data.items || []);
      })
      .catch(() => {
        if (!cancelled) setAuditTrail([]);
      })
      .finally(() => {
        if (!cancelled) setAuditLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedEvent]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function clearFilters() {
    setSelectedTenant("");
    setSelectedPath("");
    setStatusMin("");
    setSlowOnly(false);
    setRequestIdFilter("");
    setQuery("");
    setPage(1);
  }

  function applyAlertFilter(alert) {
    const tenantFilter = alert?.tenant_filter || alert?.tenant_id || "";
    setSelectedTenant(tenantFilter);
    setSelectedPath(alert?.path || "");
    setStatusMin(Number(alert?.errors_5xx || 0) > 0 ? "500" : "");
    setSlowOnly(Number(alert?.slow_requests || 0) > 0 && Number(alert?.errors_5xx || 0) === 0);
    setRequestIdFilter(alert?.request_id || "");
    setQuery("");
    setPage(1);
  }

  return (
    <OpsIncidentesView
      loadData={loadData}
      loading={loading}
      error={error}
      rangeHours={rangeHours}
      setRangeHours={setRangeHours}
      setPage={setPage}
      statusMin={statusMin}
      setStatusMin={setStatusMin}
      slowOnly={slowOnly}
      setSlowOnly={setSlowOnly}
      requestIdFilter={requestIdFilter}
      setRequestIdFilter={setRequestIdFilter}
      query={query}
      setQuery={setQuery}
      selectedTenant={selectedTenant}
      tenantNameById={tenantNameById}
      selectedPath={selectedPath}
      clearFilters={clearFilters}
      summary={summary}
      applyAlertFilter={applyAlertFilter}
      setSelectedTenant={setSelectedTenant}
      setSelectedPath={setSelectedPath}
      filteredEvents={filteredEvents}
      events={events}
      page={page}
      totalPages={totalPages}
      setSelectedEvent={setSelectedEvent}
      selectedEvent={selectedEvent}
      auditTrail={auditTrail}
      auditLoading={auditLoading}
    />
  );
}
