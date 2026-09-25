import { FiAlertTriangle, FiCheckCircle, FiCreditCard, FiUsers } from "react-icons/fi";

import OpsTenantsBillingTab from "./OpsTenantsBillingTab";
import OpsTenantsFilters from "./OpsTenantsFilters";
import OpsTenantsHeader from "./OpsTenantsHeader";
import OpsTenantsMetricCard from "./OpsTenantsMetricCard";
import OpsTenantsPilotTab from "./OpsTenantsPilotTab";
import OpsTenantsTable from "./OpsTenantsTable";
import OpsTenantsTabs from "./OpsTenantsTabs";
import OpsTenantsUsageTab from "./OpsTenantsUsageTab";
import { formatNumber } from "./opsTenantsFormatters";
import useOpsTenantsController from "./useOpsTenantsController";

export default function OpsTenantsPage() {
  const {
    activeTab,
    billingOfferCreating,
    billingOfferError,
    billingOfferForm,
    billingOfferPublicUrl,
    billingOffers,
    billingOffersLoading,
    billingOfferSuccess,
    commercialError,
    commercialForm,
    commercialSaving,
    commercialSuccess,
    error,
    handleBillingOfferChange,
    handleBillingOfferSubmit,
    handleBillingOfferToggleModule,
    handleCommercialChange,
    handleCommercialSubmit,
    handleOnboardingChange,
    handleOnboardingNoteChange,
    handleOnboardingNoteSubmit,
    handleOnboardingSubmit,
    groupedItems,
    items,
    loadTenants,
    loading,
    onboardingError,
    onboardingForm,
    onboardingNoteError,
    onboardingNoteSaving,
    onboardingNoteSuccess,
    onboardingNoteText,
    onboardingNotes,
    onboardingNotesLoading,
    onboardingSaving,
    onboardingSuccess,
    refreshAfterLojaAdded,
    search,
    selectedTenant,
    setActiveTab,
    setSearch,
    setSelectedTenantId,
    setStatus,
    setTenantsPage,
    showTenantTable,
    status,
    tabSummaries,
    tenantsLoading,
    tenantsPagination,
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

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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
            icon={FiAlertTriangle}
            label="Precisam de atencao"
            value={formatNumber(tabSummaries.pilot.needFollowUp)}
            detail="Erros, alertas ou acompanhamento pendente"
            tone={tabSummaries.pilot.needFollowUp ? "amber" : "green"}
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
          <OpsTenantsTable
            groupedItems={groupedItems}
            pagination={tenantsPagination}
            onPageChange={setTenantsPage}
            loading={tenantsLoading}
            selectedTenant={selectedTenant}
            onSelectTenant={setSelectedTenantId}
            onLojaAdded={refreshAfterLojaAdded}
          />
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
            offerForm={billingOfferForm}
            offers={billingOffers}
            offersLoading={billingOffersLoading}
            offerCreating={billingOfferCreating}
            offerError={billingOfferError}
            offerSuccess={billingOfferSuccess}
            offerPublicUrl={billingOfferPublicUrl}
            onOfferChange={handleBillingOfferChange}
            onOfferToggleModule={handleBillingOfferToggleModule}
            onOfferSubmit={handleBillingOfferSubmit}
          />
        ) : null}

        {activeTab === "usage" ? (
          <OpsTenantsUsageTab items={items} summaries={tabSummaries} loading={loading} />
        ) : null}

        {activeTab === "pilot" ? (
          <OpsTenantsPilotTab
            items={items}
            summaries={tabSummaries}
            loading={loading}
            selectedTenant={selectedTenant}
            form={onboardingForm}
            error={onboardingError}
            success={onboardingSuccess}
            saving={onboardingSaving}
            onSelectTenant={setSelectedTenantId}
            onChange={handleOnboardingChange}
            onSubmit={handleOnboardingSubmit}
            notes={onboardingNotes}
            notesLoading={onboardingNotesLoading}
            noteText={onboardingNoteText}
            noteError={onboardingNoteError}
            noteSuccess={onboardingNoteSuccess}
            noteSaving={onboardingNoteSaving}
            onNoteChange={handleOnboardingNoteChange}
            onNoteSubmit={handleOnboardingNoteSubmit}
          />
        ) : null}
      </div>
    </div>
  );
}
