import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import {
  FiAlertCircle,
  FiCheckCircle,
  FiClock,
  FiCreditCard,
  FiEye,
  FiEyeOff,
  FiFileText,
  FiGrid,
  FiMail,
  FiPackage,
  FiRefreshCw,
  FiSave,
  FiX,
  FiXCircle,
} from "react-icons/fi";
import { api } from "../../services/api";
import SefazIntegracaoCard from "./SefazIntegracaoCard";

/**
 * Página de configuração e ativação da integração Stone.
 *
 * Módulo 1 — Stone Connect (maquininha / pedidos POS via Pagar.me)
 *   - Usuário informa a chave sk_* (obtida em id.pagar.me)
 *   - Sistema salva no banco e fica pronto para criar pedidos na maquininha
 *
 * Módulo 2 — Stone Conciliação (relatório financeiro automático)
 *   - Usuário informa CNPJ e Stone Code
 *   - Clica "Solicitar Acesso"
 *   - Stone envia e-mail ao lojista para aprovar
 *   - Quando aprovado, as credenciais chegam automaticamente no sistema
 */
export default function StoneIntegracao() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [solicitando, setSolicitando] = useState(false);
  const [mostrarChave, setMostrarChave] = useState(false);
  const [modalAtivo, setModalAtivo] = useState(null);
  const [msg, setMsg] = useState(null); // { tipo: 'sucesso'|'erro', texto: '' }
  const [renovandoBling, setRenovandoBling] = useState(false);
  const [testandoBling, setTestandoBling] = useState(false);
  const [sefazStatus, setSefazStatus] = useState({
    enabled: false,
    cert_ok: false,
    mensagem: "",
  });
  const [blingStatus, setBlingStatus] = useState({
    conectado: false,
    mensagem: "Configuração pendente",
    detalhe: "Token não validado",
    renovacoes_automaticas: 0,
    proxima_renovacao: null,
  });

  const [config, setConfig] = useState({
    // Connect (Pagar.me)
    client_id: "", // sk_* da conta Pagar.me
    webhook_secret: "",
    enable_pix: true,
    enable_credit_card: true,
    enable_debit_card: true,
    active: false,
    // Conciliação
    affiliation_code: "", // Stone Code
    documento: "", // CNPJ
    webhook_url: "", // URL pública para receber resposta
    // Status vindos do banco (somente leitura)
    conciliacao_username: null,
    conciliacao_configurado: false,
  });

  const webhookUrlPadrao = `${globalThis.location.origin}/api/stone/webhook-consentimento`;

  useEffect(() => {
    carregarConfig();
  }, []);

  function formatarDataHora(value) {
    if (!value) return "-";
    const data = new Date(value);
    if (Number.isNaN(data.getTime())) return "-";
    return data.toLocaleString("pt-BR");
  }

  async function carregarConfig() {
    try {
      const [stoneResp, sefazResp, blingResp] = await Promise.all([
        api.get("/stone/config"),
        api.get("/sefaz/config").catch(() => null),
        api.get("/bling/teste-conexao").catch(() => null),
      ]);

      const { data } = stoneResp;
      setConfig((prev) => ({
        ...prev,
        ...data,
        webhook_url: data.webhook_url || webhookUrlPadrao,
      }));

      if (sefazResp?.data) {
        setSefazStatus({
          enabled: Boolean(sefazResp.data.enabled),
          cert_ok: Boolean(sefazResp.data.cert_ok),
          mensagem: sefazResp.data.mensagem || "",
        });
      }

      if (blingResp?.data) {
        const conectado = Boolean(blingResp.data.conectado || blingResp.data.success);
        const proximaRenovacao = blingResp.data.proxima_renovacao || null;

        setBlingStatus({
          conectado,
          mensagem: blingResp.data.message || (conectado ? "Conexão ativa" : "Token expirado"),
          detalhe: conectado
            ? `Próxima renovação: ${formatarDataHora(proximaRenovacao)}`
            : (blingResp.data.detail || "Token expirado ou inválido"),
          renovacoes_automaticas: blingResp.data.renovacoes_automaticas || 0,
          proxima_renovacao: proximaRenovacao,
        });
      }
    } catch (e) {
      if (e.response?.status !== 404) {
        mostrarMensagem("erro", "Erro ao carregar configuração.");
      }
      setConfig((prev) => ({ ...prev, webhook_url: webhookUrlPadrao }));
    } finally {
      setLoading(false);
    }
  }

  function mostrarMensagem(tipo, texto) {
    setMsg({ tipo, texto });
    setTimeout(() => setMsg(null), 6000);
  }

  async function testarConexaoBling() {
    setTestandoBling(true);
    try {
      const resp = await api.get("/bling/teste-conexao");
      const conectado = Boolean(resp.data.conectado || resp.data.success);
      const proximaRenovacao = resp.data.proxima_renovacao || null;

      setBlingStatus({
        conectado,
        mensagem: resp.data.message || (conectado ? "Conexão ativa" : "Token expirado"),
        detalhe: conectado
          ? `Próxima renovação: ${formatarDataHora(proximaRenovacao)}`
          : (resp.data.detail || "Token expirado ou inválido"),
        renovacoes_automaticas: resp.data.renovacoes_automaticas || 0,
        proxima_renovacao: proximaRenovacao,
      });

      mostrarMensagem(
        conectado ? "sucesso" : "erro",
        conectado ? "Bling conectado com sucesso." : "Bling desconectado. Renove o token.",
      );
    } catch (e) {
      mostrarMensagem("erro", "Erro ao testar conexão do Bling.");
    } finally {
      setTestandoBling(false);
    }
  }

  async function renovarTokenBling() {
    setRenovandoBling(true);
    try {
      await api.post("/bling/renovar-token");
      mostrarMensagem("sucesso", "Token do Bling renovado com sucesso.");
      await testarConexaoBling();
    } catch (e) {
      // Se o refresh token expirou, redireciona para autorização OAuth
      const detail = e.response?.data?.detail || "";
      const isInvalidGrant =
        detail.includes("invalid_grant") ||
        detail.includes("Invalid refresh token") ||
        e.response?.status === 400;

      if (isInvalidGrant) {
        mostrarMensagem("info", "Abrindo autorização no Bling...");
        try {
          const linkResp = await api.get("/auth/bling/link-autorizacao");
          const url = linkResp.data?.url_autorizacao || linkResp.data?.url;
          if (url) {
            window.location.href = url;
            return;
          }
        } catch {
          // fallback abaixo
        }
      }

      mostrarMensagem(
        "erro",
        detail || "Não foi possível renovar o token do Bling.",
      );
    } finally {
      setRenovandoBling(false);
    }
  }

  async function salvarConfiguracaoConnect(e) {
    e.preventDefault();
    if (!config.client_id.startsWith("sk_")) {
      mostrarMensagem(
        "erro",
        "A chave secreta deve começar com sk_. Verifique em id.pagar.me.",
      );
      return;
    }
    setSaving(true);
    try {
      await api.post("/stone/config", {
        client_id: config.client_id,
        client_secret: "",
        merchant_id: null,
        sandbox: false,
        webhook_secret: config.webhook_secret,
        enable_pix: config.enable_pix,
        enable_credit_card: config.enable_credit_card,
        enable_debit_card: config.enable_debit_card,
        active: true,
        affiliation_code: config.affiliation_code,
        documento: config.documento,
        webhook_url: config.webhook_url || webhookUrlPadrao,
      });
      mostrarMensagem(
        "sucesso",
        "Configuração Stone Connect salva com sucesso!",
      );
      await carregarConfig();
    } catch (e) {
      mostrarMensagem(
        "erro",
        e.response?.data?.detail || "Erro ao salvar. Tente novamente.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function solicitarConsentimentoConciliacao() {
    if (!config.affiliation_code) {
      mostrarMensagem(
        "erro",
        "Preencha o Stone Code (código de afiliação) primeiro.",
      );
      return;
    }
    if (!config.documento) {
      mostrarMensagem("erro", "Preencha o CNPJ da empresa primeiro.");
      return;
    }
    setSolicitando(true);
    try {
      // Salva os dados de conciliação antes de solicitar
      await api.post("/stone/config", {
        client_id: config.client_id || "",
        client_secret: "",
        merchant_id: null,
        sandbox: false,
        affiliation_code: config.affiliation_code,
        documento: config.documento.replaceAll(/\D/g, ""),
        webhook_url: config.webhook_url || webhookUrlPadrao,
        active: config.active,
      });

      // Solicita o consentimento
      await api.post("/stone/solicitar-consentimento", {
        documento: config.documento.replaceAll(/\D/g, ""),
        affiliation_code: config.affiliation_code,
        webhook_url: config.webhook_url || webhookUrlPadrao,
      });

      mostrarMensagem(
        "sucesso",
        "✅ Solicitação enviada! A Stone vai mandar um e-mail para o responsável pelo CNPJ informado. Após aprovar, a integração ativa automaticamente.",
      );
    } catch (e) {
      mostrarMensagem(
        "erro",
        e.response?.data?.detail ||
          "Erro ao solicitar consentimento. Verifique os dados.",
      );
    } finally {
      setSolicitando(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <FiRefreshCw className="animate-spin mr-2" /> Carregando...
      </div>
    );
  }

  const conectadoConnect = config.active && config.client_id?.startsWith("sk_");
  const conectadoConciliacao = config.conciliacao_configurado;
  const conectadoSefaz = sefazStatus.enabled && sefazStatus.cert_ok;
  let textoBotaoConnect = "Ativar Connect";
  if (saving) textoBotaoConnect = "Salvando...";
  if (!saving && conectadoConnect) textoBotaoConnect = "Atualizar Chave";

  let detalheConciliacao = "CNPJ e Stone Code pendentes";
  if (config.affiliation_code) detalheConciliacao = "Aguardando aprovação no e-mail";
  if (conectadoConciliacao) {
    detalheConciliacao = `Usuário: ${config.conciliacao_username || "vinculado"}`;
  }

  let statusConciliacao = "desconectado";
  if (config.affiliation_code) statusConciliacao = "pendente";
  if (conectadoConciliacao) statusConciliacao = "conectado";

  function abrirModal(modulo) {
    setModalAtivo(modulo);
  }

  function fecharModal() {
    setModalAtivo(null);
  }

  function renderModalConteudo() {
    if (modalAtivo === "stone-connect") {
      return (
        <form onSubmit={salvarConfiguracaoConnect} className="space-y-4">
          <input
            type="text"
            name="username"
            autoComplete="username"
            value="stone"
            readOnly
            className="hidden"
            tabIndex={-1}
            aria-hidden="true"
          />

          {!conectadoConnect && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800 flex gap-2">
              <FiAlertCircle className="shrink-0 mt-0.5" />
              <span>
                Para obter sua chave, acesse <strong>id.pagar.me</strong> e
                copie a chave que começa com <strong>sk_</strong>.
              </span>
            </div>
          )}

          <div>
            <label
              htmlFor="stone-client-id"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Chave Secreta (sk_*)
            </label>
            <div className="relative">
              <input
                id="stone-client-id"
                type={mostrarChave ? "text" : "password"}
                autoComplete="current-password"
                className="w-full border rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                value={config.client_id}
                onChange={(e) =>
                  setConfig({ ...config, client_id: e.target.value })
                }
                required
              />
              <button
                type="button"
                className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
                onClick={() => setMostrarChave((v) => !v)}
              >
                {mostrarChave ? <FiEyeOff size={16} /> : <FiEye size={16} />}
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.enable_pix}
                onChange={(e) =>
                  setConfig({ ...config, enable_pix: e.target.checked })
                }
              />
              <span>Aceitar PIX</span>
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.enable_credit_card}
                onChange={(e) =>
                  setConfig({ ...config, enable_credit_card: e.target.checked })
                }
              />
              <span>Aceitar Crédito</span>
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.enable_debit_card}
                onChange={(e) =>
                  setConfig({ ...config, enable_debit_card: e.target.checked })
                }
              />
              <span>Aceitar Débito</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white px-5 py-2 rounded-lg text-sm font-medium transition"
          >
            {saving ? <FiRefreshCw className="animate-spin" /> : <FiSave />}
            {textoBotaoConnect}
          </button>
        </form>
      );
    }

    if (modalAtivo === "stone-conciliacao") {
      return (
        <div className="space-y-4">
          {conectadoConciliacao ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800 flex gap-2">
              <FiCheckCircle className="shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Conciliação ativa!</p>
                <p className="text-green-700 mt-0.5">
                  Usuário vinculado: <strong>{config.conciliacao_username}</strong>
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800 flex gap-2">
              <FiMail className="shrink-0 mt-0.5" />
              <span>
                Preencha CNPJ e Stone Code para solicitar aprovação por e-mail.
              </span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="stone-documento"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                CNPJ da empresa
              </label>
              <input
                id="stone-documento"
                type="text"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="12.345.678/0001-90"
                value={config.documento}
                onChange={(e) =>
                  setConfig({ ...config, documento: e.target.value })
                }
                disabled={conectadoConciliacao}
              />
            </div>
            <div>
              <label
                htmlFor="stone-affiliation"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Stone Code (afiliação)
              </label>
              <input
                id="stone-affiliation"
                type="text"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="Ex: 128845743"
                value={config.affiliation_code}
                onChange={(e) =>
                  setConfig({ ...config, affiliation_code: e.target.value })
                }
                disabled={conectadoConciliacao}
              />
            </div>
          </div>

          {!conectadoConciliacao && (
            <button
              type="button"
              disabled={solicitando || !config.affiliation_code || !config.documento}
              onClick={solicitarConsentimentoConciliacao}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-200 disabled:text-gray-400 text-white px-5 py-2 rounded-lg text-sm font-medium transition"
            >
              {solicitando ? (
                <>
                  <FiRefreshCw className="animate-spin" /> Solicitando...
                </>
              ) : (
                <>
                  <FiMail /> Solicitar Acesso à Conciliação
                </>
              )}
            </button>
          )}
        </div>
      );
    }

    if (modalAtivo === "sefaz") {
      return <SefazIntegracaoCard modoModal onStatusChange={setSefazStatus} />;
    }

    if (modalAtivo === "bling") {
      return (
        <div className="space-y-4">
          <div className={`rounded-lg border p-4 text-sm ${
            blingStatus.conectado
              ? "bg-green-50 border-green-200 text-green-800"
              : "bg-amber-50 border-amber-200 text-amber-800"
          }`}>
            <p className="font-medium">{blingStatus.conectado ? "Bling conectado" : "Bling precisa de renovação"}</p>
            <p className="mt-1">{blingStatus.detalhe}</p>
            {blingStatus.renovacoes_automaticas > 0 && (
              <p className="mt-1">Renovações automáticas: {blingStatus.renovacoes_automaticas}</p>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={testarConexaoBling}
              disabled={testandoBling}
              className="flex items-center gap-2 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-300 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              {testandoBling ? <FiRefreshCw className="animate-spin" /> : <FiClock />}
              Testar conexão
            </button>

            <button
              type="button"
              onClick={renovarTokenBling}
              disabled={renovandoBling}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              {renovandoBling ? <FiRefreshCw className="animate-spin" /> : <FiRefreshCw />}
              Renovar token
            </button>
          </div>
        </div>
      );
    }

    return null;
  }

  function tituloModal() {
    if (modalAtivo === "stone-connect") return "Configurar Stone Connect";
    if (modalAtivo === "stone-conciliacao") return "Configurar Stone Conciliação";
    if (modalAtivo === "sefaz") return "Configurar SEFAZ";
    if (modalAtivo === "bling") return "Configurar Bling";
    return "Configurar Integração";
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6 relative">
      <div className="absolute -z-10 inset-x-0 top-0 h-40 bg-gradient-to-r from-indigo-50 via-cyan-50 to-emerald-50 rounded-2xl" />

      <div className="bg-white/85 backdrop-blur-sm border border-indigo-100 rounded-2xl px-5 py-4">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <FiGrid className="text-indigo-600" />
          Integrações
        </h1>
        <p className="text-gray-500 mt-1">
          Visualize status rápido e clique para abrir cada configuração em modal.
        </p>
      </div>

      {msg && (
        <div
          className={`flex items-start gap-3 p-4 rounded-lg border ${
            msg.tipo === "sucesso"
              ? "bg-green-50 border-green-200 text-green-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          {msg.tipo === "sucesso" ? (
            <FiCheckCircle className="mt-0.5 shrink-0" />
          ) : (
            <FiXCircle className="mt-0.5 shrink-0" />
          )}
          <span>{msg.texto}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <IntegracaoCard
          icon={FiCreditCard}
          titulo="Stone Connect"
          descricao="Cobrança na maquininha direto no sistema."
          detalhe={conectadoConnect ? "Conta conectada" : "Aguardando chave sk_*"}
          status={conectadoConnect ? "conectado" : "desconectado"}
          acaoTexto={conectadoConnect ? "Editar" : "Configurar"}
          onAcao={() => abrirModal("stone-connect")}
          tema="emerald"
        />

        <IntegracaoCard
          icon={FiMail}
          titulo="Stone Conciliação"
          descricao="Relatórios financeiros automáticos da Stone."
          detalhe={detalheConciliacao}
          status={statusConciliacao}
          acaoTexto={conectadoConciliacao ? "Ver detalhes" : "Configurar"}
          onAcao={() => abrirModal("stone-conciliacao")}
          tema="sky"
        />

        <IntegracaoCard
          icon={FiFileText}
          titulo="SEFAZ NF-e"
          descricao="Certificado A1 e parâmetros de consulta fiscal."
          detalhe={conectadoSefaz ? "Configuração validada" : sefazStatus.mensagem || "Configuração pendente"}
          status={conectadoSefaz ? "conectado" : "desconectado"}
          acaoTexto="Configurar"
          onAcao={() => abrirModal("sefaz")}
          tema="violet"
        />

        <IntegracaoCard
          icon={FiPackage}
          titulo="Bling"
          descricao="Sincronização de estoque e autorização OAuth."
          detalhe={blingStatus.conectado ? (blingStatus.detalhe || "Token ativo") : "Token expirado ou não configurado"}
          status={blingStatus.conectado ? "conectado" : "desconectado"}
          acaoTexto={blingStatus.conectado ? "Ver detalhes" : "Conectar"}
          onAcao={() => abrirModal("bling")}
          tema="sky"
        />
      </div>

      {modalAtivo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="Fechar modal"
            className="absolute inset-0 bg-black/40"
            onClick={fecharModal}
          />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-auto border border-gray-200">
            <div className="sticky top-0 bg-gradient-to-r from-indigo-50 to-cyan-50 border-b px-5 py-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">{tituloModal()}</h2>
              <button
                type="button"
                onClick={fecharModal}
                className="text-gray-500 hover:text-gray-700"
                aria-label="Fechar modal"
              >
                <FiX size={20} />
              </button>
            </div>
            <div className="p-5">{renderModalConteudo()}</div>
          </div>
        </div>
      )}
    </div>
  );
}

IntegracaoCard.propTypes = {
  icon: PropTypes.elementType.isRequired,
  titulo: PropTypes.string.isRequired,
  descricao: PropTypes.string.isRequired,
  detalhe: PropTypes.string,
  status: PropTypes.oneOf(["conectado", "pendente", "desconectado"]).isRequired,
  acaoTexto: PropTypes.string.isRequired,
  onAcao: PropTypes.func.isRequired,
  tema: PropTypes.oneOf(["emerald", "sky", "violet"]),
};

function IntegracaoCard({
  icon: Icon,
  titulo,
  descricao,
  detalhe = "",
  status,
  acaoTexto,
  onAcao,
  tema = "sky",
}) {
  const temaStyles = {
    emerald: {
      card: "hover:border-emerald-300",
      icon: "bg-emerald-50 text-emerald-600",
      botao: "text-emerald-700 bg-emerald-50 hover:bg-emerald-100",
    },
    sky: {
      card: "hover:border-sky-300",
      icon: "bg-sky-50 text-sky-600",
      botao: "text-sky-700 bg-sky-50 hover:bg-sky-100",
    },
    violet: {
      card: "hover:border-violet-300",
      icon: "bg-violet-50 text-violet-600",
      botao: "text-violet-700 bg-violet-50 hover:bg-violet-100",
    },
  };

  const estilo = temaStyles[tema] || temaStyles.sky;

  return (
    <div className={`h-full border rounded-xl p-4 bg-white flex flex-col gap-4 transition ${estilo.card}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${estilo.icon}`}>
            <Icon size={18} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-800 leading-tight">{titulo}</h3>
            <p className="text-xs text-gray-500 mt-1">{descricao}</p>
          </div>
        </div>
        <StatusBadge
          ativo={status === "conectado"}
          pendente={status === "pendente"}
        />
      </div>

      <p className="text-xs text-gray-500 min-h-10">{detalhe}</p>

      <button
        type="button"
        onClick={onAcao}
        className={`self-start mt-auto text-sm font-medium px-3 py-1.5 rounded-lg transition ${estilo.botao}`}
      >
        {acaoTexto}
      </button>
    </div>
  );
}

StatusBadge.propTypes = {
  ativo: PropTypes.bool.isRequired,
  pendente: PropTypes.bool,
};

function StatusBadge({ ativo, pendente = false }) {
  if (ativo) {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2.5 py-1 rounded-full">
        <FiCheckCircle size={12} /> Conectado
      </span>
    );
  }
  if (pendente) {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-100 px-2.5 py-1 rounded-full">
        <FiClock size={12} /> Aguardando aprovação
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-xs font-medium text-gray-500 bg-gray-100 px-2.5 py-1 rounded-full">
      <FiXCircle size={12} /> Não conectado
    </span>
  );
}
