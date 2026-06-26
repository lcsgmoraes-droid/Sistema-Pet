import { FiBox, FiCheckCircle, FiCreditCard, FiDatabase, FiUsers } from "react-icons/fi";

import OpsTenantsBillingTab from "./OpsTenantsBillingTab";
import OpsTenantsFilters from "./OpsTenantsFilters";
import OpsTenantsGuardrailsPanel from "./OpsTenantsGuardrailsPanel";
import OpsTenantsHeader from "./OpsTenantsHeader";
import OpsTenantsImportPanel from "./OpsTenantsImportPanel";
import OpsTenantsMetricCard from "./OpsTenantsMetricCard";
import OpsTenantsTable from "./OpsTenantsTable";
import OpsTenantsTabs from "./OpsTenantsTabs";
import OpsTenantsUsageTab from "./OpsTenantsUsageTab";
import { formatNumber } from "./opsTenantsFormatters";
import useOpsTenantsController from "./useOpsTenantsController";

export default function OpsTenantsPage() {
  const {
    actionError,
    activeTab,
    applyByTenant,
    busyKey,
    commercialError,
    commercialForm,
    commercialSaving,
    commercialSuccess,
    error,
    handleApply,
    handleCommercialChange,
    handleCommercialSubmit,
    handlePreview,
    items,
    loadTenants,
    loading,
    previewByTenant,
    search,
    selectedTenant,
    setActiveTab,
    setSearch,
    setSelectedTenantId,
    setStatus,
    showTenantTable,
    status,
    tabSummaries,
    totals,
  } = useOpsTenantsController();

  return (
    <div className="p-6">
      <div className="mx-auto max-w-[1600px] space-y-5">
        <OpsTenantsHeader loading={loading} onRefresh={loadTenants} />

        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <OpsTenantsMetricCard
            icon={FiUsers}
            label="Tenants"
            value={formatNumber(totals.tenants)}
            detail="Resultado do filtro atual"
            tone="slate"
          />
          <OpsTenantsMetricCard
            icon={FiCheckCircle}
            label="Ativos"
            value={formatNumber(totals.active)}
            detail="Clientes liberados para uso"
            tone="green"
          />
          <OpsTenantsMetricCard
            icon={FiBox}
            label="Com catalogo base"
            value={formatNumber(totals.withCatalog)}
            detail="Ja receberam o pacote padrao"
            tone="blue"
          />
          <OpsTenantsMetricCard
            icon={FiDatabase}
            label="Produtos somados"
            value={formatNumber(totals.products)}
            detail="Total visivel nesta lista"
            tone="amber"
          />
          <OpsTenantsMetricCard
            icon={FiCreditCard}
            label="Atencao cobranca"
            value={formatNumber(tabSummaries.billing.attention)}
            detail="Status pendente no filtro"
            tone={tabSummaries.billing.attention ? "amber" : "green"}
          />
        </div>

        <OpsTenantsTabs activeTab={activeTab} summaries={tabSummaries} onChange={setActiveTab} />

        <OpsTenantsFilters
          search={search}
          status={status}
          onSearchChange={setSearch}
          onStatusChange={setStatus}
        />

        {showTenantTable ? (
          <div className="grid gap-4 xl:grid-cols-[1fr_410px]">
            <OpsTenantsTable
              activeTab={activeTab}
              items={items}
              loading={loading}
              selectedTenant={selectedTenant}
              previewByTenant={previewByTenant}
              busyKey={busyKey}
              onSelectTenant={setSelectedTenantId}
              onPreview={handlePreview}
              onApply={handleApply}
            />

            <div className="space-y-4">
              <OpsTenantsImportPanel
                tenant={selectedTenant}
                preview={selectedTenant ? previewByTenant[selectedTenant.id] : null}
                applyResult={selectedTenant ? applyByTenant[selectedTenant.id] : null}
                actionError={actionError}
              />

              <OpsTenantsGuardrailsPanel />
            </div>
          </div>
        ) : null}

        {activeTab === "billing" ? (
          <OpsTenantsBillingTab
            items={items}
            loading={loading}
            selectedTenant={selectedTenant}
            editForm={commercialForm}
            editError={commercialError}
            editSuccess={commercialSuccess}
            saving={commercialSaving}
            onSelectTenant={setSelectedTenantId}
            onEditChange={handleCommercialChange}
            onEditSubmit={handleCommercialSubmit}
          />
        ) : null}

        {activeTab === "usage" ? (
          <OpsTenantsUsageTab items={items} summaries={tabSummaries} loading={loading} />
        ) : null}
      </div>
    </div>
  );
}
