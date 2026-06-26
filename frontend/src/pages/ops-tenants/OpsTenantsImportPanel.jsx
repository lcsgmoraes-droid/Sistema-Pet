import { FiShield } from "react-icons/fi";

import OpsTenantsBadge from "./OpsTenantsBadge";
import { catalogBadge, formatNumber } from "./opsTenantsFormatters";

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
            <div
              key={key}
              className="flex items-center justify-between gap-2 rounded-md bg-white px-2 py-1.5"
            >
              <span className="truncate">{key}</span>
              <b>{formatNumber(value)}</b>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function OpsTenantsImportPanel({ tenant, preview, applyResult, actionError }) {
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
            {tenant.name} recebe uma copia separada da loja base, com estoque e precos operacionais
            zerados.
          </p>
        </div>
        <OpsTenantsBadge className={catalogBadge(tenant.base_catalog)}>
          {tenant.base_catalog?.installed ? "instalado" : "nao importado"}
        </OpsTenantsBadge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Tenant</div>
          <div className="mt-1 truncate text-sm font-semibold text-slate-900">{tenant.name}</div>
          <div className="mt-1 font-mono text-xs text-slate-500">{tenant.id}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Usuario principal
          </div>
          <div className="mt-1 truncate text-sm font-semibold text-slate-900">
            {tenant.principal_user?.nome || tenant.principal_user?.email || "-"}
          </div>
          <div className="mt-1 truncate text-xs text-slate-500">
            {tenant.principal_user?.email || "-"}
          </div>
        </div>
      </div>

      {actionError ? (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-700">
          {actionError}
        </div>
      ) : null}

      {!result ? (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-3 py-3 text-sm text-blue-800">
          Rode uma simulacao para conferir quantos departamentos, categorias, marcas, produtos e
          imagens seriam criados.
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
            <div>
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
                {source}
              </div>
              <div className="mt-1 text-sm font-semibold text-slate-900">
                {result.ok ? "Sem erro retornado" : "Importacao com pendencias"}
              </div>
            </div>
            <OpsTenantsBadge
              className={
                result.ok
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-rose-200 bg-rose-50 text-rose-700"
              }
            >
              {result.dry_run ? "simulacao" : "aplicado"}
            </OpsTenantsBadge>
          </div>

          <div className="grid gap-3">
            <ImportSummary
              title={result.dry_run ? "Seriam criados" : "Criados"}
              values={result.dry_run ? result.would_create : result.created}
            />
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
