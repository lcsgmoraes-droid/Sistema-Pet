import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import {
  FiAlertCircle,
  FiCheckCircle,
  FiClock,
  FiCreditCard,
  FiEye,
  FiEyeOff,
  FiMail,
  FiRefreshCw,
  FiSave,
  FiXCircle,
} from "react-icons/fi";
import { api } from "../../services/api";

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
  const [msg, setMsg] = useState(null); // { tipo: 'sucesso'|'erro', texto: '' }

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

  async function carregarConfig() {
    try {
      const { data } = await api.get("/stone/config");
      setConfig((prev) => ({
        ...prev,
        ...data,
        webhook_url: data.webhook_url || webhookUrlPadrao,
      }));
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

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <FiCreditCard className="text-green-600" />
          Integrações
        </h1>
        <p className="text-gray-500 mt-1">
          Configure as integrações do sistema com serviços externos.
        </p>
      </div>

      {/* Mensagem de retorno */}
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

      {/* ── MÓDULO 1: Stone Connect ─────────────────── */}
      <section className="border rounded-xl overflow-hidden">
        <div className="bg-gray-50 border-b px-5 py-4 flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-gray-800">
              Stone Connect — Maquininha
            </h2>
            <p className="text-sm text-gray-500">
              Permite cobrar diretamente na maquininha a partir do sistema.
            </p>
          </div>
          <StatusBadge ativo={conectadoConnect} />
        </div>

        <form onSubmit={salvarConfiguracaoConnect} className="p-5 space-y-4">
          {/* Instrução de como obter a chave */}
          {!conectadoConnect && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800 flex gap-2">
              <FiAlertCircle className="shrink-0 mt-0.5" />
              <span>
                Para obter sua chave, acesse{" "}
                <strong>id.pagar.me → Empresas → sua empresa → API Keys</strong>{" "}
                e copie a chave que começa com <strong>sk_</strong>. Caso sua
                empresa não apareça, entre em contato com a Stone pelo chat e
                peça acesso ao Pagar.me Connect.
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
                autoComplete="new-password"
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
            <p className="text-xs text-gray-400 mt-1">
              Nunca compartilhe esta chave. Ela dá acesso à sua conta Pagar.me.
            </p>
          </div>

          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.enable_pix}
                onChange={(e) =>
                  setConfig({ ...config, enable_pix: e.target.checked })
                }
              />{" "}
              Aceitar PIX
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.enable_credit_card}
                onChange={(e) =>
                  setConfig({ ...config, enable_credit_card: e.target.checked })
                }
              />{" "}
              Aceitar Crédito
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.enable_debit_card}
                onChange={(e) =>
                  setConfig({ ...config, enable_debit_card: e.target.checked })
                }
              />{" "}
              Aceitar Débito
            </label>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white px-5 py-2 rounded-lg text-sm font-medium transition"
          >
            {saving ? <FiRefreshCw className="animate-spin" /> : <FiSave />}
            {(() => {
              if (saving) return "Salvando...";
              return conectadoConnect ? "Atualizar Chave" : "Ativar Connect";
            })()}
          </button>
        </form>
      </section>

      {/* ── MÓDULO 2: Stone Conciliação ─────────────── */}
      <section className="border rounded-xl overflow-hidden">
        <div className="bg-gray-50 border-b px-5 py-4 flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-gray-800">
              Stone Conciliação — Relatório Automático
            </h2>
            <p className="text-sm text-gray-500">
              Baixa automaticamente o relatório financeiro da Stone todos os
              dias.
            </p>
          </div>
          <StatusBadge
            ativo={conectadoConciliacao}
            pendente={!conectadoConciliacao && !!config.affiliation_code}
          />
        </div>

        <div className="p-5 space-y-4">
          {/* Status da conciliação */}
          {conectadoConciliacao ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800 flex gap-2">
              <FiCheckCircle className="shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Conciliação ativa!</p>
                <p className="text-green-700 mt-0.5">
                  Usuário vinculado:{" "}
                  <strong>{config.conciliacao_username}</strong>
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800 flex gap-2">
              <FiMail className="shrink-0 mt-0.5" />
              <span>
                Preencha o <strong>CNPJ</strong> e o <strong>Stone Code</strong>{" "}
                e clique em <strong>Solicitar Acesso</strong>. A Stone enviará
                um e-mail para o responsável pelo CNPJ.{" "}
                <strong>Após aprovar no e-mail</strong>, a integração ativa
                automaticamente aqui.
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
                Stone Code (código de afiliação)
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
              <p className="text-xs text-gray-400 mt-1">
                Encontrado no portal Stone → Meu negócio → Dados da empresa
              </p>
            </div>
          </div>

          {/* URL do webhook (oculta por padrão, só para referência) */}
          <details className="text-xs text-gray-400">
            <summary className="cursor-pointer hover:text-gray-600">
              Ver URL do webhook (avançado)
            </summary>
            <p className="mt-2 break-all font-mono bg-gray-100 p-2 rounded">
              {config.webhook_url || webhookUrlPadrao}
            </p>
          </details>

          {!conectadoConciliacao && (
            <button
              type="button"
              disabled={
                solicitando || !config.affiliation_code || !config.documento
              }
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

          {/* Instrução pós-solicitação */}
          {!conectadoConciliacao && config.affiliation_code && (
            <div className="flex items-start gap-2 text-sm text-gray-500">
              <FiClock className="shrink-0 mt-0.5" />
              <span>
                Após solicitar, o responsável pelo CNPJ receberá um e-mail da
                Stone para aprovar. Assim que aprovado, o sistema ativa
                automaticamente — sem precisar fazer nada aqui.
              </span>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

StatusBadge.propTypes = {
  ativo: PropTypes.bool.isRequired,
  pendente: PropTypes.bool.isRequired,
};

function StatusBadge({ ativo, pendente }) {
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
