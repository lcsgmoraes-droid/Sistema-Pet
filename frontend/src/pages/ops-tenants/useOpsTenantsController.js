import { useCallback, useEffect, useMemo, useState } from "react";

import api from "../../api";
import {
  buildOpsTenantCommercialForm,
  buildOpsTenantCommercialPayload,
  buildOpsTenantTabSummaries,
} from "../opsTenantsUtils";

import { extractError, sumCounts } from "./opsTenantsFormatters";
import { BILLING_OFFER_PLAN_OPTIONS } from "./opsTenantsConstants";

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
      setCommercialError("");
      setCommercialSuccess("");
      setBillingOfferForm(initialBillingOfferForm());
      setBillingOfferError("");
      setBillingOfferSuccess("");
      setBillingOfferPublicUrl("");
      loadBillingOffers(selectedTenant.id);
    }
  }, [loadBillingOffers, selectedTenant]);

  const totals = useMemo(
    () => ({
      tenants: summary?.total ?? items.length,
      active:
        summary?.active ??
        items.filter((item) =>
          ["active", "ativo"].includes(String(item.status || "").toLowerCase()),
        ).length,
      withCatalog:
        summary?.with_base_catalog ?? items.filter((item) => item.base_catalog?.installed).length,
      products: sumCounts(items, "produtos"),
    }),
    [items, summary],
  );

  const tabSummaries = useMemo(() => buildOpsTenantTabSummaries(items, summary), [items, summary]);
  const showTenantTable = activeTab === "tenants" || activeTab === "catalog";

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
      const response = await api.post(`/admin/tenants/${tenant.id}/catalog-import/apply`, {
        confirm: true,
      });
      setApplyByTenant((current) => ({ ...current, [tenant.id]: response.data }));
      await loadTenants();
    } catch (err) {
      setActionError(extractError(err, "Nao foi possivel aplicar a importacao."));
    } finally {
      setBusyKey("");
    }
  }

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
    actionError,
    activeTab,
    applyByTenant,
    busyKey,
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
    handleApply,
    handleCommercialChange,
    handleCommercialSubmit,
    handleBillingOfferChange,
    handleBillingOfferSubmit,
    handleBillingOfferToggleModule,
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
  };
}
