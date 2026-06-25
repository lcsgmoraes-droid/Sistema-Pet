import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import { buscarClientes } from "../../api/clientes";
import { DEFAULT_ANONYMIZE_FORM, DEFAULT_NEW_REQUEST, DEFAULT_PROCESS_FORM } from "./lgpdConstants";
import {
  exportDossieJson,
  getDossieSummary,
  getPreferenceState,
  getRequests,
  mergeUpdatedRequest,
  onlyDefinedParams,
} from "./lgpdUtils";

export default function useLGPDOperacionalController() {
  const [status, setStatus] = useState(null);
  const [requests, setRequests] = useState([]);
  const [requestsFilter, setRequestsFilter] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [requestModalOpen, setRequestModalOpen] = useState(false);
  const [newRequestModalOpen, setNewRequestModalOpen] = useState(false);
  const [privacyModalOpen, setPrivacyModalOpen] = useState(false);
  const [processForm, setProcessForm] = useState(DEFAULT_PROCESS_FORM);
  const [anonymizeDialogOpen, setAnonymizeDialogOpen] = useState(false);
  const [anonymizeForm, setAnonymizeForm] = useState(DEFAULT_ANONYMIZE_FORM);
  const [clienteTermo, setClienteTermo] = useState("");
  const [clientesSugeridos, setClientesSugeridos] = useState([]);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  const [clienteRequests, setClienteRequests] = useState([]);
  const [dossie, setDossie] = useState(null);
  const [consentimentos, setConsentimentos] = useState(null);
  const [prefs, setPrefs] = useState(getPreferenceState());
  const [loadingCliente, setLoadingCliente] = useState(false);
  const [newRequest, setNewRequest] = useState(DEFAULT_NEW_REQUEST);

  const pendingCount = status?.pending ?? 0;
  const reviewCount = status?.in_review ?? 0;
  const completedCount = requests.filter((item) => item.status === "completed").length;
  const selectedClienteId = clienteSelecionado?.id || dossie?.cliente?.id || "";
  const selectedCustomer = dossie?.cliente || clienteSelecionado;
  const visibleRequests = selectedClienteId ? clienteRequests : requests;
  const selectedRequestBelongsToCustomer =
    selectedRequest?.subject_type === "customer" &&
    String(selectedRequest?.subject_id) === String(selectedClienteId);
  const requestToProcess =
    selectedClienteId && !selectedRequestBelongsToCustomer ? null : selectedRequest;
  const canAnonymizeSelected =
    requestToProcess?.request_type === "deletion" &&
    requestToProcess?.subject_type === "customer" &&
    !["completed", "cancelled", "rejected"].includes(requestToProcess?.status);

  const loadStatus = useCallback(async () => {
    const response = await api.get("/lgpd/status");
    setStatus(response.data || {});
  }, []);

  const loadRequests = useCallback(async () => {
    const response = await api.get("/lgpd/solicitacoes", {
      params: onlyDefinedParams({ status: requestsFilter, limit: 120 }),
    });
    const rows = getRequests(response.data);
    setRequests(rows);
    setSelectedRequest((current) => {
      if (current && rows.some((item) => item.id === current.id)) return current;
      return null;
    });
  }, [requestsFilter]);

  const loadClienteRequests = useCallback(async (clienteId) => {
    if (!clienteId) {
      setClienteRequests([]);
      return [];
    }
    const response = await api.get("/lgpd/solicitacoes", {
      params: {
        subject_type: "customer",
        subject_id: String(clienteId),
        limit: 100,
      },
    });
    const rows = getRequests(response.data);
    setClienteRequests(rows);
    setSelectedRequest((current) => {
      if (current && rows.some((item) => item.id === current.id)) return current;
      return null;
    });
    return rows;
  }, []);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([loadStatus(), loadRequests()]);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel carregar LGPD.");
    } finally {
      setLoading(false);
    }
  }, [loadRequests, loadStatus]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    if (!selectedRequest) return;
    setProcessForm({
      status: selectedRequest.status || "in_review",
      resolution_notes: selectedRequest.resolution_notes || "",
    });
  }, [selectedRequest]);

  useEffect(() => {
    const termo = clienteTermo.trim();
    if (termo.length < 2) {
      setClientesSugeridos([]);
      return undefined;
    }
    const timer = window.setTimeout(async () => {
      try {
        const rows = await buscarClientes({
          search: termo,
          incluir_inativos: true,
          limit: 10,
        });
        setClientesSugeridos(rows);
      } catch {
        setClientesSugeridos([]);
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [clienteTermo]);

  const clearClienteContext = () => {
    setClienteRequests([]);
    setSelectedRequest(null);
    setRequestModalOpen(false);
    setDossie(null);
    setConsentimentos(null);
    setPrefs(getPreferenceState());
  };

  const handleClienteTermoChange = (value) => {
    setClienteTermo(value);
    setClienteSelecionado(null);
    clearClienteContext();
  };

  const handleSelectCliente = (cliente) => {
    setClienteSelecionado(cliente);
    setClienteTermo(cliente?.nome || cliente?.razao_social || cliente?.codigo || "");
    setClientesSugeridos([]);
    clearClienteContext();
    if (cliente?.id) {
      loadClienteRequests(cliente.id).catch(() => setClienteRequests([]));
    }
  };

  const handleSelectRequest = (request) => {
    setSelectedRequest(request);
    setRequestModalOpen(true);
  };

  const carregarClientePrivacidade = async (clienteId = selectedClienteId) => {
    if (!clienteId) {
      toast.error("Selecione um titular primeiro.");
      return;
    }
    setLoadingCliente(true);
    try {
      const [dossieResponse, consentResponse, requestRows] = await Promise.all([
        api.get(`/lgpd/clientes/${clienteId}/dossie`),
        api.get(`/lgpd/clientes/${clienteId}/consentimentos`),
        loadClienteRequests(clienteId),
      ]);
      setDossie(dossieResponse.data);
      setConsentimentos(consentResponse.data);
      setPrefs(getPreferenceState(consentResponse.data?.preferencias));
      setClienteRequests(requestRows || []);
      toast.success("Dados de privacidade carregados.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel carregar o titular.");
    } finally {
      setLoadingCliente(false);
    }
  };

  const processarSolicitacao = async () => {
    if (!requestToProcess?.id) return;
    setSaving(true);
    try {
      const response = await api.patch(`/lgpd/solicitacoes/${requestToProcess.id}`, {
        status: processForm.status,
        resolution_notes: processForm.resolution_notes || null,
      });
      const updated = response.data?.request;
      setRequests((current) => mergeUpdatedRequest(current, updated));
      setClienteRequests((current) => mergeUpdatedRequest(current, updated));
      setSelectedRequest(updated);
      setRequestModalOpen(false);
      await loadStatus();
      toast.success("Solicitacao atualizada.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel atualizar.");
    } finally {
      setSaving(false);
    }
  };

  const abrirDialogAnonimizacao = () => {
    setAnonymizeForm({
      confirmacao: "",
      resolution_notes: processForm.resolution_notes || "",
    });
    setAnonymizeDialogOpen(true);
  };

  const confirmarAnonimizacao = async () => {
    if (!requestToProcess?.id || !canAnonymizeSelected) return;
    if (anonymizeForm.confirmacao.trim().toUpperCase() !== "ANONIMIZAR") {
      toast.error("Digite ANONIMIZAR para confirmar.");
      return;
    }
    setSaving(true);
    try {
      const response = await api.post(`/lgpd/solicitacoes/${requestToProcess.id}/anonimizar`, {
        confirmacao: anonymizeForm.confirmacao,
        resolution_notes: anonymizeForm.resolution_notes || null,
      });
      const updated = response.data?.request;
      setRequests((current) => mergeUpdatedRequest(current, updated));
      setClienteRequests((current) => mergeUpdatedRequest(current, updated));
      setSelectedRequest(updated);
      if (String(selectedClienteId) === String(updated?.subject_id)) {
        setDossie(null);
        setConsentimentos(null);
        setPrefs(getPreferenceState());
      }
      setAnonymizeDialogOpen(false);
      setRequestModalOpen(false);
      await Promise.all([loadStatus(), loadRequests(), loadClienteRequests(updated?.subject_id)]);
      toast.success("Titular anonimizado com trilha de auditoria.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel anonimizar o titular.");
    } finally {
      setSaving(false);
    }
  };

  const resetNewRequest = () => setNewRequest(DEFAULT_NEW_REQUEST);

  const criarSolicitacao = async () => {
    if (!selectedClienteId) {
      toast.error("Selecione o titular.");
      return;
    }
    setSaving(true);
    try {
      const response = await api.post("/lgpd/solicitacoes", {
        subject_type: "customer",
        subject_id: String(selectedClienteId),
        request_type: newRequest.request_type,
        details: newRequest.details || null,
        requester_name:
          newRequest.requester_name || dossie?.cliente?.nome || clienteSelecionado?.nome || null,
        requester_email:
          newRequest.requester_email || dossie?.cliente?.email || clienteSelecionado?.email || null,
        requester_phone:
          newRequest.requester_phone ||
          dossie?.cliente?.telefone ||
          clienteSelecionado?.telefone ||
          null,
        channel: "erp",
      });
      const created = response.data?.request;
      setRequests((current) => [created, ...current].filter(Boolean));
      setClienteRequests((current) => [created, ...current].filter(Boolean));
      setSelectedRequest(created);
      setNewRequestModalOpen(false);
      setRequestModalOpen(true);
      resetNewRequest();
      await loadStatus();
      toast.success("Solicitacao registrada.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel registrar.");
    } finally {
      setSaving(false);
    }
  };

  const criarSolicitacaoExclusao = async () => {
    if (!selectedClienteId) {
      toast.error("Selecione o titular antes de abrir a exclusao.");
      return;
    }
    setSaving(true);
    try {
      const response = await api.post("/lgpd/solicitacoes", {
        subject_type: "customer",
        subject_id: String(selectedClienteId),
        request_type: "deletion",
        details: "Pedido de exclusao/anonimizacao aberto pelo operador no painel LGPD.",
        requester_name: selectedCustomer?.nome || selectedCustomer?.razao_social || null,
        requester_email: selectedCustomer?.email || null,
        requester_phone: selectedCustomer?.telefone || selectedCustomer?.celular || null,
        channel: "erp",
      });
      const created = response.data?.request;
      setRequests((current) => [created, ...current].filter(Boolean));
      setClienteRequests((current) => [created, ...current].filter(Boolean));
      setSelectedRequest(created);
      setRequestModalOpen(true);
      await loadStatus();
      toast.success("Solicitacao de exclusao aberta. Revise e confirme a anonimizacao.");
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Nao foi possivel abrir a solicitacao de exclusao.",
      );
    } finally {
      setSaving(false);
    }
  };

  const abrirNovoPedidoAcesso = () => {
    setNewRequest((current) => ({ ...current, request_type: "access" }));
    setNewRequestModalOpen(true);
  };

  const salvarPreferencias = async () => {
    if (!selectedClienteId) {
      toast.error("Selecione um titular primeiro.");
      return;
    }
    setSaving(true);
    try {
      const response = await api.put(`/lgpd/clientes/${selectedClienteId}/preferencias`, prefs);
      setConsentimentos((current) => ({
        ...(current || {}),
        preferencias: response.data?.preferencias,
      }));
      toast.success("Preferencias salvas.");
      await carregarClientePrivacidade(selectedClienteId);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel salvar preferencias.");
    } finally {
      setSaving(false);
    }
  };

  const exportarJson = () => {
    if (!dossie) {
      toast.error("Carregue o dossie antes de exportar.");
      return;
    }
    exportDossieJson(dossie);
  };

  const resumoDossie = useMemo(() => getDossieSummary(dossie), [dossie]);

  return {
    anonymizeDialogOpen,
    anonymizeForm,
    abrirDialogAnonimizacao,
    abrirNovoPedidoAcesso,
    canAnonymizeSelected,
    carregarClientePrivacidade,
    clienteTermo,
    clientesSugeridos,
    completedCount,
    confirmarAnonimizacao,
    consentimentos,
    criarSolicitacao,
    criarSolicitacaoExclusao,
    dossie,
    exportarJson,
    handleClienteTermoChange,
    handleSelectCliente,
    handleSelectRequest,
    loading,
    loadingCliente,
    newRequest,
    newRequestModalOpen,
    pendingCount,
    prefs,
    privacyModalOpen,
    processForm,
    processarSolicitacao,
    refreshAll,
    requestModalOpen,
    requestToProcess,
    requestsFilter,
    reviewCount,
    resumoDossie,
    salvarPreferencias,
    saving,
    selectedClienteId,
    selectedCustomer,
    setAnonymizeDialogOpen,
    setAnonymizeForm,
    setNewRequest,
    setNewRequestModalOpen,
    setPrefs,
    setPrivacyModalOpen,
    setProcessForm,
    setRequestModalOpen,
    setRequestsFilter,
    visibleRequests,
  };
}
