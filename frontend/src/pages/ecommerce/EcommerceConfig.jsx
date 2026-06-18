import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Copy,
  CreditCard,
  ExternalLink,
  KeyRound,
  Unplug,
  Webhook,
} from "lucide-react";
import { api } from "../../services/api";
import { readMercadoPagoOAuthReturn } from "../../utils/mercadoPagoOAuthReturn";

const DIAS_SEMANA = [
  { key: "seg", label: "Segunda" },
  { key: "ter", label: "Terça" },
  { key: "qua", label: "Quarta" },
  { key: "qui", label: "Quinta" },
  { key: "sex", label: "Sexta" },
  { key: "sab", label: "Sábado" },
  { key: "dom", label: "Domingo" },
];

function parseDias(diasStr) {
  if (!diasStr) return [];
  return diasStr
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean);
}

function formatDias(diasArr) {
  return diasArr.join(",");
}

export default function EcommerceConfig() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingPayment, setSavingPayment] = useState(false);
  const [connectingPayment, setConnectingPayment] = useState(false);
  const [disconnectingPayment, setDisconnectingPayment] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [oauthReturn, setOauthReturn] = useState(null);
  const mercadoPagoSectionRef = useRef(null);

  const [ativo, setAtivo] = useState(true);
  const [descricao, setDescricao] = useState("");
  const [horarioAbertura, setHorarioAbertura] = useState("");
  const [horarioFechamento, setHorarioFechamento] = useState("");
  const [diasSelecionados, setDiasSelecionados] = useState([]);
  const [paymentLoading, setPaymentLoading] = useState(true);
  const [paymentConfig, setPaymentConfig] = useState({
    enabled: false,
    environment: "production",
    public_key: "",
    public_key_configured: false,
    public_key_preview: null,
    access_token_configured: false,
    webhook_secret_configured: false,
    oauth_client_id_configured: false,
    oauth_client_id_preview: null,
    oauth_client_secret_configured: false,
    oauth_available: false,
    oauth_connected: false,
    oauth_connected_at: null,
    mercado_pago_user_id: null,
    oauth_redirect_uri: "",
    webhook_url: "",
  });
  const [paymentSecrets, setPaymentSecrets] = useState({
    public_key: "",
    access_token: "",
    webhook_secret: "",
    oauth_client_id: "",
    oauth_client_secret: "",
  });

  // Avise-me pendentes
  const [avisos, setAvisos] = useState([]);
  const [loadingAvisos, setLoadingAvisos] = useState(true);

  useEffect(() => {
    const oauthResult = readMercadoPagoOAuthReturn(window.location.search);
    if (oauthResult) {
      setOauthReturn(oauthResult);
      if (oauthResult.status === "success") {
        setSuccess(oauthResult.message);
      } else {
        setError(oauthResult.message);
      }
      window.history.replaceState({}, "", window.location.pathname);
      window.setTimeout(() => {
        mercadoPagoSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 150);
    }
    fetchConfig();
    fetchAvisos();
    fetchPaymentConfig();
  }, []);

  function applyPaymentConfigResponse(data) {
    const d = data || {};
    setPaymentConfig({
      enabled: Boolean(d.enabled),
      environment: d.environment || "production",
      public_key: "",
      public_key_configured: Boolean(d.public_key_configured),
      public_key_preview: d.public_key_preview || null,
      access_token_configured: Boolean(d.access_token_configured),
      webhook_secret_configured: Boolean(d.webhook_secret_configured),
      oauth_client_id_configured: Boolean(d.oauth_client_id_configured),
      oauth_client_id_preview: d.oauth_client_id_preview || null,
      oauth_client_secret_configured: Boolean(d.oauth_client_secret_configured),
      oauth_available: Boolean(d.oauth_available),
      oauth_connected: Boolean(d.oauth_connected),
      oauth_connected_at: d.oauth_connected_at || null,
      mercado_pago_user_id: d.mercado_pago_user_id || null,
      oauth_redirect_uri: d.oauth_redirect_uri || "",
      webhook_url: d.webhook_url || "",
    });
  }

  async function fetchConfig() {
    try {
      const res = await api.get("/ecommerce-config");
      const d = res.data;
      setAtivo(d.ecommerce_ativo ?? true);
      setDescricao(d.ecommerce_descricao || "");
      setHorarioAbertura(d.ecommerce_horario_abertura || "");
      setHorarioFechamento(d.ecommerce_horario_fechamento || "");
      setDiasSelecionados(parseDias(d.ecommerce_dias_funcionamento));
    } catch {
      setError("Não foi possível carregar as configurações.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchAvisos() {
    try {
      const res = await api.get("/ecommerce-notify/pendentes");
      setAvisos(res.data || []);
    } catch {
      // silencioso
    } finally {
      setLoadingAvisos(false);
    }
  }

  async function fetchPaymentConfig() {
    try {
      const res = await api.get("/ecommerce-payment-config/mercadopago");
      applyPaymentConfigResponse(res.data);
    } catch {
      setError("Nao foi possivel carregar a configuracao de pagamento.");
    } finally {
      setPaymentLoading(false);
    }
  }

  async function salvar(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await api.put("/ecommerce-config", {
        ecommerce_ativo: ativo,
        ecommerce_descricao: descricao || null,
        ecommerce_horario_abertura: horarioAbertura || null,
        ecommerce_horario_fechamento: horarioFechamento || null,
        ecommerce_dias_funcionamento:
          diasSelecionados.length > 0 ? formatDias(diasSelecionados) : null,
      });
      setSuccess("Configurações salvas com sucesso!");
      setTimeout(() => setSuccess(""), 4000);
    } catch {
      setError("Erro ao salvar. Tente novamente.");
    } finally {
      setSaving(false);
    }
  }

  async function salvarPagamento(e) {
    e.preventDefault();
    setSavingPayment(true);
    setError("");
    setSuccess("");
    setOauthReturn(null);
    try {
      const res = await api.put("/ecommerce-payment-config/mercadopago", {
        enabled: paymentConfig.enabled,
        environment: paymentConfig.environment,
        public_key: paymentSecrets.public_key || null,
        access_token: paymentSecrets.access_token || null,
        webhook_secret: paymentSecrets.webhook_secret || null,
        oauth_client_id: paymentSecrets.oauth_client_id || null,
        oauth_client_secret: paymentSecrets.oauth_client_secret || null,
      });
      applyPaymentConfigResponse(res.data);
      setPaymentSecrets({
        public_key: "",
        access_token: "",
        webhook_secret: "",
        oauth_client_id: "",
        oauth_client_secret: "",
      });
      setSuccess("Configuracao do Mercado Pago salva com sucesso!");
      setTimeout(() => setSuccess(""), 4000);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Erro ao salvar Mercado Pago. Confira as credenciais.",
      );
    } finally {
      setSavingPayment(false);
    }
  }

  async function conectarMercadoPago() {
    setConnectingPayment(true);
    setError("");
    setSuccess("");
    setOauthReturn(null);
    try {
      const res = await api.get("/ecommerce-payment-config/mercadopago/oauth/url");
      const data = res.data || {};
      if (!data.configured || !data.authorization_url) {
        const missing =
          Array.isArray(data.missing) && data.missing.length > 0
            ? ` (${data.missing.join(", ")})`
            : "";
        setError(`OAuth Mercado Pago ainda nao esta configurado no servidor CorePet${missing}.`);
        return;
      }
      window.location.assign(data.authorization_url);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Nao foi possivel iniciar a conexao com o Mercado Pago.",
      );
    } finally {
      setConnectingPayment(false);
    }
  }

  async function desconectarMercadoPago() {
    setDisconnectingPayment(true);
    setError("");
    setSuccess("");
    setOauthReturn(null);
    try {
      const res = await api.post("/ecommerce-payment-config/mercadopago/oauth/disconnect");
      applyPaymentConfigResponse(res.data);
      setPaymentSecrets({
        public_key: "",
        access_token: "",
        webhook_secret: "",
        oauth_client_id: "",
        oauth_client_secret: "",
      });
      setSuccess("Mercado Pago desconectado desta loja.");
      setTimeout(() => setSuccess(""), 4000);
    } catch (err) {
      setError(err.response?.data?.detail || "Nao foi possivel desconectar o Mercado Pago.");
    } finally {
      setDisconnectingPayment(false);
    }
  }

  async function copiarTexto(texto, mensagem) {
    if (!texto) return;
    try {
      await navigator.clipboard.writeText(texto);
      setSuccess(mensagem);
      setTimeout(() => setSuccess(""), 2500);
    } catch {
      setError("Nao foi possivel copiar automaticamente.");
    }
  }

  function copiarWebhookUrl() {
    copiarTexto(paymentConfig.webhook_url, "URL do webhook copiada.");
  }

  function copiarOAuthRedirectUri() {
    copiarTexto(paymentConfig.oauth_redirect_uri, "URL de retorno OAuth copiada.");
  }

  function toggleDia(key) {
    setDiasSelecionados((prev) =>
      prev.includes(key) ? prev.filter((d) => d !== key) : [...prev, key],
    );
  }

  function statusConfigurado(configurado, preview = null) {
    if (!configurado) return null;
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
        <CheckCircle2 size={12} />
        {preview ? `Configurado (${preview})` : "Configurado"}
      </span>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  // Agrupar avisos por produto
  const avisosPorProduto = avisos.reduce((acc, aviso) => {
    const key = `${aviso.product_id}__${aviso.product_name || "Produto"}`;
    if (!acc[key])
      acc[key] = {
        product_id: aviso.product_id,
        product_name: aviso.product_name || "Produto",
        emails: [],
      };
    acc[key].emails.push(aviso.email);
    return acc;
  }, {});

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">⚙️ Configurações da Loja Virtual</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm">
          {success}
        </div>
      )}

      <form onSubmit={salvar} className="space-y-6">
        {/* Status da loja */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Status da Loja</h2>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-700">Loja online</p>
              <p className="text-sm text-gray-500">
                {ativo
                  ? "Sua loja está visível e aceitando pedidos."
                  : "Sua loja está offline. Clientes não conseguem fazer pedidos."}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAtivo((v) => !v)}
              className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none ${
                ativo ? "bg-indigo-500" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                  ativo ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Descrição */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-3">
          <h2 className="text-base font-semibold text-gray-800">Descrição da Loja</h2>
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            rows={3}
            maxLength={500}
            placeholder="Ex.: Petshop especializado em cães e gatos. Atendemos com carinho! 🐾"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
          />
          <p className="text-xs text-gray-400 text-right">{descricao.length}/500</p>
        </div>

        {/* Horário */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Horário de Funcionamento</h2>
          <p className="text-sm text-gray-500">
            Exibido como informação na loja. Não bloqueia pedidos fora do horário.
          </p>
          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Abertura</label>
              <input
                type="time"
                value={horarioAbertura}
                onChange={(e) => setHorarioAbertura(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <span className="text-gray-400 mt-5">até</span>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Fechamento</label>
              <input
                type="time"
                value={horarioFechamento}
                onChange={(e) => setHorarioFechamento(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          </div>

          {/* Dias da semana */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-2">Dias de funcionamento</p>
            <div className="flex flex-wrap gap-2">
              {DIAS_SEMANA.map((dia) => (
                <button
                  key={dia.key}
                  type="button"
                  onClick={() => toggleDia(dia.key)}
                  className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
                    diasSelecionados.includes(dia.key)
                      ? "bg-indigo-500 text-white border-indigo-500"
                      : "bg-white text-gray-600 border-gray-300 hover:border-indigo-400"
                  }`}
                >
                  {dia.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl transition-colors"
        >
          {saving ? "Salvando…" : "Salvar Configurações"}
        </button>
      </form>

      {/* Pagamentos online */}
      <form ref={mercadoPagoSectionRef} onSubmit={salvarPagamento} className="space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-5">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <CreditCard size={20} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-gray-800">Mercado Pago</h2>
              <p className="text-sm text-gray-500">
                Conta que recebe os pagamentos Pix, debito e credito desta loja.
              </p>
            </div>
          </div>

          {paymentLoading ? (
            <div className="animate-pulse h-24 bg-gray-100 rounded-lg" />
          ) : (
            <>
              {oauthReturn && (
                <div
                  className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${
                    oauthReturn.status === "success"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-red-200 bg-red-50 text-red-700"
                  }`}
                >
                  <div className="mt-0.5">
                    {oauthReturn.status === "success" ? (
                      <CheckCircle2 size={18} />
                    ) : (
                      <AlertCircle size={18} />
                    )}
                  </div>
                  <div>
                    <p className="font-semibold">
                      {oauthReturn.status === "success"
                        ? "Conexao concluida"
                        : "Conexao nao concluida"}
                    </p>
                    <p>{oauthReturn.message}</p>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between gap-4 border border-gray-100 rounded-lg p-4">
                <div>
                  <p className="font-medium text-gray-700">Pagamento online</p>
                  <p className="text-sm text-gray-500">
                    {paymentConfig.enabled
                      ? "Ativo no app e e-commerce."
                      : "Desligado para esta loja."}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setPaymentConfig((prev) => ({ ...prev, enabled: !prev.enabled }))}
                  className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none ${
                    paymentConfig.enabled ? "bg-emerald-500" : "bg-gray-300"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                      paymentConfig.enabled ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              <div className="border border-emerald-100 rounded-lg p-4 bg-emerald-50/40 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div
                      className={`mt-0.5 h-8 w-8 rounded-full flex items-center justify-center ${
                        paymentConfig.oauth_connected
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-white text-gray-500"
                      }`}
                    >
                      <CheckCircle2 size={18} />
                    </div>
                    <div>
                      <p className="font-medium text-gray-800">
                        {paymentConfig.oauth_connected
                          ? "Conta Mercado Pago conectada"
                          : "Conectar conta Mercado Pago"}
                      </p>
                      <p className="text-sm text-gray-500">
                        {paymentConfig.oauth_connected
                          ? `Recebendo nesta loja${paymentConfig.mercado_pago_user_id ? ` (conta ${paymentConfig.mercado_pago_user_id})` : ""}.`
                          : "O cliente autoriza a propria conta e os tokens ficam salvos no tenant."}
                      </p>
                    </div>
                  </div>
                  {paymentConfig.oauth_connected ? (
                    <button
                      type="button"
                      onClick={desconectarMercadoPago}
                      disabled={disconnectingPayment}
                      className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      <Unplug size={16} />
                      {disconnectingPayment ? "Desconectando..." : "Desconectar"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={conectarMercadoPago}
                      disabled={connectingPayment || !paymentConfig.oauth_available}
                      className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      <ExternalLink size={16} />
                      {connectingPayment ? "Abrindo..." : "Conectar"}
                    </button>
                  )}
                </div>
                {!paymentConfig.oauth_available && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-md px-3 py-2">
                    O botao sera liberado quando o Client ID e Client Secret OAuth forem salvos
                    abaixo.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  URL do webhook
                </label>
                <div className="flex gap-2">
                  <input
                    value={paymentConfig.webhook_url}
                    readOnly
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-700"
                  />
                  <button
                    type="button"
                    onClick={copiarWebhookUrl}
                    className="inline-flex items-center justify-center h-10 w-10 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
                    title="Copiar URL"
                  >
                    <Copy size={18} />
                  </button>
                </div>
              </div>

              <details className="border border-gray-200 rounded-lg">
                <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-gray-700">
                  Configuracao avancada
                </summary>
                <div className="px-4 pb-4 pt-1 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Ambiente
                      </label>
                      <select
                        value={paymentConfig.environment}
                        onChange={(e) =>
                          setPaymentConfig((prev) => ({ ...prev, environment: e.target.value }))
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white"
                      >
                        <option value="production">Producao</option>
                        <option value="sandbox">Teste / Sandbox</option>
                      </select>
                    </div>
                    <div>
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <label className="block text-xs font-medium text-gray-600">
                          Public key
                        </label>
                        {statusConfigurado(
                          paymentConfig.public_key_configured,
                          paymentConfig.public_key_preview,
                        )}
                      </div>
                      <input
                        type="password"
                        value={paymentSecrets.public_key}
                        onChange={(e) =>
                          setPaymentSecrets((prev) => ({ ...prev, public_key: e.target.value }))
                        }
                        placeholder={
                          paymentConfig.public_key_configured
                            ? "Public key ja configurada"
                            : "APP_USR-..."
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      URL de retorno OAuth
                    </label>
                    <div className="flex gap-2">
                      <input
                        value={paymentConfig.oauth_redirect_uri}
                        readOnly
                        className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-700"
                      />
                      <button
                        type="button"
                        onClick={copiarOAuthRedirectUri}
                        className="inline-flex items-center justify-center h-10 w-10 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
                        title="Copiar URL de retorno OAuth"
                      >
                        <Copy size={18} />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <label className="flex items-center gap-1 text-xs font-medium text-gray-600">
                          <KeyRound size={14} />
                          OAuth Client ID
                        </label>
                        {statusConfigurado(
                          paymentConfig.oauth_client_id_configured,
                          paymentConfig.oauth_client_id_preview,
                        )}
                      </div>
                      <input
                        value={paymentSecrets.oauth_client_id}
                        onChange={(e) =>
                          setPaymentSecrets((prev) => ({
                            ...prev,
                            oauth_client_id: e.target.value,
                          }))
                        }
                        placeholder={
                          paymentConfig.oauth_client_id_configured
                            ? "Client ID ja configurado"
                            : "Client ID da aplicacao"
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                      />
                    </div>
                    <div>
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <label className="flex items-center gap-1 text-xs font-medium text-gray-600">
                          <KeyRound size={14} />
                          OAuth Client Secret
                        </label>
                        {statusConfigurado(paymentConfig.oauth_client_secret_configured)}
                      </div>
                      <input
                        type="password"
                        value={paymentSecrets.oauth_client_secret}
                        onChange={(e) =>
                          setPaymentSecrets((prev) => ({
                            ...prev,
                            oauth_client_secret: e.target.value,
                          }))
                        }
                        placeholder={
                          paymentConfig.oauth_client_secret_configured
                            ? "Client Secret ja configurado"
                            : "Client Secret da aplicacao"
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <label className="flex items-center gap-1 text-xs font-medium text-gray-600">
                          <KeyRound size={14} />
                          Access token
                        </label>
                        {statusConfigurado(paymentConfig.access_token_configured)}
                      </div>
                      <input
                        type="password"
                        value={paymentSecrets.access_token}
                        onChange={(e) =>
                          setPaymentSecrets((prev) => ({ ...prev, access_token: e.target.value }))
                        }
                        placeholder={
                          paymentConfig.access_token_configured
                            ? "Token ja configurado"
                            : "APP_USR-..."
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                      />
                    </div>
                    <div>
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <label className="flex items-center gap-1 text-xs font-medium text-gray-600">
                          <Webhook size={14} />
                          Assinatura secreta
                        </label>
                        {statusConfigurado(paymentConfig.webhook_secret_configured)}
                      </div>
                      <input
                        type="password"
                        value={paymentSecrets.webhook_secret}
                        onChange={(e) =>
                          setPaymentSecrets((prev) => ({ ...prev, webhook_secret: e.target.value }))
                        }
                        placeholder={
                          paymentConfig.webhook_secret_configured
                            ? "Assinatura ja configurada"
                            : "Cole a assinatura secreta do webhook"
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
                      />
                    </div>
                  </div>
                </div>
              </details>
            </>
          )}
        </div>

        <button
          type="submit"
          disabled={savingPayment || paymentLoading}
          className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl transition-colors"
        >
          {savingPayment ? "Salvando..." : "Salvar Mercado Pago"}
        </button>
      </form>

      {/* Avisos de Estoque Pendentes */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800">🔔 Avisos de Estoque Pendentes</h2>
          {avisos.length > 0 && (
            <span className="bg-red-100 text-red-600 text-xs font-bold px-2 py-0.5 rounded-full">
              {avisos.length}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500">
          Clientes que pediram para ser avisados quando um produto voltar ao estoque. Os emails são
          enviados automaticamente quando você aumenta o estoque do produto.
        </p>

        {loadingAvisos ? (
          <div className="animate-pulse h-10 bg-gray-100 rounded" />
        ) : Object.keys(avisosPorProduto).length === 0 ? (
          <p className="text-sm text-gray-400 italic">Nenhum aviso pendente no momento.</p>
        ) : (
          <div className="space-y-3">
            {Object.values(avisosPorProduto).map((grupo) => (
              <div
                key={grupo.product_id}
                className="border border-gray-100 rounded-lg p-3 space-y-1"
              >
                <p className="font-medium text-sm text-gray-800">{grupo.product_name}</p>
                <p className="text-xs text-gray-500">
                  {grupo.emails.length} cliente{grupo.emails.length !== 1 ? "s" : ""} aguardando:{" "}
                  <span className="text-gray-400">{grupo.emails.join(", ")}</span>
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
