import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Download,
  FileText,
  History,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Trash2,
  UserSearch,
  X,
} from "lucide-react";
import api from "../api";
import { buscarClientes } from "../api/clientes";
import PessoaSelector from "../components/clientes/PessoaSelector";
import ActionButton from "../components/ui/ActionButton";
import CopyableCode from "../components/ui/CopyableCode";
import CustomerIdentity from "../components/ui/CustomerIdentity";
import EmptyState from "../components/ui/EmptyState";
import LoadingState from "../components/ui/LoadingState";
import MetricCard from "../components/ui/MetricCard";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import StatusBadge from "../components/ui/StatusBadge";

const REQUEST_TYPES = [
  ["access", "Acesso aos dados"],
  ["export", "Exportacao"],
  ["correction", "Correcao"],
  ["deletion", "Exclusao"],
  ["revocation", "Revogacao"],
  ["information", "Informacao"],
];

const REQUEST_STATUS = [
  ["pending", "Pendente"],
  ["in_review", "Em analise"],
  ["waiting_customer", "Aguardando cliente"],
  ["completed", "Concluida"],
  ["rejected", "Rejeitada"],
  ["cancelled", "Cancelada"],
];

const STATUS_INTENT = {
  pending: "warning",
  in_review: "info",
  waiting_customer: "purple",
  completed: "success",
  rejected: "danger",
  cancelled: "neutral",
};

const PREFERENCES = [
  ["marketing_email", "Email marketing", "Ofertas, cupons e campanhas por email."],
  ["marketing_whatsapp", "WhatsApp marketing", "Mensagens promocionais e lembretes comerciais."],
  ["marketing_sms", "SMS marketing", "Comunicacoes curtas por SMS."],
  ["marketing_push", "Push no app", "Avisos e campanhas no aplicativo."],
  ["analytics", "Analise e personalizacao", "Uso de dados para segmentacao e melhoria da experiencia."],
];

const REQUEST_TYPE_LABEL = Object.fromEntries(REQUEST_TYPES);
const REQUEST_STATUS_LABEL = Object.fromEntries(REQUEST_STATUS);

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function onlyDefinedParams(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value != null),
  );
}

function getRequests(payload) {
  if (Array.isArray(payload?.requests)) return payload.requests;
  if (Array.isArray(payload?.next_items)) return payload.next_items;
  return [];
}

function getPreferenceState(preferencias) {
  return Object.fromEntries(
    PREFERENCES.map(([key]) => [key, Boolean(preferencias?.[key]?.enabled)]),
  );
}

function PreferenceToggle({ description, label, name, onChange, value }) {
  return (
    <label className="flex min-h-[70px] cursor-pointer items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 transition-colors hover:border-blue-200 hover:bg-blue-50/40">
      <input
        type="checkbox"
        checked={Boolean(value)}
        onChange={(event) => onChange(name, event.target.checked)}
        className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
      />
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-slate-900">{label}</span>
        <span className="mt-1 block text-xs leading-snug text-slate-500">
          {description}
        </span>
      </span>
    </label>
  );
}

