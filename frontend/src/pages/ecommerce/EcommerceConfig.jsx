import { useEffect, useRef, useState } from "react";
import EcommerceConfigView from "./EcommerceConfigView";
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

  return (
    <EcommerceConfigView
      loading={loading}
      error={error}
      success={success}
      salvar={salvar}
      ativo={ativo}
      setAtivo={setAtivo}
      descricao={descricao}
      setDescricao={setDescricao}
      horarioAbertura={horarioAbertura}
      setHorarioAbertura={setHorarioAbertura}
      horarioFechamento={horarioFechamento}
      setHorarioFechamento={setHorarioFechamento}
      diasSelecionados={diasSelecionados}
      toggleDia={toggleDia}
      diasSemana={DIAS_SEMANA}
      saving={saving}
      mercadoPagoSectionRef={mercadoPagoSectionRef}
      salvarPagamento={salvarPagamento}
      paymentLoading={paymentLoading}
      oauthReturn={oauthReturn}
      paymentConfig={paymentConfig}
      setPaymentConfig={setPaymentConfig}
      desconectarMercadoPago={desconectarMercadoPago}
      disconnectingPayment={disconnectingPayment}
      conectarMercadoPago={conectarMercadoPago}
      connectingPayment={connectingPayment}
      copiarWebhookUrl={copiarWebhookUrl}
      copiarOAuthRedirectUri={copiarOAuthRedirectUri}
      paymentSecrets={paymentSecrets}
      setPaymentSecrets={setPaymentSecrets}
      savingPayment={savingPayment}
      avisos={avisos}
      loadingAvisos={loadingAvisos}
    />
  );
}
