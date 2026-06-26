import { FiCheckCircle, FiEdit3 } from "react-icons/fi";

import { buildOpsTenantCommercialForm, buildOpsTenantCommercialPayload } from "../opsTenantsUtils";

import OpsTenantsBadge from "./OpsTenantsBadge";
import {
  BILLING_EDIT_OPTIONS,
  PLAN_EDIT_OPTIONS,
  SOURCE_EDIT_OPTIONS,
  TENANT_STATUS_EDIT_OPTIONS,
} from "./opsTenantsConstants";
import { billingBadge } from "./opsTenantsFormatters";

function SelectField({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function OpsTenantsCommercialEditPanel({
  tenant,
  form,
  error,
  success,
  saving,
  onChange,
  onSubmit,
}) {
  if (!tenant) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm text-slate-500">
          Selecione um tenant para editar plano e cobranca.
        </div>
      </section>
    );
  }

  const original = buildOpsTenantCommercialForm(tenant);
  const payload = buildOpsTenantCommercialPayload(original, form);
  const hasChanges = Object.keys(payload).length > 0;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <FiEdit3 className="h-4 w-4 text-blue-600" />
            Manutencao comercial
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Ajuste status, plano e cobranca sem entrar no tenant do cliente.
          </p>
        </div>
        <OpsTenantsBadge className={billingBadge(tenant.billing_status)}>
          {tenant.billing_status || "active"}
        </OpsTenantsBadge>
      </div>

      <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
        <div className="truncate text-sm font-bold text-slate-900">{tenant.name}</div>
        <div className="mt-1 truncate text-xs text-slate-500">
          {tenant.principal_user?.email || tenant.id}
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <SelectField
          label="Status tenant"
          value={form.status}
          options={TENANT_STATUS_EDIT_OPTIONS}
          onChange={(value) => onChange("status", value)}
        />
        <SelectField
          label="Plano"
          value={form.plan}
          options={PLAN_EDIT_OPTIONS}
          onChange={(value) => onChange("plan", value)}
        />
        <SelectField
          label="Cobranca"
          value={form.billing_status}
          options={BILLING_EDIT_OPTIONS}
          onChange={(value) => onChange("billing_status", value)}
        />
        <SelectField
          label="Origem"
          value={form.subscription_source}
          options={SOURCE_EDIT_OPTIONS}
          onChange={(value) => onChange("subscription_source", value)}
        />

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        ) : null}
        {success ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {success}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={!hasChanges || saving}
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FiCheckCircle className={`h-4 w-4 ${saving ? "animate-pulse" : ""}`} />
          Salvar manutencao
        </button>
      </form>
    </section>
  );
}