function RequestCard({ request, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(request)}
      className={[
        "w-full rounded-lg border p-3 text-left transition-colors",
        selected ? "border-blue-400 bg-blue-50" : "border-slate-200 bg-white hover:bg-slate-50",
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-950">
              {REQUEST_TYPE_LABEL[request.request_type] || request.request_type}
            </span>
            <CopyableCode label="ID" value={request.id} />
          </div>
          <div className="mt-1 flex min-w-0 flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>{request.subject_type || "customer"}</span>
            <CopyableCode label="Titular" value={request.subject_id} />
            <span>Canal: {request.channel || "-"}</span>
          </div>
        </div>
        <StatusBadge
          status={request.status}
          intent={STATUS_INTENT[request.status]}
        >
          {REQUEST_STATUS_LABEL[request.status] || request.status}
        </StatusBadge>
      </div>
      {request.requester_name || request.requester_email ? (
        <p className="mt-2 truncate text-xs text-slate-600">
          Solicitante: {request.requester_name || "-"} {request.requester_email ? `- ${request.requester_email}` : ""}
        </p>
      ) : null}
      {request.details ? (
        <p className="mt-2 line-clamp-2 text-xs text-slate-500">{request.details}</p>
      ) : null}
      <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-500 sm:grid-cols-2">
        <span>Criada: {formatDate(request.created_at)}</span>
        <span>Prazo: {formatDate(request.due_at)}</span>
      </div>
    </button>
  );
}

export default function LGPDOperacional() {
  const [status, setStatus] = useState(null);
  const [requests, setRequests] = useState([]);
  const [requestsFilter, setRequestsFilter] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [processForm, setProcessForm] = useState({
    status: "in_review",
    resolution_notes: "",
  });
  const [anonymizeDialogOpen, setAnonymizeDialogOpen] = useState(false);
  const [anonymizeForm, setAnonymizeForm] = useState({
    confirmacao: "",
    resolution_notes: "",
  });

  const [clienteTermo, setClienteTermo] = useState("");
  const [clientesSugeridos, setClientesSugeridos] = useState([]);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  const [clienteRequests, setClienteRequests] = useState([]);
  const [dossie, setDossie] = useState(null);
  const [consentimentos, setConsentimentos] = useState(null);
  const [prefs, setPrefs] = useState(getPreferenceState());
  const [loadingCliente, setLoadingCliente] = useState(false);

  const [newRequest, setNewRequest] = useState({
    request_type: "access",
    details: "",
    requester_name: "",
    requester_email: "",
    requester_phone: "",
  });

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
      if (!current) return rows[0] || null;
      return rows.find((item) => item.id === current.id) || rows[0] || null;
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
      return rows[0] || null;
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
          tipo_cadastro: "cliente",
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

  const handleSelectCliente = (cliente) => {
    setClienteSelecionado(cliente);
    setClienteTermo(cliente?.nome || cliente?.razao_social || cliente?.codigo || "");
    setClientesSugeridos([]);
    setClienteRequests([]);
    setSelectedRequest(null);
    setDossie(null);
    setConsentimentos(null);
    setPrefs(getPreferenceState());
    if (cliente?.id) {
      loadClienteRequests(cliente.id).catch(() => setClienteRequests([]));
    }
  };

  const carregarClientePrivacidade = async (clienteId = selectedClienteId) => {
    if (!clienteId) {
      toast.error("Selecione um cliente primeiro.");
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
      toast.error(error.response?.data?.detail || "Nao foi possivel carregar o cliente.");
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
      setRequests((current) =>
        current.map((item) => (item.id === updated?.id ? updated : item)),
      );
      setClienteRequests((current) =>
        current.map((item) => (item.id === updated?.id ? updated : item)),
      );
      setSelectedRequest(updated);
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
      setRequests((current) =>
        current.map((item) => (item.id === updated?.id ? updated : item)),
      );
      setClienteRequests((current) =>
        current.map((item) => (item.id === updated?.id ? updated : item)),
      );
      setSelectedRequest(updated);
      if (String(selectedClienteId) === String(updated?.subject_id)) {
        setDossie(null);
        setConsentimentos(null);
        setPrefs(getPreferenceState());
      }
      setAnonymizeDialogOpen(false);
      await Promise.all([loadStatus(), loadRequests(), loadClienteRequests(updated?.subject_id)]);
      toast.success("Cliente anonimizado com trilha de auditoria.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel anonimizar o cliente.");
    } finally {
      setSaving(false);
    }
  };

  const criarSolicitacao = async () => {
    if (!selectedClienteId) {
      toast.error("Selecione o cliente titular.");
      return;
    }

    setSaving(true);
    try {
      const response = await api.post("/lgpd/solicitacoes", {
        subject_type: "customer",
        subject_id: String(selectedClienteId),
        request_type: newRequest.request_type,
        details: newRequest.details || null,
        requester_name: newRequest.requester_name || dossie?.cliente?.nome || clienteSelecionado?.nome || null,
        requester_email: newRequest.requester_email || dossie?.cliente?.email || clienteSelecionado?.email || null,
        requester_phone: newRequest.requester_phone || dossie?.cliente?.telefone || clienteSelecionado?.telefone || null,
        channel: "erp",
      });
      const created = response.data?.request;
      setRequests((current) => [created, ...current].filter(Boolean));
      setClienteRequests((current) => [created, ...current].filter(Boolean));
      setSelectedRequest(created);
      setNewRequest({
        request_type: "access",
        details: "",
        requester_name: "",
        requester_email: "",
        requester_phone: "",
      });
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
      await loadStatus();
      toast.success("Solicitacao de exclusao aberta. Revise e confirme a anonimizacao.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel abrir a solicitacao de exclusao.");
    } finally {
      setSaving(false);
    }
  };

  const salvarPreferencias = async () => {
    if (!selectedClienteId) {
      toast.error("Selecione um cliente primeiro.");
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
    const clienteId = dossie?.cliente?.codigo || dossie?.cliente?.id || "cliente";
    const blob = new Blob([JSON.stringify(dossie, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `dossie-lgpd-${clienteId}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const resumoDossie = useMemo(() => {
    if (!dossie) return [];
    return [
      ["Pets", dossie.pets?.length || 0],
      ["Vendas", dossie.vendas?.length || 0],
      ["Pedidos app/e-commerce", dossie.ecommerce_pedidos?.length || 0],
      ["Consentimentos", dossie.consentimentos?.length || 0],
      ["Solicitacoes", dossie.solicitacoes?.length || 0],
      ["Logs de acesso", dossie.logs_acesso?.length || 0],
    ];
  }, [dossie]);

  return (
    <div className="space-y-5 p-4 md:p-6">
      <PageHeader
        icon={ShieldCheck}
        title="LGPD e Privacidade"
        subtitle="Solicitacoes, preferencias, dossie e trilha de acesso dos titulares."
        actions={
          <ActionButton
            icon={RefreshCw}
            intent="neutral"
            tone="soft"
            onClick={refreshAll}
            loading={loading}
          >
            Atualizar
          </ActionButton>
        }
      />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <MetricCard
          intent={pendingCount ? "amber" : "emerald"}
          icon={<Clock3 className="h-5 w-5" />}
          label="Pendentes"
          value={pendingCount}
          subtitle="Solicitacoes ainda sem tratamento."
        />
        <MetricCard
          intent={reviewCount ? "blue" : "slate"}
          icon={<FileText className="h-5 w-5" />}
          label="Em analise"
          value={reviewCount}
          subtitle="Demandas em acompanhamento operacional."
        />
        <MetricCard
          intent="emerald"
          icon={<CheckCircle2 className="h-5 w-5" />}
          label="Concluidas no filtro"
          value={completedCount}
          subtitle="Itens retornados pelo filtro atual."
        />
      </div>

      <Panel
        title="1. Buscar titular"
        subtitle="Comece pelo cliente. A busca inclui ativos e inativos para permitir atendimento LGPD completo."
      >
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(380px,0.8fr)]">
          <div className="space-y-3">
            <PessoaSelector
              minChars={2}
              onChange={(value) => {
                setClienteTermo(value);
                setClienteSelecionado(null);
                setClienteRequests([]);
                setDossie(null);
                setConsentimentos(null);
              }}
              onSelect={handleSelectCliente}
              placeholder="Digite nome, codigo, CPF, email ou telefone do cliente..."
              showSuggestions={clientesSugeridos.length > 0}
              suggestions={clientesSugeridos}
              value={clienteTermo}
              renderSuggestion={(cliente, index) => (
                <button
                  key={cliente?.id || index}
                  type="button"
                  onClick={() => handleSelectCliente(cliente)}
                  className="w-full border-b px-4 py-3 text-left last:border-b-0 hover:bg-slate-50"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CustomerIdentity customer={cliente} />
                    <StatusBadge intent={cliente?.ativo === false ? "neutral" : "success"} size="xs">
                      {cliente?.ativo === false ? "Inativo" : "Ativo"}
                    </StatusBadge>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    {cliente?.email || cliente?.telefone || cliente?.celular || "-"}
                  </div>
                </button>
              )}
            />
            <div className="flex flex-wrap items-center gap-2">
              <ActionButton
                icon={Search}
                intent="edit"
                onClick={() => carregarClientePrivacidade()}
                loading={loadingCliente}
                disabled={!selectedClienteId}
              >
                Carregar dados LGPD
              </ActionButton>
              {selectedClienteId ? <CopyableCode label="Cliente" value={selectedClienteId} /> : null}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            {selectedCustomer ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <CustomerIdentity customer={selectedCustomer} />
                  <StatusBadge intent={selectedCustomer?.ativo === false ? "neutral" : "success"}>
                    {selectedCustomer?.ativo === false ? "Inativo" : "Ativo"}
                  </StatusBadge>
                </div>
                <div className="grid grid-cols-1 gap-2 text-xs text-slate-600 sm:grid-cols-2">
                  <span>Email: {selectedCustomer.email || "-"}</span>
                  <span>Telefone: {selectedCustomer.telefone || selectedCustomer.celular || "-"}</span>
                  <span>Codigo: {selectedCustomer.codigo || "-"}</span>
                  <span>ID: {selectedCustomer.id || "-"}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <ActionButton
                    icon={Trash2}
                    intent="delete"
                    tone="soft"
                    onClick={criarSolicitacaoExclusao}
                    loading={saving}
                  >
                    Abrir exclusao LGPD
                  </ActionButton>
                  <ActionButton
                    icon={FileText}
                    intent="neutral"
                    tone="soft"
                    onClick={() =>
                      setNewRequest((current) => ({
                        ...current,
                        request_type: "access",
                      }))
                    }
                  >
                    Registrar outro pedido
                  </ActionButton>
                </div>
              </div>
            ) : (
              <EmptyState
                compact
                icon={UserSearch}
                title="Nenhum titular selecionado"
                description="Pesquise o cliente primeiro; depois aparecem dossie, solicitacoes e exclusao."
              />
            )}
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.9fr)]">
        <Panel
          title={selectedClienteId ? "2. Solicitacoes deste titular" : "2. Fila de solicitacoes"}
          subtitle={selectedClienteId ? "Pedidos LGPD vinculados ao cliente selecionado." : "Fila operacional geral enquanto nenhum titular esta selecionado."}
          actions={
            selectedClienteId ? null : (
              <select
                value={requestsFilter}
                onChange={(event) => setRequestsFilter(event.target.value)}
                className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
              >
                <option value="">Todos os status</option>
                {REQUEST_STATUS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            )
          }
        >
          {loading ? (
            <LoadingState compact label="Carregando solicitacoes..." />
          ) : visibleRequests.length === 0 ? (
            <EmptyState
              compact
              title={selectedClienteId ? "Nenhuma solicitacao para este titular" : "Nenhuma solicitacao neste filtro"}
              description={selectedClienteId ? "Use Abrir exclusao LGPD ou registre outro pedido para iniciar o atendimento." : "Quando um titular pedir acesso, exportacao, correcao ou exclusao, o acompanhamento aparece aqui."}
            />
          ) : (
            <div className="max-h-[540px] space-y-2 overflow-y-auto pr-1">
              {visibleRequests.map((request) => (
                <RequestCard
                  key={request.id}
                  request={request}
                  selected={requestToProcess?.id === request.id}
                  onSelect={setSelectedRequest}
                />
              ))}
            </div>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel
            title="3. Resolver solicitacao"
            subtitle="Atualize status ou execute a anonimizacao quando o pedido for de exclusao."
          >
            {requestToProcess ? (
              <div className="space-y-3">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-semibold text-slate-950">
                      {REQUEST_TYPE_LABEL[requestToProcess.request_type] || requestToProcess.request_type}
                    </div>
                    <CopyableCode label="ID" value={requestToProcess.id} />
                  </div>
                  <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
                    <span>Criada: {formatDate(requestToProcess.created_at)}</span>
                    <span>Prazo: {formatDate(requestToProcess.due_at)}</span>
                    <span>Solicitante: {requestToProcess.requester_name || "-"}</span>
                    <span>Email: {requestToProcess.requester_email || "-"}</span>
                  </div>
                </div>

                {requestToProcess.request_type === "deletion" && requestToProcess.subject_type === "customer" ? (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                      <div className="min-w-0 text-sm">
                        <div className="font-semibold text-red-900">
                          Exclusao LGPD: proximo passo e anonimizar
                        </div>
                        <p className="mt-1 text-xs leading-relaxed text-red-700">
                          Remove dados pessoais do cliente e dos pets, revoga consentimentos
                          e preserva historico financeiro/vendas sem identificadores.
                        </p>
                      </div>
                    </div>
                    <ActionButton
                      icon={Trash2}
                      intent="delete"
                      tone="soft"
                      onClick={abrirDialogAnonimizacao}
                      disabled={!canAnonymizeSelected}
                      className="mt-3 w-full"
                    >
                      Anonimizar cliente
                    </ActionButton>
                  </div>
                ) : null}

                <label className="block text-sm font-medium text-slate-700">
                  Status
                  <select
                    value={processForm.status}
                    onChange={(event) =>
                      setProcessForm((current) => ({
                        ...current,
                        status: event.target.value,
                      }))
                    }
                    className="mt-1 h-9 w-full rounded-lg border border-slate-300 px-3 text-sm"
                  >
                    {REQUEST_STATUS.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-sm font-medium text-slate-700">
                  Observacao / resposta
                  <textarea
                    value={processForm.resolution_notes}
                    onChange={(event) =>
                      setProcessForm((current) => ({
                        ...current,
                        resolution_notes: event.target.value,
                      }))
                    }
                    rows={4}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    placeholder="Registre o que foi feito, resposta enviada ou motivo da rejeicao..."
                  />
                </label>

                <ActionButton
                  icon={Save}
                  intent="edit"
                  onClick={processarSolicitacao}
                  loading={saving}
                  className="w-full"
                >
                  Salvar processamento
                </ActionButton>
              </div>
            ) : (
              <EmptyState compact title="Selecione ou abra uma solicitacao" description="Para excluir dados, selecione o titular e clique em Abrir exclusao LGPD." />
            )}
          </Panel>

          <Panel title="Registrar nova solicitacao" subtitle="Use quando o pedido chegar por telefone, loja ou atendimento.">
            <div className="grid gap-3">
              <select
                value={newRequest.request_type}
                onChange={(event) =>
                  setNewRequest((current) => ({
                    ...current,
                    request_type: event.target.value,
                  }))
                }
                className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
              >
                {REQUEST_TYPES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <input
                  value={newRequest.requester_name}
                  onChange={(event) =>
                    setNewRequest((current) => ({
                      ...current,
                      requester_name: event.target.value,
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
                  placeholder="Nome do solicitante"
                />
                <input
                  value={newRequest.requester_email}
                  onChange={(event) =>
                    setNewRequest((current) => ({
                      ...current,
                      requester_email: event.target.value,
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
                  placeholder="Email"
                />
              </div>
              <input
                value={newRequest.requester_phone}
                onChange={(event) =>
                  setNewRequest((current) => ({
                    ...current,
                    requester_phone: event.target.value,
                  }))
                }
                className="h-9 rounded-lg border border-slate-300 px-3 text-sm"
                placeholder="Telefone"
              />
              <textarea
                value={newRequest.details}
                onChange={(event) =>
                  setNewRequest((current) => ({
                    ...current,
                    details: event.target.value,
                  }))
                }
                rows={3}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Detalhes do pedido do titular..."
              />
              <ActionButton
                icon={FileText}
                intent="create"
                onClick={criarSolicitacao}
                loading={saving}
                disabled={!selectedClienteId}
              >
                Registrar para o cliente selecionado
              </ActionButton>
            </div>
          </Panel>
        </div>
      </div>

      <Panel
        title="4. Dossie e preferencias"
        subtitle="Depois de selecionar o titular, carregue o dossie para exportar dados e ajustar consentimentos."
        actions={
          <ActionButton
            icon={Download}
            intent="neutral"
            tone="soft"
            onClick={exportarJson}
            disabled={!dossie}
          >
            Exportar JSON
          </ActionButton>
        }
      >
        {!selectedClienteId ? (
          <EmptyState
            compact
            icon={UserSearch}
            title="Busque um titular primeiro"
            description="A pesquisa fica no passo 1. Depois disso esta area mostra dossie, preferencias e historico."
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="space-y-3">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  {selectedCustomer ? <CustomerIdentity customer={selectedCustomer} /> : null}
                  <StatusBadge intent={selectedCustomer?.ativo === false ? "neutral" : "success"}>
                    {selectedCustomer?.ativo === false ? "Inativo" : "Ativo"}
                  </StatusBadge>
                </div>
                <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-600 sm:grid-cols-2">
                  <span>Email: {selectedCustomer?.email || "-"}</span>
                  <span>Telefone: {selectedCustomer?.telefone || selectedCustomer?.celular || "-"}</span>
                  <span>Codigo: {selectedCustomer?.codigo || "-"}</span>
                  <span>Gerado em: {formatDate(dossie?.generated_at)}</span>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <ActionButton
                    icon={Search}
                    intent="edit"
                    onClick={() => carregarClientePrivacidade()}
                    loading={loadingCliente}
                  >
                    Carregar dossie e consentimentos
                  </ActionButton>
                  <CopyableCode label="Cliente" value={selectedClienteId} />
                </div>
              </div>

              {resumoDossie.length ? (
                <div className="grid grid-cols-2 gap-2">
                  {resumoDossie.map(([label, value]) => (
                    <div key={label} className="rounded-lg border border-slate-200 bg-white p-3">
                      <div className="text-xs font-medium text-slate-500">{label}</div>
                      <div className="mt-1 text-lg font-bold text-slate-950">{value}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  compact
                  icon={UserSearch}
                  title="Dossie ainda nao carregado"
                  description="Clique em Carregar dossie e consentimentos para consultar os dados exportaveis."
                />
              )}
            </div>

            <div className="space-y-4">
              {dossie ? (
                <>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    {PREFERENCES.map(([key, label, description]) => (
                      <PreferenceToggle
                        key={key}
                        name={key}
                        label={label}
                        description={description}
                        value={prefs[key]}
                        onChange={(name, value) =>
                          setPrefs((current) => ({ ...current, [name]: value }))
                        }
                      />
                    ))}
                  </div>

                  <ActionButton
                    icon={Save}
                    intent="edit"
                    onClick={salvarPreferencias}
                    loading={saving}
                  >
                    Salvar preferencias
                  </ActionButton>

                  <div className="rounded-lg border border-slate-200">
                    <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2 text-sm font-semibold text-slate-900">
                      <History className="h-4 w-4 text-slate-500" />
                      Historico recente
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      {consentimentos?.historico?.length ? (
                        consentimentos.historico.slice(0, 20).map((item) => (
                          <div key={item.id} className="border-b border-slate-100 px-3 py-2 text-xs last:border-b-0">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="font-medium text-slate-800">
                                {item.consent_type}
                              </span>
                              <StatusBadge intent={item.consent_given && !item.revoked_at ? "success" : "danger"} size="xs">
                                {item.consent_given && !item.revoked_at ? "Autorizado" : "Revogado"}
                              </StatusBadge>
                            </div>
                            <div className="mt-1 text-slate-500">{formatDate(item.created_at)}</div>
                            {item.consent_text ? (
                              <div className="mt-1 text-slate-500">{item.consent_text}</div>
                            ) : null}
                          </div>
                        ))
                      ) : (
                        <div className="p-4">
                          <EmptyState compact title="Sem historico de consentimento" />
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <EmptyState
                  compact
                  icon={ShieldCheck}
                  title="Preferencias aguardando dossie"
                  description="Carregue os dados do titular para revisar consentimentos e exportar o JSON."
                />
              )}
            </div>
          </div>
        )}
      </Panel>

      {anonymizeDialogOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
            <div className="flex items-start justify-between gap-3 border-b border-slate-200 p-4">
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-red-100 p-2 text-red-600">
                  <Trash2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-950">
                    Anonimizar dados do cliente
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Essa acao remove identificadores pessoais e conclui a solicitacao LGPD.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAnonymizeDialogOpen(false)}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                aria-label="Fechar"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4 p-4">
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                O codigo interno, vendas, pagamentos e historico operacional continuam
                preservados para auditoria. Nome, documentos, contatos, enderecos,
                observacoes sensiveis, dados dos pets e consentimentos ativos serao removidos.
              </div>
              <label className="block text-sm font-medium text-slate-700">
                Observacao da conclusao
                <textarea
                  value={anonymizeForm.resolution_notes}
                  onChange={(event) =>
                    setAnonymizeForm((current) => ({
                      ...current,
                      resolution_notes: event.target.value,
                    }))
                  }
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  placeholder="Ex.: Solicitacao validada com o titular e anonimizada no ERP."
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Digite ANONIMIZAR para confirmar
                <input
                  value={anonymizeForm.confirmacao}
                  onChange={(event) =>
                    setAnonymizeForm((current) => ({
                      ...current,
                      confirmacao: event.target.value,
                    }))
                  }
                  className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
                  placeholder="ANONIMIZAR"
                />
              </label>
            </div>
            <div className="flex flex-col-reverse gap-2 border-t border-slate-200 p-4 sm:flex-row sm:justify-end">
              <ActionButton
                intent="neutral"
                tone="soft"
                onClick={() => setAnonymizeDialogOpen(false)}
                disabled={saving}
              >
                Cancelar
              </ActionButton>
              <ActionButton
                icon={Trash2}
                intent="delete"
                onClick={confirmarAnonimizacao}
                loading={saving}
                disabled={anonymizeForm.confirmacao.trim().toUpperCase() !== "ANONIMIZAR"}
              >
                Confirmar anonimizacao
              </ActionButton>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
