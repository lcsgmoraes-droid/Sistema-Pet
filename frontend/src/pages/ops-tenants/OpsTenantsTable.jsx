import { FiDatabase, FiDownloadCloud } from "react-icons/fi";

import OpsTenantsBadge from "./OpsTenantsBadge";
import {
  billingBadge,
  catalogBadge,
  formatDate,
  formatNumber,
  shortId,
  statusBadge,
  sumObjectValues,
} from "./opsTenantsFormatters";

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
        <button
          type="button"
          onClick={() => onSelect(tenant.id)}
          className="block min-w-0 text-left"
        >
          <div className="truncate text-sm font-bold text-slate-900" title={tenant.name}>
            {tenant.name}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] text-slate-500">{shortId(tenant.id)}</span>
            <OpsTenantsBadge className={statusBadge(tenant.status)}>
              {tenant.status || "active"}
            </OpsTenantsBadge>
          </div>
        </button>
      </td>
      <td className="px-4 py-3 align-top">
        <div className="flex flex-wrap gap-2">
          <OpsTenantsBadge className="border-blue-200 bg-blue-50 text-blue-700">
            {tenant.plan || "free"}
          </OpsTenantsBadge>
          <OpsTenantsBadge className={billingBadge(tenant.billing_status)}>
            {tenant.billing_status || "active"}
          </OpsTenantsBadge>
        </div>
        <div className="mt-2 text-xs text-slate-500">
          Origem {tenant.subscription_source || "manual"} |{" "}
          {formatDate(tenant.subscription_activated_at || tenant.created_at)}
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <div
          className="max-w-[210px] truncate text-sm font-semibold text-slate-800"
          title={tenant.principal_user?.email}
        >
          {tenant.principal_user?.nome || tenant.principal_user?.email || "-"}
        </div>
        <div className="mt-1 max-w-[210px] truncate text-xs text-slate-500">
          {tenant.principal_user?.email || "sem usuario principal"}
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <div className="grid min-w-[260px] grid-cols-5 gap-2 text-xs">
          <span>
            Prod <b>{formatNumber(counts.produtos)}</b>
          </span>
          <span>
            Img <b>{formatNumber(counts.produto_imagens)}</b>
          </span>
          <span>
            Cli <b>{formatNumber(counts.clientes)}</b>
          </span>
          <span>
            Pets <b>{formatNumber(counts.pets)}</b>
          </span>
          <span>
            Vendas <b>{formatNumber(counts.vendas)}</b>
          </span>
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <OpsTenantsBadge className={catalogBadge(tenant.base_catalog)}>
          {tenant.base_catalog?.installed
            ? tenant.base_catalog?.status || "instalado"
            : "nao importado"}
        </OpsTenantsBadge>
        {tenant.base_catalog?.updated_at ? (
          <div className="mt-2 text-xs text-slate-500">
            {formatDate(tenant.base_catalog.updated_at)}
          </div>
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

export default function OpsTenantsTable({
  activeTab,
  items,
  loading,
  selectedTenant,
  previewByTenant,
  busyKey,
  onSelectTenant,
  onPreview,
  onApply,
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            {activeTab === "catalog" ? "Importacao de catalogo base" : "Tenants"}
          </h2>
          <p className="text-sm text-slate-500">
            {activeTab === "catalog"
              ? "Simulacao e aplicacao controlada por tenant."
              : "Contagens basicas, cobranca e cadastro padrao."}
          </p>
        </div>
        {loading ? (
          <OpsTenantsBadge className="border-blue-200 bg-blue-50 text-blue-700">
            carregando
          </OpsTenantsBadge>
        ) : (
          <OpsTenantsBadge className="border-slate-200 bg-slate-50 text-slate-700">
            {items.length} exibido(s)
          </OpsTenantsBadge>
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
                  onSelect={onSelectTenant}
                  onPreview={onPreview}
                  onApply={onApply}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
