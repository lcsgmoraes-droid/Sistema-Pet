import { FiCopy, FiFilter, FiZap } from "react-icons/fi";

export const PAGE_SIZE = 80;

export const RANGE_OPTIONS = [
  { label: "Ultimas 2h", hours: 2 },
  { label: "24h", hours: 24 },
  { label: "7 dias", hours: 168 },
  { label: "30 dias", hours: 720 },
];

export function sinceFromHours(hours) {
  return new Date(Date.now() - Number(hours || 24) * 60 * 60 * 1000).toISOString();
}

export function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  });
}

export function formatMs(value) {
  const number = Number(value || 0);
  return `${number.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} ms`;
}

export function shortText(value, max = 120) {
  const text = String(value || "-");
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

export function statusTone(status) {
  const code = Number(status || 0);
  if (code >= 500) return "border-rose-200 bg-rose-100 text-rose-700";
  if (code >= 400) return "border-amber-200 bg-amber-100 text-amber-700";
  if (code >= 200) return "border-emerald-200 bg-emerald-100 text-emerald-700";
  return "border-slate-200 bg-slate-100 text-slate-600";
}

export function severityTone(severity) {
  if (severity === "critical") return "border-rose-200 bg-rose-50 text-rose-800";
  if (severity === "warning") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-slate-200 bg-white text-slate-800";
}

export function alertTone(tone) {
  if (tone === "red") return "border-rose-200 bg-rose-50 text-rose-900";
  if (tone === "amber") return "border-amber-200 bg-amber-50 text-amber-900";
  if (tone === "green") return "border-emerald-200 bg-emerald-50 text-emerald-900";
  return "border-blue-200 bg-blue-50 text-blue-900";
}

export function severityLabel(severity) {
  if (severity === "critical") return "critico";
  if (severity === "warning") return "atencao";
  if (severity === "ok") return "ok";
  return severity || "info";
}

export function Badge({ children, className = "" }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${className}`}
    >
      {children}
    </span>
  );
}

export function copyToClipboard(value) {
  if (!value) return;
  navigator.clipboard?.writeText(String(value)).catch(() => {});
}

export function TenantCard({ item, selected, onSelect }) {
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
        <span>
          5xx: <b>{item.errors_5xx}</b>
        </span>
        <span>
          Lentas: <b>{item.slow_requests}</b>
        </span>
        <span>{formatDate(item.latest_at)}</span>
      </div>
    </button>
  );
}

export function RouteCard({ item, selected, onSelect }) {
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
        <span>
          5xx: <b>{item.errors_5xx}</b>
        </span>
        <span>
          Lentas: <b>{item.slow_requests}</b>
        </span>
        <span>
          Media: <b>{formatMs(item.avg_duration_ms)}</b>
        </span>
      </div>
    </button>
  );
}

export function ActionableAlertsPanel({ alerts, notifications, recoveryActions, onApply }) {
  const items = alerts || [];
  const activeAlerts = notifications?.open ?? 0;
  const criticalAlerts = notifications?.critical_open ?? 0;
  const recoveries = recoveryActions?.length ?? 0;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <FiZap className="h-4 w-4 text-blue-600" />
            Alertas automaticos
          </div>
          <p className="mt-1 text-sm text-slate-500">
            O sistema cruza tenant, rota, lentidao e erro repetido para sugerir a proxima acao.
          </p>
        </div>
        <Badge className="border-blue-200 bg-blue-50 text-blue-700">{items.length} alerta(s)</Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Notificacoes ativas
          </div>
          <div className="mt-1 text-xl font-bold text-slate-900">{activeAlerts}</div>
        </div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-rose-600">
            Criticas abertas
          </div>
          <div className="mt-1 text-xl font-bold text-rose-700">{criticalAlerts}</div>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
            Acoes recuperacao
          </div>
          <div className="mt-1 text-xl font-bold text-emerald-800">{recoveries}</div>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Nenhum alerta acionavel no periodo selecionado.
        </div>
      ) : (
        <div className="mt-4 grid gap-3 xl:grid-cols-2">
          {items.slice(0, 6).map((alert) => (
            <button
              type="button"
              key={alert.id || `${alert.scope}-${alert.title}`}
              onClick={() => onApply(alert)}
              className={`rounded-lg border px-4 py-3 text-left transition hover:shadow-sm ${alertTone(alert.tone)}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className="border-white bg-white/80 text-slate-800">
                      {severityLabel(alert.severity)}
                    </Badge>
                    <span className="text-sm font-bold">{alert.title}</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-600">{alert.detail}</p>
                  <p className="mt-2 text-xs font-semibold text-slate-800">{alert.action}</p>
                </div>
                <FiFilter className="mt-1 h-4 w-4 shrink-0 opacity-70" />
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
                {alert.tenant_name ? <span>{alert.tenant_name}</span> : null}
                {alert.path ? <span className="font-mono">{alert.path}</span> : null}
                {alert.request_id ? <span className="font-mono">{alert.request_id}</span> : null}
                {alert.latest_at ? <span>{formatDate(alert.latest_at)}</span> : null}
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export function EventDetail({ event, auditTrail = [], auditLoading = false }) {
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
          <div
            key={label}
            className="grid grid-cols-[110px_1fr] gap-3 rounded-md bg-slate-50 px-3 py-2 text-sm"
          >
            <span className="font-semibold text-slate-500">{label}</span>
            <span className="min-w-0 break-words font-mono text-xs text-slate-800">{value}</span>
          </div>
        ))}
      </div>

      {event.exception_type || event.exception_message ? (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <div className="font-bold">{event.exception_type || "Erro"}</div>
          <div className="mt-1 whitespace-pre-wrap text-xs">
            {event.exception_message || "Sem mensagem detalhada."}
          </div>
        </div>
      ) : null}

      <div className="mt-4 border-t border-slate-100 pt-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Auditoria do request</h3>
            <p className="mt-1 text-xs text-slate-500">
              Eventos de negocio vinculados ao mesmo request_id.
            </p>
          </div>
          <Badge className="border-slate-200 bg-slate-50 text-slate-600">{auditTrail.length}</Badge>
        </div>

        {auditLoading ? (
          <div className="mt-3 rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">
            Carregando auditoria...
          </div>
        ) : auditTrail.length === 0 ? (
          <div className="mt-3 rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-500">
            Nenhum evento de auditoria encontrado para este request.
          </div>
        ) : (
          <div className="mt-3 divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
            {auditTrail.slice(0, 8).map((item) => (
              <div key={item.id} className="bg-white px-3 py-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-slate-900">{item.action}</span>
                  <span className="text-xs text-slate-500">{formatDate(item.timestamp)}</span>
                </div>
                <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span>{item.entity_type || "sem_entidade"}</span>
                  {item.entity_id ? <span>#{item.entity_id}</span> : null}
                  {item.user_id ? <span>user {item.user_id}</span> : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
