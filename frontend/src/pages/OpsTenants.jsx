import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FiAlertTriangle,
  FiBox,
  FiCheckCircle,
  FiDatabase,
  FiDownloadCloud,
  FiRefreshCw,
  FiSearch,
  FiShield,
  FiUsers,
} from "react-icons/fi";

import api from "../api";

const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "active", label: "Ativos" },
  { value: "inactive", label: "Inativos" },
  { value: "trial", label: "Trial" },
  { value: "suspended", label: "Suspensos" },
];

function formatNumber(value) {
  return Number(value || 0).toLocaleString("pt-BR");
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

function shortId(value) {
  const text = String(value || "");
  return text ? text.slice(0, 8) : "-";
}

function extractError(err, fallback) {
  return err?.response?.data?.detail || err?.message || fallback;
}

function sumCounts(items, key) {
  return (items || []).reduce((total, item) => total + Number(item?.counts?.[key] || 0), 0);
}

function sumObjectValues(value) {
  return Object.values(value || {}).reduce((total, current) => total + Number(current || 0), 0);
}

function statusBadge(status) {
  const normalized = String(status || "").toLowerCase();
  if (["active", "ativo"].includes(normalized)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (["suspended", "blocked", "bloqueado"].includes(normalized)) {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  if (["trial"].includes(normalized)) {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function billingBadge(status) {
  const normalized = String(status || "").toLowerCase();
  if (["active", "paid", "ok", "em_dia"].includes(normalized)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (["past_due", "overdue", "late", "inadimplente"].includes(normalized)) {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function catalogBadge(catalog) {
  if (catalog?.installed) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

function Badge({ children, className = "" }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${className}`}>
      {children}
    </span>
  );
}

function MetricCard({ icon: Icon, label, value, detail, tone = "slate" }) {
  const tones = {
    blue: "border-blue-200 bg-blue-50 text-blue-900",
    green: "border-emerald-200 bg-emerald-50 text-emerald-900",
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    slate: "border-slate-200 bg-white text-slate-900",
  };
  return (
    <div className={`rounded-lg border p-4 shadow-sm ${tones[tone] || tones.slate}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
        <Icon className="h-5 w-5 text-current opacity-70" />
      </div>
      <div className="mt-3 text-2xl font-bold">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{detail}</div>
    </div>
  );
}

function ImportSummary({ title, values }) {
  const entries = Object.entries(values || {}).filter(([, value]) => Number(value || 0) > 0);
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{title}</div>
      {entries.length === 0 ? (
        <div className="mt-2 text-sm text-slate-500">Nenhum item.</div>
      ) : (
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-700">
          {entries.map(([key, value]) => (
            <div key={key} className="flex items-center justify-between gap-2 rounded-md bg-white px-2 py-1.5">
              <span className="truncate">{key}</span>
              <b>{formatNumber(value)}</b>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ImportResultPanel({ tenant, preview, applyResult, actionError }) {
  if (!tenant) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm text-slate-500">Selecione um tenant para ver detalhes.</div>
      </section>
    );
  }

  const result = applyResult || preview;
  const source = applyResult ? "Ultima importacao aplicada" : "Ultima simulacao";

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <FiShield className="h-4 w-4 text-blue-600" />
            Catalogo base
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {tenant.name} recebe uma copia separada da loja base, com estoque e precos operacionais zerados.
          </p>
        </div>
        <Badge className={catalogBadge(tenant.base_catalog)}>
          {tenant.base_catalog?.installed ? "instalado" : "nao importado"}
        </Badge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Tenant</div>
          <div className="mt-1 truncate text-sm font-semibold text-slate-900">{tenant.name}</div>
          <div className="mt-1 font-mono text-xs text-slate-500">{tenant.id}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Usuario principal</div>
          <div className="mt-1 truncate text-sm font-semibold text-slate-900">
            {tenant.principal_user?.nome || tenant.principal_user?.email || "-"}
          </div>
          <div className="mt-1 truncate text-xs text-slate-500">{tenant.principal_user?.email || "-"}</div>
        </div>
      </div>

      {actionError ? (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-700">
          {actionError}
        </div>
      ) : null}

      {!result ? (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-3 py-3 text-sm text-blue-800">
          Rode uma simulacao para conferir quantos departamentos, categorias, marcas, produtos e imagens seriam criados.
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
            <div>
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{source}</div>
              <div className="mt-1 text-sm font-semibold text-slate-900">
                {result.ok ? "Sem erro retornado" : "Importacao com pendencias"}
              </div>
            </div>
            <Badge className={result.ok ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}>
              {result.dry_run ? "simulacao" : "aplicado"}
            </Badge>
          </div>

          <div className="grid gap-3">
            <ImportSummary title={result.dry_run ? "Seriam criados" : "Criados"} values={result.dry_run ? result.would_create : result.created} />
            <ImportSummary title="Ignorados por ja existirem" values={result.skipped} />
          </div>

          {(result.warnings || []).length ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-800">
              {(result.warnings || []).map((warning) => (
                <div key={warning}>{warning}</div>
              ))}
            </div>
          ) : null}

          {(result.errors || []).length ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-700">
              {(result.errors || []).map((error) => (
                <div key={error}>{error}</div>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

function TenantRow({
  tenant,
  selected,
  preview,
  applying,
  previewing,
  onSelect,
  onPreview,
  onApply,
}) {
  const counts = tenant.counts || {};
  const canApply = Boolean(preview?.ok) && !applying && !previewing;
  const previewTotal = sumObjectValues(preview?.would_create);

  return (
    <tr className={selected ? "bg-blue-50" : "bg-white hover:bg-slate-50"}>
      <td className="w-[28%] px-4 py-3 align-top">
        <button type="button" onClick={() => onSelect(tenant.id)} className="block min-w-0 text-left">
          <div className="truncate text-sm font-bold text-slate-900" title={tenant.name}>
            {tenant.name}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] text-slate-500">{shortId(tenant.id)}</span>
            <Badge className={statusBadge(tenant.status)}>{tenant.status || "active"}</Badge>
          </div>
        </button>
      </td>
      <td className="px-4 py-3 align-top">
        <div className="flex flex-wrap gap-2">
          <Badge className="border-blue-200 bg-blue-50 text-blue-700">{tenant.plan || "free"}</Badge>
          <Badge className={billingBadge(tenant.billing_status)}>{tenant.billing_status || "active"}</Badge>
        </div>
        <div className="mt-2 text-xs text-slate-500">
          Origem {tenant.subscription_source || "manual"} | {formatDate(tenant.subscription_activated_at || tenant.created_at)}
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <div className="max-w-[210px] truncate text-sm font-semibold text-slate-800" title={tenant.principal_user?.email}>
          {tenant.principal_user?.nome || tenant.principal_user?.email || "-"}
        </div>
        <div className="mt-1 max-w-[210px] truncate text-xs text-slate-500">
          {tenant.principal_user?.email || "sem usuario principal"}
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <div className="grid min-w-[260px] grid-cols-5 gap-2 text-xs">
          <span>Prod <b>{formatNumber(counts.produtos)}</b></span>
          <span>Cli <b>{formatNumber(counts.clientes)}</b></span>
          <span>Pets <b>{formatNumber(counts.pets)}</b></span>
          <span>Vendas <b>{formatNumber(counts.vendas)}</b></span>
          <span>Users <b>{formatNumber(counts.usuarios)}</b></span>
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <Badge className={catalogBadge(tenant.base_catalog)}>
          {tenant.base_catalog?.installed ? tenant.base_catalog?.status || "instalado" : "nao importado"}
        </Badge>
        {tenant.base_catalog?.updated_at ? (
          <div className="mt-2 text-xs text-slate-500">{formatDate(tenant.base_catalog.updated_at)}</div>
        ) : null}
      </td>
      <td className="px-4 py-3 align-top">
        <div className="flex min-w-[230px] flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onPreview(tenant)}
            disabled={previewing || applying}
            className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            title="Simular importacao"
          >
            <FiDatabase className={`h-4 w-4 ${previewing ? "animate-pulse" : ""}`} />
            Simular
          </button>
          <button
            type="button"
            onClick={() => onApply(tenant)}
            disabled={!canApply}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-blue-600 px-3 text-xs font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            title={preview?.ok ? "Aplicar importacao" : "Rode a simulacao primeiro"}
          >
            <FiDownloadCloud className={`h-4 w-4 ${applying ? "animate-bounce" : ""}`} />
            Importar catalogo base
          </button>
        </div>
        {preview ? (
          <div className="mt-2 text-xs text-slate-500">
            Simulacao: {formatNumber(previewTotal)} novo(s) item(ns)
          </div>
        ) : null}
      </td>
    </tr>
  );
}

export default function OpsTenants() {
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [selectedTenantId, setSelectedTenantId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [previewByTenant, setPreviewByTenant] = useState({});
  const [applyByTenant, setApplyByTenant] = useState({});
  const [busyKey, setBusyKey] = useState("");

  const loadTenants = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/admin/tenants", {
        params: {
          search: search.trim() || undefined,
          status: status || undefined,
          limit: 100,
        },
      });
      const nextItems = response.data?.items || [];
      setItems(nextItems);
      setSummary(response.data?.summary || null);
      setSelectedTenantId((current) => current || nextItems[0]?.id || "");
    } catch (err) {
      console.error("Erro ao carregar tenants Ops:", err);
      setError(extractError(err, "Nao foi possivel carregar os tenants agora."));
    } finally {
      setLoading(false);
    }
  }, [search, status]);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  const selectedTenant = useMemo(
    () => items.find((item) => item.id === selectedTenantId) || items[0] || null,
    [items, selectedTenantId],
  );

  const totals = useMemo(
    () => ({
      tenants: summary?.total ?? items.length,
      active: summary?.active ?? items.filter((item) => ["active", "ativo"].includes(String(item.status || "").toLowerCase())).length,
      withCatalog: summary?.with_base_catalog ?? items.filter((item) => item.base_catalog?.installed).length,
      products: sumCounts(items, "produtos"),
    }),
    [items, summary],
  );

  async function handlePreview(tenant) {
    setBusyKey(`preview:${tenant.id}`);
    setActionError("");
    setSelectedTenantId(tenant.id);
    try {
      const response = await api.post(`/admin/tenants/${tenant.id}/catalog-import/preview`);
      setPreviewByTenant((current) => ({ ...current, [tenant.id]: response.data }));
      setApplyByTenant((current) => {
        const next = { ...current };
        delete next[tenant.id];
        return next;
      });
    } catch (err) {
      setActionError(extractError(err, "Nao foi possivel simular a importacao."));
    } finally {
      setBusyKey("");
    }
  }

  async function handleApply(tenant) {
    const preview = previewByTenant[tenant.id];
    if (!preview?.ok) {
      setSelectedTenantId(tenant.id);
      setActionError("Rode uma simulacao valida antes de aplicar a importacao.");
      return;
    }

    setBusyKey(`apply:${tenant.id}`);
    setActionError("");
    setSelectedTenantId(tenant.id);
    try {
      const response = await api.post(`/admin/tenants/${tenant.id}/catalog-import/apply`, { confirm: true });
      setApplyByTenant((current) => ({ ...current, [tenant.id]: response.data }));
      await loadTenants();
    } catch (err) {
      setActionError(extractError(err, "Nao foi possivel aplicar a importacao."));
    } finally {
      setBusyKey("");
    }
  }

  return (
    <div className="p-6">
      <div className="mx-auto max-w-[1600px] space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-600">
              <FiUsers className="h-5 w-5" />
              Gestao de tenants
            </div>
            <h1 className="mt-1 text-2xl font-bold text-slate-950">Clientes e catalogo base</h1>
            <p className="mt-1 text-sm text-slate-500">
              Visao operacional dos tenants e comando controlado para copiar o cadastro base da loja Lucas.
            </p>
          </div>
          <button
            type="button"
            onClick={loadTenants}
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

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard icon={FiUsers} label="Tenants" value={formatNumber(totals.tenants)} detail="Resultado do filtro atual" tone="slate" />
          <MetricCard icon={FiCheckCircle} label="Ativos" value={formatNumber(totals.active)} detail="Clientes liberados para uso" tone="green" />
          <MetricCard icon={FiBox} label="Com catalogo base" value={formatNumber(totals.withCatalog)} detail="Ja receberam o pacote padrao" tone="blue" />
          <MetricCard icon={FiDatabase} label="Produtos somados" value={formatNumber(totals.products)} detail="Total visivel nesta lista" tone="amber" />
        </div>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[260px] flex-1">
              <FiSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por nome ou tenant id"
                className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
            </div>
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[1fr_410px]">
          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Tenants</h2>
                <p className="text-sm text-slate-500">Contagens basicas, cobranca e importacao do cadastro padrao.</p>
              </div>
              {loading ? (
                <Badge className="border-blue-200 bg-blue-50 text-blue-700">carregando</Badge>
              ) : (
                <Badge className="border-slate-200 bg-slate-50 text-slate-700">{items.length} exibido(s)</Badge>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-[1180px] w-full divide-y divide-slate-200 text-left">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-bold">Tenant</th>
                    <th className="px-4 py-3 font-bold">Plano</th>
                    <th className="px-4 py-3 font-bold">Principal</th>
                    <th className="px-4 py-3 font-bold">Cadastros</th>
                    <th className="px-4 py-3 font-bold">Catalogo</th>
                    <th className="px-4 py-3 font-bold">Acoes</th>
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
                    items.map((tenant) => (
                      <TenantRow
                        key={tenant.id}
                        tenant={tenant}
                        selected={selectedTenant?.id === tenant.id}
                        preview={previewByTenant[tenant.id]}
                        applying={busyKey === `apply:${tenant.id}`}
                        previewing={busyKey === `preview:${tenant.id}`}
                        onSelect={setSelectedTenantId}
                        onPreview={handlePreview}
                        onApply={handleApply}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <div className="space-y-4">
            <ImportResultPanel
              tenant={selectedTenant}
              preview={selectedTenant ? previewByTenant[selectedTenant.id] : null}
              applyResult={selectedTenant ? applyByTenant[selectedTenant.id] : null}
              actionError={actionError}
            />

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
                <FiAlertTriangle className="h-4 w-4 text-amber-600" />
                Guardrails do MVP
              </div>
              <div className="mt-3 space-y-2 text-sm text-slate-600">
                <p>O comando copia dados para outro tenant, mantendo cada cliente separado.</p>
                <p>Estoque, custo, margem, fornecedores e precos operacionais entram zerados ou vazios pela rotina de catalogo base.</p>
                <p>A importacao real so fica habilitada depois de uma simulacao sem erro.</p>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
