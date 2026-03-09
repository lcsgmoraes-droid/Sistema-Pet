import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { formatMoneyBRL } from "../utils/formatters";

function formatarChave(valor) {
  return valor.replaceAll(/\D/g, "").slice(0, 44);
}

function tratarColagemChave(event, setChave) {
  event.preventDefault();
  const texto = event.clipboardData?.getData("text") || "";
  setChave(formatarChave(texto));
}

function formatarMoeda(valor) {
  if (valor === null || valor === undefined) return "-";
  return formatMoneyBRL(valor);
}

function formatarDataHora(valor) {
  if (!valor) return "-";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "-";
  return data.toLocaleString("pt-BR");
}

export default function SEFAZImportacao() {
  const [chave, setChave] = useState("");
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(true);
  const [salvandoRotina, setSalvandoRotina] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [mensagemRotina, setMensagemRotina] = useState("");
  const [cfg, setCfg] = useState({
    enabled: false,
    modo: "mock",
    ambiente: "homologacao",
    uf: "SP",
    cnpj: "",
    importacao_automatica: false,
    importacao_intervalo_min: 15,
    cert_ok: false,
    ultimo_sync_status: "nunca",
    ultimo_sync_mensagem: "Ainda nao sincronizado.",
    ultimo_sync_at: null,
    ultimo_sync_documentos: 0,
  });

  useEffect(() => {
    carregarConfigOperacional();
  }, []);

  async function carregarConfigOperacional() {
    try {
      setConfigLoading(true);
      const { data } = await api.get("/sefaz/config");
      setCfg((prev) => ({
        ...prev,
        enabled: Boolean(data.enabled),
        modo: data.modo || "mock",
        ambiente: data.ambiente || "homologacao",
        uf: data.uf || "SP",
        cnpj: data.cnpj || "",
        importacao_automatica: Boolean(data.importacao_automatica),
        importacao_intervalo_min: Number(data.importacao_intervalo_min || 15),
        cert_ok: Boolean(data.cert_ok),
        ultimo_sync_status: data.ultimo_sync_status || "nunca",
        ultimo_sync_mensagem: data.ultimo_sync_mensagem || "Ainda nao sincronizado.",
        ultimo_sync_at: data.ultimo_sync_at || null,
        ultimo_sync_documentos: Number(data.ultimo_sync_documentos || 0),
      }));
    } catch (err) {
      setMensagemRotina(err?.response?.data?.detail || "Nao foi possivel carregar a rotina da SEFAZ.");
    } finally {
      setConfigLoading(false);
    }
  }

  async function salvarRotina() {
    setMensagemRotina("");
    try {
      setSalvandoRotina(true);
      await api.post("/sefaz/config", {
        enabled: cfg.enabled,
        modo: cfg.modo,
        ambiente: cfg.ambiente,
        uf: cfg.uf,
        cnpj: cfg.cnpj,
        importacao_automatica: cfg.importacao_automatica,
        importacao_intervalo_min: Number(cfg.importacao_intervalo_min || 15),
      });
      setMensagemRotina("Rotina automatica salva com sucesso.");
      await carregarConfigOperacional();
    } catch (err) {
      setMensagemRotina(err?.response?.data?.detail || "Erro ao salvar rotina automatica.");
    } finally {
      setSalvandoRotina(false);
    }
  }

  async function sincronizarAgora() {
    setMensagemRotina("");
    try {
      setSincronizando(true);
      const { data } = await api.post("/sefaz/sync-now");
      setMensagemRotina(data?.mensagem || "Sincronizacao solicitada.");
      await carregarConfigOperacional();
    } catch (err) {
      setMensagemRotina(err?.response?.data?.detail || "Erro ao sincronizar agora.");
    } finally {
      setSincronizando(false);
    }
  }

  function atualizarRotina(campo, valor) {
    setCfg((prev) => ({ ...prev, [campo]: valor }));
  }

  async function consultar(e) {
    e.preventDefault();
    setErro("");
    setResultado(null);

    if (chave.length !== 44) {
      setErro("A chave de acesso deve ter exatamente 44 digitos.");
      return;
    }

    try {
      setLoading(true);
      const resp = await api.post("/sefaz/consultar", { chave_acesso: chave });
      setResultado(resp.data);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erro ao consultar a SEFAZ.";
      setErro(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Consulta NF-e - SEFAZ</h1>
        <p className="text-gray-500 text-sm mt-1">
          Esta tela e para operacao. A configuracao da integracao (certificado, senha e ambiente)
          fica em <Link to="/configuracoes/integracoes" className="text-indigo-600 font-semibold"> Configuracoes - Integracoes</Link>.
        </p>
      </div>

      <form onSubmit={consultar} className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <label htmlFor="sefaz-chave" className="block text-sm font-semibold text-gray-700 mb-2">
          Chave de Acesso (44 digitos)
        </label>
        <div className="flex gap-3">
          <input
            id="sefaz-chave"
            type="text"
            value={chave}
            onChange={(e) => setChave(formatarChave(e.target.value))}
            onPaste={(e) => tratarColagemChave(e, setChave)}
            placeholder="Ex: 35250112345678000195550010000001231234567890"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            maxLength={80}
          />
          <button
            type="submit"
            disabled={loading || chave.length !== 44}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Consultando..." : "Consultar"}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">{chave.length}/44 digitos preenchidos</p>

        {erro && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {erro}
          </div>
        )}
      </form>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 space-y-4">
        <div>
          <h2 className="text-lg font-bold text-gray-800">Rotina Automatica SEFAZ</h2>
          <p className="text-sm text-gray-500 mt-1">
            Esta e a parte do dia a dia: autorizar, sincronizar e importar de forma continua.
          </p>
        </div>

        {configLoading ? (
          <p className="text-sm text-gray-500">Carregando configuracao da rotina...</p>
        ) : (
          <>
            {!cfg.enabled || !cfg.cert_ok ? (
              <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm">
                A integracao ainda nao esta pronta para rotina automatica. Finalize em Configuracoes &gt; Integracoes.
              </div>
            ) : null}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={cfg.importacao_automatica}
                  onChange={(e) => atualizarRotina("importacao_automatica", e.target.checked)}
                />
                <span>Ativar importacao automatica</span>
              </label>

              <div>
                <label htmlFor="intervalo-importacao" className="block text-sm font-medium text-gray-700 mb-1">
                  Intervalo (minutos)
                </label>
                <input
                  id="intervalo-importacao"
                  type="number"
                  min={5}
                  step={1}
                  value={cfg.importacao_intervalo_min}
                  onChange={(e) => atualizarRotina("importacao_intervalo_min", Number(e.target.value || 15))}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-lg p-3">
              <div>
                Ultima sincronizacao: <strong>{formatarDataHora(cfg.ultimo_sync_at)}</strong>
              </div>
              <div>
                Status: <strong>{cfg.ultimo_sync_status}</strong>
              </div>
              <div>
                Documentos trazidos: <strong>{cfg.ultimo_sync_documentos}</strong>
              </div>
              <div>
                Modo atual: <strong>{cfg.modo}</strong>
              </div>
              <div className="sm:col-span-2">
                Mensagem: <strong>{cfg.ultimo_sync_mensagem}</strong>
              </div>
            </div>

            {mensagemRotina && (
              <div className="text-sm bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-700">
                {mensagemRotina}
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={salvarRotina}
                disabled={salvandoRotina}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60"
              >
                {salvandoRotina ? "Salvando rotina..." : "Salvar rotina"}
              </button>

              <button
                type="button"
                onClick={sincronizarAgora}
                disabled={sincronizando}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 disabled:opacity-60"
              >
                {sincronizando ? "Sincronizando..." : "Sincronizar agora"}
              </button>
            </div>
          </>
        )}
      </div>

      {resultado && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {resultado.aviso && (
            <div className="bg-yellow-50 px-6 py-3 text-xs text-yellow-700 border-b border-yellow-200">
              {resultado.aviso}
            </div>
          )}

          <div className="p-6 border-b border-gray-100">
            <h2 className="text-lg font-bold text-gray-800 mb-4">Dados da Nota Fiscal</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Numero / Serie:</span>
                <span className="ml-2 font-semibold">{resultado.numero_nf} / {resultado.serie}</span>
              </div>
              <div>
                <span className="text-gray-500">Emissao:</span>
                <span className="ml-2 font-semibold">{resultado.data_emissao}</span>
              </div>
              <div>
                <span className="text-gray-500">Emitente:</span>
                <span className="ml-2 font-semibold">{resultado.emitente_nome}</span>
              </div>
              <div>
                <span className="text-gray-500">CNPJ Emitente:</span>
                <span className="ml-2 font-semibold">{resultado.emitente_cnpj}</span>
              </div>
              <div>
                <span className="text-gray-500">Destinatario:</span>
                <span className="ml-2 font-semibold">{resultado.destinatario_nome || "-"}</span>
              </div>
              <div>
                <span className="text-gray-500">Valor Total:</span>
                <span className="ml-2 font-bold text-green-700 text-base">{formatarMoeda(resultado.valor_total_nf)}</span>
              </div>
            </div>
          </div>

          <div className="p-6">
            <h3 className="text-sm font-bold text-gray-700 mb-3">Itens da Nota ({resultado.itens?.length})</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-gray-600 text-xs uppercase">
                    <th className="text-left px-3 py-2">#</th>
                    <th className="text-left px-3 py-2">Codigo</th>
                    <th className="text-left px-3 py-2">Descricao</th>
                    <th className="text-left px-3 py-2">NCM</th>
                    <th className="text-right px-3 py-2">Qtd</th>
                    <th className="text-left px-3 py-2">UN</th>
                    <th className="text-right px-3 py-2">Unit.</th>
                    <th className="text-right px-3 py-2">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {resultado.itens?.map((item) => (
                    <tr key={item.numero_item} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-gray-500">{item.numero_item}</td>
                      <td className="px-3 py-2 font-mono text-xs">{item.codigo_produto}</td>
                      <td className="px-3 py-2">{item.descricao}</td>
                      <td className="px-3 py-2 font-mono text-xs text-gray-500">{item.ncm || "-"}</td>
                      <td className="px-3 py-2 text-right">{item.quantidade}</td>
                      <td className="px-3 py-2 text-gray-500">{item.unidade}</td>
                      <td className="px-3 py-2 text-right">{formatarMoeda(item.valor_unitario)}</td>
                      <td className="px-3 py-2 text-right font-semibold">{formatarMoeda(item.valor_total)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-gray-300 bg-gray-50">
                    <td colSpan={7} className="px-3 py-2 text-right font-bold text-gray-700">Total da NF-e</td>
                    <td className="px-3 py-2 text-right font-bold text-green-700">{formatarMoeda(resultado.valor_total_nf)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
