import { FiEdit3 } from "react-icons/fi";

import { buildOpsTenantCommercialForm, buildOpsTenantCommercialPayload } from "../opsTenantsUtils";

import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import OpsTenantsBadge from "./OpsTenantsBadge";
import {
  BILLING_EDIT_OPTIONS,
  PLAN_EDIT_OPTIONS,
  SOURCE_EDIT_OPTIONS,
  TENANT_STATUS_EDIT_OPTIONS,
} from "./opsTenantsConstants";
import { billingBadge } from "./opsTenantsFormatters";

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
      <div className="text-sm text-slate-500 dark:text-slate-400">
        Selecione um tenant para editar plano e cobranca.
      </div>
    );
  }

  const original = buildOpsTenantCommercialForm(tenant);
  const payload = buildOpsTenantCommercialPayload(original, form);
  const hasChanges = Object.keys(payload).length > 0;

  return (
    <div>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            <FiEdit3 className="h-4 w-4 text-blue-600" />
            Manutencao comercial
          </div>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Ajuste status, plano e cobranca sem entrar no tenant do cliente.
          </p>
        </div>
        <OpsTenantsBadge className={billingBadge(tenant.billing_status)}>
          {tenant.billing_status || "active"}
        </OpsTenantsBadge>
      </div>

      <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 dark:border-slate-700 dark:bg-slate-800">
        <div className="truncate text-sm font-bold text-slate-900 dark:text-slate-100">
          {tenant.name}
        </div>
        <div className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">
          {tenant.principal_user?.email || tenant.id}
        </div>
      </div>

      <form
        id="tenant-comercial-form"
        onSubmit={onSubmit}
        noValidate
        className="mt-4 space-y-3"
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <InputCombobox
            id="tenant-comercial-status"
            label="Status tenant"
            opcoes={TENANT_STATUS_EDIT_OPTIONS}
            value={form.status}
            onChange={(value) => onChange("status", value)}
            permitirLimpar={false}
          />
          <InputCombobox
            id="tenant-comercial-plano"
            label="Plano"
            opcoes={PLAN_EDIT_OPTIONS}
            value={form.plan}
            onChange={(value) => onChange("plan", value)}
            permitirLimpar={false}
          />
          <InputCombobox
            id="tenant-comercial-cobranca"
            label="Cobranca"
            opcoes={BILLING_EDIT_OPTIONS}
            value={form.billing_status}
            onChange={(value) => onChange("billing_status", value)}
            permitirLimpar={false}
          />
          <InputCombobox
            id="tenant-comercial-origem"
            label="Origem"
            opcoes={SOURCE_EDIT_OPTIONS}
            value={form.subscription_source}
            onChange={(value) => onChange("subscription_source", value)}
            permitirLimpar={false}
          />
        </div>

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
            {error}
          </div>
        ) : null}
        {success ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">
            {success}
          </div>
        ) : null}

        <BotaoSalva
          form="tenant-comercial-form"
          disabled={!hasChanges}
          loading={saving}
          larguraTotal
        >
          Salvar manutencao
        </BotaoSalva>
      </form>
    </div>
  );
}
