import { useCallback, useEffect, useMemo, useState } from "react";

import api from "../../platformApi";
import {
  buildOpsTenantCommercialForm,
  buildOpsTenantCommercialPayload,
  buildOpsTenantOnboardingForm,
  buildOpsTenantOnboardingPayload,
  buildOpsTenantTabSummaries,
  groupOpsTenantsByClient,
} from "../opsTenantsUtils";

import { extractError } from "./opsTenantsFormatters";
import { BILLING_OFFER_PLAN_OPTIONS } from "./opsTenantsConstants";
import useOpsTenantOnboardingNotes from "./useOpsTenantOnboardingNotes";

function tomorrowIsoDate() {
  const value = new Date();
  value.setDate(value.getDate() + 1);
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function initialBillingOfferForm() {
  return {
    title: "CorePet - Pet Venda Ativa",
    plan_code: "pet-venda-ativa",
    price: 0,
    first_due_date: tomorrowIsoDate(),
    billing_type: "UNDEFINED",
    extra_modules: [],
    scope_summary: "Uso do CorePet com o plano e os módulos indicados nesta proposta.",
    implementation_summary: "Implantação acompanhada. Migração ampla exige proposta separada.",
    exclusions_summary: "Não inclui equipamentos, internet ou desenvolvimento não descrito.",
    support_channel: "E-mail e WhatsApp informados no contrato",
    custom_work_summary: "Nenhum desenvolvimento sob medida integra esta proposta.",
  };
}

export default function useOpsTenantsController() {
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [activeTab, setActiveTab] = useState("tenants");
  const [commercialForm, setCommercialForm] = useState(buildOpsTenantCommercialForm());
  const [commercialError, setCommercialError] = useState("");
  const [commercialSuccess, setCommercialSuccess] = useState("");
  const [commercialSaving, setCommercialSaving] = useState(false);
  const [onboardingForm, setOnboardingForm] = useState(buildOpsTenantOnboardingForm());
  const [onboardingError, setOnboardingError] = useState("");
  const [onboardingSuccess, setOnboardingSuccess] = useState("");
  const [onboardingSaving, setOnboardingSaving] = useState(false);
  const [billingOfferForm, setBillingOfferForm] = useState(initialBillingOfferForm);
  const [billingOffers, setBillingOffers] = useState([]);
  const [billingOffersLoading, setBillingOffersLoading] = useState(false);
  const [billingOfferCreating, setBillingOfferCreating] = useState(false);
  const [billingOfferError, setBillingOfferError] = useState("");
  const [billingOfferSuccess, setBillingOfferSuccess] = useState("");
  const [billingOfferPublicUrl, setBillingOfferPublicUrl] = useState("");
  const [selectedTenantId, setSelectedTenantId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tenantsPage, setTenantsPage] = useState(1);
  const [tenantsItems, setTenantsItems] = useState([]);
  const [tenantsLoading, setTenantsLoading] = useState(true);
  const [tenantsPagination, setTenantsPagination] = useState({
    page: 1,
    pageSize: 10,
    totalGroups: 0,
    totalPages: 0,
  });

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

  const loadTenantsGrouped = useCallback(async () => {
    setTenantsLoading(true);
    try {
      const response = await api.get("/admin/tenants/grouped", {
        params: {
          search: search.trim() || undefined,
          status: status || undefined,
          page: tenantsPage,
          page_size: 10,
        },
      });
      setTenantsItems(response.data?.items || []);
      setTenantsPagination({
        page: response.data?.page || 1,
        pageSize: response.data?.page_size || 10,
        totalGroups: response.data?.total_groups || 0,
        totalPages: response.data?.total_pages || 0,
      });
    } catch (err) {
      console.error("Erro ao carregar tenants agrupados:", err);
      setError(extractError(err, "Nao foi possivel carregar os tenants agora."));
    } finally {
      setTenantsLoading(false);
    }
  }, [search, status, tenantsPage]);

  useEffect(() => {
    loadTenantsGrouped();
  }, [loadTenantsGrouped]);

  useEffect(() => {
    setTenantsPage(1);
  }, [search, status]);

  const selectedTenant = useMemo(
    () => items.find((item) => item.id === selectedTenantId) || items[0] || null,
    [items, selectedTenantId],
  );

  const loadBillingOffers = useCallback(async (tenantId) => {
    if (!tenantId) {
      setBillingOffers([]);
      return;
    }
    setBillingOffersLoading(true);
    try {
      const response = await api.get(`/admin/tenants/${tenantId}/billing-offers`);
      setBillingOffers(response.data?.items || []);
    } catch (err) {
      setBillingOfferError(extractError(err, "Nao foi possivel carregar as propostas."));
    } finally {
      setBillingOffersLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedTenant) {
      setCommercialForm(buildOpsTenantCommercialForm(selectedTenant));
      setOnboardingForm(buildOpsTenantOnboardingForm(selectedTenant));
      setBillingOfferForm(initialBillingOfferForm());
      loadBillingOffers(selectedTenant.id);
    }
  }, [loadBillingOffers, selectedTenant]);

  const {
    handleNoteChange: handleOnboardingNoteChange,
    handleNoteSubmit: handleOnboardingNoteSubmit,
    noteError: onboardingNoteError,
    noteSaving: onboardingNoteSaving,
    noteSuccess: onboardingNoteSuccess,
    noteText: onboardingNoteText,
    notes: onboardingNotes,
    notesLoading: onboardingNotesLoading,
  } = useOpsTenantOnboardingNotes(selectedTenant?.id || "");

  useEffect(() => {
    setCommercialError("");
    setCommercialSuccess("");
    setOnboardingError("");
    setOnboardingSuccess("");
    setBillingOfferError("");
    setBillingOfferSuccess("");
    setBillingOfferPublicUrl("");
  }, [selectedTenantId]);

  const totals = useMemo(
    () => ({
      tenants: summary?.total ?? items.length,
      active:
        summary?.active ??
        items.filter((item) =>
          ["active", "ativo"].includes(String(item.status || "").toLowerCase()),
        ).length,
    }),
    [items, summary],
  );

  const tabSummaries = useMemo(() => buildOpsTenantTabSummaries(items, summary), [items, summary]);
  const groupedItems = useMemo(() => groupOpsTenantsByClient(tenantsItems), [tenantsItems]);
  const showTenantTable = activeTab === "tenants";

  const refreshAfterLojaAdded = useCallback(async () => {
    setTenantsPage(1);
    await Promise.all([loadTenants(), loadTenantsGrouped()]);
  }, [loadTenants, loadTenantsGrouped]);

  function handleCommercialChange(field, value) {
    setCommercialForm((current) => ({ ...current, [field]: value }));
    setCommercialError("");
    setCommercialSuccess("");
  }

  async function handleCommercialSubmit(event) {
    event.preventDefault();
    if (!selectedTenant) {
      setCommercialError("Selecione um tenant antes de salvar.");
      return;
    }

    const original = buildOpsTenantCommercialForm(selectedTenant);
    const payload = buildOpsTenantCommercialPayload(original, commercialForm);
    if (Object.keys(payload).length === 0) {
      setCommercialSuccess("Nenhuma alteracao para salvar.");
      return;
    }

    setCommercialSaving(true);
    setCommercialError("");
    setCommercialSuccess("");
    try {
      const response = await api.patch(`/admin/tenants/${selectedTenant.id}/commercial`, payload);
      setItems((current) =>
        current.map((item) => (item.id === selectedTenant.id ? response.data : item)),
      );
      setCommercialSuccess("Manutencao salva.");
      await loadTenants();
      setSelectedTenantId(response.data.id);
    } catch (err) {
      setCommercialError(extractError(err, "Nao foi possivel salvar a manutencao comercial."));
    } finally {
      setCommercialSaving(false);
    }
  }

  function handleOnboardingChange(field, value) {
    setOnboardingForm((current) => ({ ...current, [field]: value }));
    setOnboardingError("");
    setOnboardingSuccess("");
  }

  async function handleOnboardingSubmit(event) {
    event.preventDefault();
    if (!selectedTenant) {
      setOnboardingError("Selecione uma empresa antes de salvar.");
      return;
    }

    const original = buildOpsTenantOnboardingForm(selectedTenant);
    const payload = buildOpsTenantOnboardingPayload(original, onboardingForm);
    if (Object.keys(payload).length === 0) {
      setOnboardingSuccess("Nenhuma alteracao para salvar.");
      return;
    }

    setOnboardingSaving(true);
    setOnboardingError("");
    setOnboardingSuccess("");
    try {
      const response = await api.patch(
        `/admin/tenants/${selectedTenant.id}/onboarding-follow-up`,
        payload,
      );
      setItems((current) =>
        current.map((item) => (item.id === selectedTenant.id ? response.data : item)),
      );
      setOnboardingSuccess("Acompanhamento salvo.");
      await loadTenants();
      setSelectedTenantId(response.data.id);
    } catch (err) {
      setOnboardingError(extractError(err, "Nao foi possivel salvar o acompanhamento."));
    } finally {
      setOnboardingSaving(false);
    }
  }

  function handleBillingOfferChange(field, value) {
    setBillingOfferForm((current) => {
      const next = { ...current, [field]: value };
      if (field === "plan_code") {
        const plan = BILLING_OFFER_PLAN_OPTIONS.find((item) => item.value === value);
        next.title = plan ? `CorePet - ${plan.label}` : current.title;
      }
      return next;
    });
    setBillingOfferError("");
    setBillingOfferSuccess("");
    setBillingOfferPublicUrl("");
  }

  function handleBillingOfferToggleModule(module) {
    setBillingOfferForm((current) => ({
      ...current,
      extra_modules: current.extra_modules.includes(module)
        ? current.extra_modules.filter((item) => item !== module)
        : [...current.extra_modules, module],
    }));
    setBillingOfferError("");
    setBillingOfferSuccess("");
    setBillingOfferPublicUrl("");
  }

  async function handleBillingOfferSubmit(event) {
    event.preventDefault();
    if (!selectedTenant) {
      setBillingOfferError("Selecione uma empresa antes de gerar a proposta.");
      return;
    }
    const priceCents = Math.round(Number(billingOfferForm.price || 0) * 100);
    if (priceCents < 100) {
      setBillingOfferError("Informe o valor mensal combinado com o cliente.");
      return;
    }
    const invalidCommercialTerms = [
      ["scope_summary", 10],
      ["implementation_summary", 10],
      ["exclusions_summary", 10],
      ["support_channel", 3],
    ].some(([key, min]) => billingOfferForm[key].trim().length < min);
    if (invalidCommercialTerms) {
      setBillingOfferError("Revise as condições específicas antes de continuar.");
      return;
    }
    setBillingOfferCreating(true);
    setBillingOfferError("");
    setBillingOfferSuccess("");
    setBillingOfferPublicUrl("");
    try {
      const response = await api.post(`/admin/tenants/${selectedTenant.id}/billing-offers`, {
        title: billingOfferForm.title.trim(),
        plan_code: billingOfferForm.plan_code,
        price_cents: priceCents,
        first_due_date: billingOfferForm.first_due_date,
        billing_type: billingOfferForm.billing_type,
        extra_modules: billingOfferForm.extra_modules,
        scope_summary: billingOfferForm.scope_summary.trim(),
        implementation_summary: billingOfferForm.implementation_summary.trim(),
        exclusions_summary: billingOfferForm.exclusions_summary.trim(),
        support_channel: billingOfferForm.support_channel.trim(),
        custom_work_summary: billingOfferForm.custom_work_summary.trim() || null,
      });
      const publicUrl = new URL(response.data.public_path, globalThis.location.origin).toString();
      setBillingOfferPublicUrl(publicUrl);
      setBillingOfferSuccess("Proposta criada. Confira e envie o link ao cliente.");
      await loadBillingOffers(selectedTenant.id);
    } catch (err) {
      setBillingOfferError(extractError(err, "Nao foi possivel gerar o link de contratacao."));
    } finally {
      setBillingOfferCreating(false);
    }
  }

  return {
    activeTab,
    commercialError,
    commercialForm,
    commercialSaving,
    commercialSuccess,
    billingOfferCreating,
    billingOfferError,
    billingOfferForm,
    billingOfferPublicUrl,
    billingOffers,
    billingOffersLoading,
    billingOfferSuccess,
    error,
    handleCommercialChange,
    handleCommercialSubmit,
    handleOnboardingChange,
    handleOnboardingNoteChange,
    handleOnboardingNoteSubmit,
    handleOnboardingSubmit,
    handleBillingOfferChange,
    handleBillingOfferSubmit,
    handleBillingOfferToggleModule,
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
  };
}
