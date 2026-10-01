import { FiEdit3 } from "react-icons/fi";

import { isBillingAttention } from "../opsTenantsUtils";

import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import OpsTenantsBadge from "./OpsTenantsBadge";
import OpsTenantsCommercialEditPanel from "./OpsTenantsCommercialEditPanel";
import OpsTenantBillingOfferPanel from "./OpsTenantBillingOfferPanel";
import {
  billingBadge,
  formatDate,
  shortId,
  tenantPlanosSegmento,
} from "./opsTenantsFormatters";

export default function OpsTenantsBillingTab({
  items,
  loading,
  selectedTenant,
  modalOpen,
  editForm,
  editError,
  editSuccess,
  saving,
  onSelectTenant,
  onCloseManage,
  onEditChange,
  onEditSubmit,
  offerForm,
  offers,
  offersLoading,
  offerCreating,
  offerError,
  offerSuccess,
  offerPublicUrl,
  planosCatalogo,
  onOfferChange,
  onOfferSegmentChange,
  onOfferToggleModule,
  onOfferSubmit,
}) {
  return (
    <>
      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">Planos e pagamentos</h2>
            <p className="text-sm text-slate-500">
              Status comercial dos tenants ativos no filtro atual.
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
          <table className="min-w-[1080px] w-full divide-y divide-slate-200 text-left">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-bold">Acao</th>
                <th className="px-4 py-3 font-bold">Tenant</th>
                <th className="px-4 py-3 font-bold">Plano</th>
                <th className="px-4 py-3 font-bold">Pagamento</th>
                <th className="px-4 py-3 font-bold">Origem</th>
                <th className="px-4 py-3 font-bold">Usuario principal</th>
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
                items.map((tenant) => {
                  const attention = isBillingAttention(tenant.billing_status);
                  const selected = selectedTenant?.id === tenant.id;
                  return (
                    <tr
                      key={tenant.id}
                      className={
                        selected
                          ? "bg-blue-50"
                          : attention
                            ? "bg-amber-50"
                            : "bg-white hover:bg-slate-50"
                      }
                    >
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => onSelectTenant(tenant.id)}
                          className="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                        >
                          <FiEdit3 className="h-4 w-4" aria-hidden="true" />
                          Editar
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-bold text-slate-900">{tenant.name}</div>
                        <div className="mt-1 font-mono text-xs text-slate-500">
                          {shortId(tenant.id)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {tenantPlanosSegmento(tenant).map(({ label, codigo }) => (
                            <OpsTenantsBadge
                              key={label || codigo}
                              className="border-blue-200 bg-blue-50 text-blue-700"
                            >
                              {label ? `${label}: ${codigo}` : codigo}
                            </OpsTenantsBadge>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <OpsTenantsBadge
                          className={
                            attention
                              ? "border-amber-200 bg-amber-100 text-amber-800"
                              : billingBadge(tenant.billing_status)
                          }
                        >
                          {tenant.billing_status || "active"}
                        </OpsTenantsBadge>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600">
                        <div>{tenant.subscription_source || "manual"}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {formatDate(tenant.subscription_activated_at || tenant.created_at)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="max-w-[260px] truncate text-sm font-semibold text-slate-800">
                          {tenant.principal_user?.nome || tenant.principal_user?.email || "-"}
                        </div>
                        <div className="mt-1 max-w-[260px] truncate text-xs text-slate-500">
                          {tenant.principal_user?.email || "sem usuario principal"}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {modalOpen && selectedTenant ? (
        <ModalPadrao titulo={`Manutencao comercial — ${selectedTenant.name}`} tamanho="grande" onFechar={onCloseManage}>
          <div className="space-y-4">
            <OpsTenantBillingOfferPanel
              tenant={selectedTenant}
              form={offerForm}
              offers={offers}
              loadingOffers={offersLoading}
              creating={offerCreating}
              error={offerError}
              success={offerSuccess}
              publicUrl={offerPublicUrl}
              planosCatalogo={planosCatalogo}
              onChange={onOfferChange}
              onSegmentChange={onOfferSegmentChange}
              onToggleModule={onOfferToggleModule}
              onSubmit={onOfferSubmit}
            />
            <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
              <OpsTenantsCommercialEditPanel
                tenant={selectedTenant}
                form={editForm}
                error={editError}
                success={editSuccess}
                saving={saving}
                onChange={onEditChange}
                onSubmit={onEditSubmit}
              />
            </div>
          </div>
        </ModalPadrao>
      ) : null}
    </>
  );
}
