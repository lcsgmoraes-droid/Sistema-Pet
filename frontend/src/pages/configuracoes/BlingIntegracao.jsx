import { useEffect, useState } from "react";
import {
  FiAlertCircle,
  FiCheckCircle,
  FiRefreshCw,
  FiClock,
  FiLock,
  FiLink2,
} from "react-icons/fi";
import { api } from "../../services/api";

/**
 * Página de configuração e renovação da integração Bling v3.
 *
 * Funcionalidades:
 * - Renovar access token usando refresh token
 * - Status da conexão com a API
 * - Link para autorização OAuth
 * - Informações sobre a próxima renovação automática
 */
export default function BlingIntegracao() {
  const [loading, setLoading] = useState(true);
  const [renovando, setRenovando] = useState(false);
  const [msg, setMsg] = useState(null); // { tipo: 'sucesso'|'erro'|'info', texto: '' }
  const [status, setStatus] = useState({
    conectado: false,
    ultima_renovacao: null,
    proxima_renovacao: null,
    renovacoes_automaticas: 0,
    temp_acesso_horas: 0,
    total_produtos_bling: 0,
  });

  useEffect(() => {
    carregarStatus();
  }, []);

  async function carregarStatus() {
    try {
      setLoading(true);
      const resp = await api.get("/bling/teste-conexao");
      setStatus(resp.data);
    } catch (e) {
      // Conexão falhada é normal se token expirou
      setStatus({
        conectado: false,
        ultima_renovacao: null,
        proxima_renovacao: null,
        renovacoes_automaticas: 0,
        temp_acesso_horas: 0,
        total_produtos_bling: 0,
      });
    } finally {
      setLoading(false);
    }
  }

  function mostrarMensagem(tipo, texto) {
    setMsg({ tipo, texto });
    setTimeout(() => setMsg(null), 6000);
  }

  async function renovarToken() {
    setRenovando(true);
    try {
      const resp = await api.post("/bling/renovar-token");
      mostrarMensagem(
        "sucesso",
        `✅ Token renovado! Válido por ${resp.data.expires_in_hours?.toFixed(1) || 6} horas.`
      );
      setTimeout(() => carregarStatus(), 1000);
    } catch (e) {
      // Se o refresh token expirou, redireciona para autorização OAuth
      const detail = e.response?.data?.detail || "";
      const isInvalidGrant =
        detail.includes("invalid_grant") ||
        detail.includes("Invalid refresh token") ||
        e.response?.status === 400;

      if (isInvalidGrant) {
        mostrarMensagem("info", "⏳ Abrindo autorização no Bling...");
        try {
          window.location.assign("/api/auth/bling/link-autorizacao?redirect=1");
          return;
        } catch {
          // fallback abaixo
        }
      }

      const erro = detail || e.message || "Erro ao renovar token";
      mostrarMensagem("erro", `❌ ${erro}`);
    } finally {
      setRenovando(false);
    }
  }

  async function testarConexao() {
    try {
      setLoading(true);
      await carregarStatus();
      if (status.conectado) {
        mostrarMensagem(
          "sucesso",
          `✅ Conectado! ${status.total_produtos_bling || 0} produtos no Bling.`
        );
      } else {
        mostrarMensagem(
          "info",
          "⚠️ Token expirado. Use o botão 'Renovar Token' abaixo."
        );
      }
    } catch (e) {
      mostrarMensagem("erro", "Erro ao testar conexão.");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <FiRefreshCw className="animate-spin mr-2" /> Carregando...
      </div>
    );
  }

  const statusClasse = status.conectado
    ? "bg-emerald-50 border-emerald-200"
    : "bg-red-50 border-red-200";

  const statusTexto = status.conectado
    ? "✅ Conectado"
    : "❌ Token Expirado";

  const statusCor = status.conectado ? "text-emerald-700" : "text-red-700";

  return (
    <div className="container mx-auto px-4 py-6 max-w-2xl">
      {/* Mensagens */}
      {msg && (
        <div
          className={`mb-4 p-4 rounded-lg flex gap-2 animate-in fade-in ${
            msg.tipo === "sucesso"
              ? "bg-emerald-100 border border-emerald-300 text-emerald-800"
              : msg.tipo === "erro"
                ? "bg-red-100 border border-red-300 text-red-800"
                : "bg-blue-100 border border-blue-300 text-blue-800"
          }`}
        >
          <div className="shrink-0 mt-0.5">
            {msg.tipo === "sucesso" ? (
              <FiCheckCircle className="w-5 h-5" />
            ) : msg.tipo === "erro" ? (
              <FiAlertCircle className="w-5 h-5" />
            ) : (
              <FiClock className="w-5 h-5" />
            )}
          </div>
          <div className="flex-1">{msg.texto}</div>
        </div>
      )}

      {/* Card Principal - Status da Integração */}
      <div
        className={`border rounded-lg p-6 mb-6 transition-colors ${statusClasse}`}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Integração Bling v3
            </h2>
            <p className={`text-sm font-medium mt-1 ${statusCor}`}>
              {statusTexto}
            </p>
          </div>
          <div className={`p-2 rounded-full ${
            status.conectado
              ? "bg-emerald-200/50 text-emerald-600"
              : "bg-red-200/50 text-red-600"
          }`}>
            {status.conectado ? (
              <FiCheckCircle className="w-6 h-6" />
            ) : (
              <FiAlertCircle className="w-6 h-6" />
            )}
          </div>
        </div>

        {/* Informações de Status */}
        <div className="space-y-2 text-sm mb-4">
          {status.conectado && (
            <>
              <p className="flex justify-between">
                <span className="text-gray-600">Produtos carregados:</span>
                <span className="font-mono font-medium text-gray-900">
                  {status.total_produtos_bling || 0}
                </span>
              </p>
              <p className="flex justify-between">
                <span className="text-gray-600">Renovações automáticas:</span>
                <span className="font-mono font-medium text-gray-900">
                  {status.renovacoes_automaticas || 0}
                </span>
              </p>
              <p className="flex justify-between">
                <span className="text-gray-600">Próxima renovação:</span>
                <span className="font-mono font-medium text-gray-900">
                  {status.proxima_renovacao
                    ? new Date(status.proxima_renovacao).toLocaleString("pt-BR")
                    : "—"}
                </span>
              </p>
            </>
          )}
          {!status.conectado && (
            <p className="text-gray-700">
              O token expirou ou é inválido. Clique em "Renovar Token" abaixo
              para reconectar.
            </p>
          )}
        </div>
      </div>

      {/* Botões de Ação */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <button
          onClick={renovarToken}
          disabled={renovando}
          className="px-4 py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-all
            bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
            text-white shadow-sm hover:shadow-md"
        >
          <FiRefreshCw className={renovando ? "animate-spin" : ""} />
          {renovando ? "Renovando..." : "Renovar Token"}
        </button>

        <button
          onClick={testarConexao}
          disabled={loading}
          className="px-4 py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-all
            bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed
            text-gray-900"
        >
          <FiLock className="w-4 h-4" />
          {loading ? "Testando..." : "Testar Conexão"}
        </button>
      </div>

      {/* Informações de Configuração */}
      <div className="bg-gray-50 rounded-lg p-6 space-y-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <FiLink2 className="w-5 h-5" />
          Configuração
        </h3>

        <div className="space-y-3 text-sm">
          <p className="text-gray-700">
            <strong>Status:</strong> {status.conectado ? "✅ Online" : "❌ Offline"}
          </p>

          <p className="text-gray-700">
            <strong>Renovação automática:</strong> O sistema renova o token
            automaticamente a cada 5h30min. Você não precisa fazer nada.
          </p>

          {!status.conectado && (
            <div className="bg-amber-50 border border-amber-200 rounded p-3 text-amber-800">
              <p className="font-medium mb-2">Se o botão acima não funcionar:</p>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Acesse o painel do Bling (bling.com.br)</li>
                <li>Vá em Integrações → Aplicações</li>
                <li>Encontre "Sistema Pet" e autorize novamente</li>
                <li>Copie o código gerado</li>
                <li>Contacte o suporte com esse código</li>
              </ol>
            </div>
          )}

          <p className="text-gray-600 text-xs mt-4">
            💡 <strong>Dica:</strong> Mantenha a integração conectada para que
            o estoque sincronize automaticamente com o Bling.
          </p>
        </div>
      </div>
    </div>
  );
}
