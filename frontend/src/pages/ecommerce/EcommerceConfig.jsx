import { useEffect, useRef, useState } from "react";
import EcommerceConfigView from "./EcommerceConfigView";
import { api } from "../../services/api";
import { readMercadoPagoOAuthReturn } from "../../utils/mercadoPagoOAuthReturn";
import { confirmarCorePet } from "../../services/corepetDialog";

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
  const [commerceConfig, setCommerceConfig] = useState({
    entregaAtiva: true,
    retiradaAtiva: true,
    taxaEntrega: 0,
    freteGratisAcima: 0,
    pedidoMinimo: 0,
    prazoEntrega: "",
    usarEstoqueCanal: false,
    ocultarSemEstoque: true,
    ocultarSemImagem: false,
    ocultarServicos: true,
    corPrimaria: "#f97316",
    corSecundaria: "#0f766e",
  });
  const [paymentLoading, setPaymentLoading] = useState(true);
  const [paymentAccountLoading, setPaymentAccountLoading] = useState(false);
  const [paymentAccountError, setPaymentAccountError] = useState("");
  const [paymentAccount, setPaymentAccount] = useState(null);
  const [paymentConfig, setPaymentConfig] = useState({
    enabled: false,
    access_token_configured: false,
    oauth_available: false,
    oauth_connected: false,
    oauth_connected_at: null,
    mercado_pago_user_id: null,
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
      access_token_configured: Boolean(d.access_token_configured),
      oauth_available: Boolean(d.oauth_available),
      oauth_connected: Boolean(d.oauth_connected),
      oauth_connected_at: d.oauth_connected_at || null,
      mercado_pago_user_id: d.mercado_pago_user_id || null,
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
      setCommerceConfig({
        entregaAtiva: d.ecommerce_entrega_ativa ?? true,
        retiradaAtiva: d.ecommerce_retirada_ativa ?? true,
        taxaEntrega: Number(d.ecommerce_taxa_entrega || 0),
        freteGratisAcima: Number(d.ecommerce_frete_gratis_acima || 0),
        pedidoMinimo: Number(d.ecommerce_pedido_minimo || 0),
        prazoEntrega: d.ecommerce_prazo_entrega_texto || "",
        usarEstoqueCanal: d.ecommerce_usar_estoque_canal ?? false,
        ocultarSemEstoque: d.ecommerce_ocultar_sem_estoque ?? true,
        ocultarSemImagem: d.ecommerce_ocultar_sem_imagem ?? false,
        ocultarServicos: d.ecommerce_ocultar_servicos ?? true,
        corPrimaria: d.ecommerce_cor_primaria || "#f97316",
        corSecundaria: d.ecommerce_cor_secundaria || "#0f766e",
      });
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
      if (res.data?.oauth_connected) {
        void fetchPaymentAccountIdentity();
      } else {
        setPaymentAccount(null);
        setPaymentAccountError("");
      }
    } catch {
      setError("Nao foi possivel carregar a configuracao de pagamento.");
    } finally {
      setPaymentLoading(false);
    }
  }

  async function fetchPaymentAccountIdentity() {
    setPaymentAccountLoading(true);
    setPaymentAccountError("");
    try {
      const res = await api.get("/ecommerce-payment-config/mercadopago/account-identity");
      setPaymentAccount(res.data || null);
    } catch {
      setPaymentAccount(null);
      setPaymentAccountError("Não foi possível confirmar os dados da conta no Mercado Pago agora.");
    } finally {
      setPaymentAccountLoading(false);
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
        ecommerce_usar_estoque_canal: commerceConfig.usarEstoqueCanal,
        ecommerce_ocultar_sem_estoque: commerceConfig.ocultarSemEstoque,
        ecommerce_ocultar_sem_imagem: commerceConfig.ocultarSemImagem,
        ecommerce_ocultar_servicos: commerceConfig.ocultarServicos,
        ecommerce_cor_primaria: commerceConfig.corPrimaria,
        ecommerce_cor_secundaria: commerceConfig.corSecundaria,
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
      });
      applyPaymentConfigResponse(res.data);
      setSuccess("Preferência de pagamento salva com sucesso!");
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
        setError("A conexão está temporariamente indisponível. Fale com o suporte CorePet.");
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
    if (
      !(await confirmarCorePet(
        "Desconectar o Mercado Pago vai impedir novos pagamentos online. Deseja continuar?",
      ))
    ) {
      return;
    }
    setDisconnectingPayment(true);
    setError("");
    setSuccess("");
    setOauthReturn(null);
    try {
      const res = await api.post("/ecommerce-payment-config/mercadopago/oauth/disconnect");
      applyPaymentConfigResponse(res.data);
      setPaymentAccount(null);
      setPaymentAccountError("");
      setSuccess("Mercado Pago desconectado desta loja.");
      setTimeout(() => setSuccess(""), 4000);
    } catch (err) {
      setError(err.response?.data?.detail || "Nao foi possivel desconectar o Mercado Pago.");
    } finally {
      setDisconnectingPayment(false);
    }
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
      commerceConfig={commerceConfig}
      setCommerceConfig={setCommerceConfig}
      saving={saving}
      mercadoPagoSectionRef={mercadoPagoSectionRef}
      salvarPagamento={salvarPagamento}
      paymentLoading={paymentLoading}
      oauthReturn={oauthReturn}
      paymentConfig={paymentConfig}
      paymentAccount={paymentAccount}
      paymentAccountLoading={paymentAccountLoading}
      paymentAccountError={paymentAccountError}
      recarregarPaymentAccount={fetchPaymentAccountIdentity}
      setPaymentConfig={setPaymentConfig}
      desconectarMercadoPago={desconectarMercadoPago}
      disconnectingPayment={disconnectingPayment}
      conectarMercadoPago={conectarMercadoPago}
      connectingPayment={connectingPayment}
      savingPayment={savingPayment}
      avisos={avisos}
      loadingAvisos={loadingAvisos}
    />
  );
}
