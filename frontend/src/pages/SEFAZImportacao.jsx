import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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

function montarNomeArquivoXml(dados) {
  const numero = String(dados?.numero_nf || "sem-numero").replaceAll(/\D/g, "");
  const serie = String(dados?.serie || "1").replaceAll(/\D/g, "");
  const chaveAcesso = String(dados?.chave_acesso || "").replaceAll(/\D/g, "").slice(-8);
  return `nfe_${numero || "0"}_${serie || "1"}_${chaveAcesso || "xml"}.xml`;
}

function somenteDigitos(valor) {
  return String(valor || "").replaceAll(/\D/g, "");
}

export default function SEFAZImportacao() {
  const navigate = useNavigate();
  const [chave, setChave] = useState("");
  const [importacoes, setImportacoes] = useState([]);
  const [importacaoExpandidaId, setImportacaoExpandidaId] = useState(null);
  const [importandoEntradaId, setImportandoEntradaId] = useState(null);
  const [resultadoEntradaPorId, setResultadoEntradaPorId] = useState({});
  const [erro, setErro] = useState("");
  const [avisoConector, setAvisoConector] = useState("");
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(true);
  const [salvandoRotina, setSalvandoRotina] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [pulandoParaHoje, setPulandoParaHoje] = useState(false);
  const [mensagemRotina, setMensagemRotina] = useState("");
  const listaImportacoesRef = useRef(null);
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
    proximo_sync_permitido_at: null,
  });

  const emCooldown = (() => {
    if (!cfg.proximo_sync_permitido_at) return false;
    return new Date(cfg.proximo_sync_permitido_at) > new Date();
  })();

  const minutosRestantesCooldown = (() => {
    if (!cfg.proximo_sync_permitido_at) return 0;
    const diff = new Date(cfg.proximo_sync_permitido_at) - new Date();
    if (diff <= 0) return 0;
    return Math.ceil(diff / 60000);
  })();

  useEffect(() => {
    carregarConfigOperacional();
  }, []);

  useEffect(() => {
    if (!importacoes.length || !listaImportacoesRef.current) return;
    listaImportacoesRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [importacoes.length]);

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
        proximo_sync_permitido_at: data.proximo_sync_permitido_at || null,
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

  async function pularParaHoje() {
    const confirmado = window.confirm(
      "Isso vai fazer o sistema IGNORAR todas as NFs antigas e começar pelo ponto atual da SEFAZ.\n\nAs NFs antigas NÃO serão importadas. Continuar?"
    );
    if (!confirmado) return;
    setMensagemRotina("");
    try {
      setPulandoParaHoje(true);
      const { data } = await api.post("/sefaz/pular-para-hoje");
      setMensagemRotina(data?.mensagem || "Configurado para começar do ponto atual.");
      await carregarConfigOperacional();
    } catch (err) {
      setMensagemRotina(err?.response?.data?.detail || "Erro ao configurar pulo para hoje.");
    } finally {
      setPulandoParaHoje(false);
    }
  }

  function atualizarRotina(campo, valor) {
    setCfg((prev) => ({ ...prev, [campo]: valor }));
  }

  function abrirEntradaXmlNovaGuia(notaId) {
    const alvo = notaId ? `/compras/entrada-xml?nota_id=${notaId}` : "/compras/entrada-xml";
    const novaGuia = globalThis.open(alvo, "_blank", "noopener,noreferrer");
    if (!novaGuia) {
      navigate(alvo);
    }
  }

  async function importarNaEntradaXML(importacao) {
    const xmlNfe = importacao?.dados?.xml_nfe;
    if (!xmlNfe) {
      setResultadoEntradaPorId((prev) => ({
        ...prev,
        [importacao.id]: {
          tipo: "erro",
          mensagem: "Esta consulta nao trouxe XML completo da NF-e. Tente outra chave ou rode sincronizacao real.",
        },
      }));
      return;
    }

    try {
      setImportandoEntradaId(importacao.id);
      setResultadoEntradaPorId((prev) => ({ ...prev, [importacao.id]: null }));

      const fileName = montarNomeArquivoXml(importacao.dados);
      const blob = new Blob([xmlNfe], { type: "application/xml;charset=utf-8" });
      const file = new File([blob], fileName, { type: "text/xml" });
      const formData = new FormData();
      formData.append("file", file);

      const { data } = await api.post("/notas-entrada/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      const notaIdCriada = data?.nota_id;
      if (notaIdCriada) {
        abrirEntradaXmlNovaGuia(notaIdCriada);
        return;
      }

      setResultadoEntradaPorId((prev) => ({
        ...prev,
        [importacao.id]: {
          tipo: "ok",
          mensagem: `Entrada criada com sucesso (Nota ID ${data?.nota_id || "-"}).`,
        },
      }));
    } catch (err) {
      const msg = err?.response?.data?.detail || "Falha ao enviar XML para Entrada por XML.";
      setResultadoEntradaPorId((prev) => ({
        ...prev,
        [importacao.id]: {
          tipo: "erro",
          mensagem: msg,
        },
      }));
    } finally {
      setImportandoEntradaId(null);
    }
  }

  async function consultar(e) {
    e.preventDefault();
    setErro("");
    setAvisoConector("");

    if (chave.length !== 44) {
      setErro("A chave de acesso deve ter exatamente 44 digitos.");
      return;
    }

    try {
      setLoading(true);
      const resp = await api.post("/sefaz/consultar", { chave_acesso: chave });

      const caminhoAtual = globalThis.location?.pathname || "";
      const telaEntrada = caminhoAtual.includes("/notas-fiscais/entrada");
      const telaSaida = caminhoAtual.includes("/notas-fiscais/saida");

      const cnpjEmpresa = somenteDigitos(cfg.cnpj);
      const cnpjEmitente = somenteDigitos(resp.data.emitente_cnpj);
      const cnpjDestinatario = somenteDigitos(resp.data.destinatario_cnpj);

      if (cnpjEmpresa && telaEntrada && cnpjEmitente && cnpjEmitente === cnpjEmpresa) {
        setErro("Esta chave parece ser NF de saida da propria empresa. Use a tela NF de Saida.");
        return;
      }

      if (cnpjEmpresa && telaSaida && cnpjDestinatario && cnpjDestinatario === cnpjEmpresa) {
        setErro("Esta chave parece ser NF de entrada para a propria empresa. Use a tela NF de Entrada.");
        return;
      }

      const novaImportacao = {
        id: `${Date.now()}-${resp.data.chave_acesso}`,
        criadoEm: new Date().toISOString(),
        dados: resp.data,
      };
      setImportacoes((prev) => [novaImportacao, ...prev]);
      setImportacaoExpandidaId(null);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erro ao consultar a SEFAZ.";
      const status = Number(err?.response?.status || 0);
      const ehEtapaConector = status === 501 && msg.toLowerCase().includes("conector");

      if (ehEtapaConector) {
        setAvisoConector(msg);
      } else {
        setErro(msg);
      }
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

        {avisoConector && (
          <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
            <strong>Integracao validada, etapa final pendente:</strong> {avisoConector}
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

            {emCooldown && (
              <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-red-800 text-sm">
                ⛔ <strong>SEFAZ bloqueada por consumo indevido (código 656).</strong> O sistema fez chamadas demais e a SEFAZ aplicou uma penalidade. O botão ficará disponível em <strong>~{minutosRestantesCooldown} minuto(s)</strong>. Não tente forçar — isso reinicia o contador de penalidade.
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
                disabled={sincronizando || emCooldown}
                title={emCooldown ? `Aguarde ${minutosRestantesCooldown} min antes de tentar novamente (cooldown SEFAZ 656)` : ""}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {sincronizando ? "Sincronizando..." : emCooldown ? `⏳ Aguarde ~${minutosRestantesCooldown} min` : "Sincronizar agora"}
              </button>

              <button
                type="button"
                onClick={pularParaHoje}
                disabled={pulandoParaHoje}
                title="Ignora todas as NFs antigas e começa do ponto atual da SEFAZ. Use quando o sistema estiver muito atrasado e causando bloqueios."
                className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-semibold hover:bg-amber-700 disabled:opacity-60"
              >
                {pulandoParaHoje ? "Configurando..." : "🚀 Ignorar NFs antigas"}
              </button>
            </div>
          </>
        )}
      </div>

      {importacoes.length > 0 && (
        <div ref={listaImportacoesRef} className="space-y-3">
          <h2 className="text-base font-bold text-gray-800">Importacoes da sessao ({importacoes.length})</h2>

          {importacoes.map((imp) => {
            const expandida = importacaoExpandidaId === imp.id;
            const dados = imp.dados;

            return (
              <div key={imp.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setImportacaoExpandidaId(expandida ? null : imp.id)}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-gray-800">
                      NF {dados.numero_nf}/{dados.serie} - {dados.emitente_nome}
                    </div>
                    <div className="text-xs text-gray-500">{formatarDataHora(imp.criadoEm)}</div>
                  </div>

                  <div className="mt-2 grid grid-cols-1 sm:grid-cols-4 gap-2 text-xs">
                    <div className="text-gray-600">Chave: <span className="font-mono">{dados.chave_acesso}</span></div>
                    <div className="text-gray-600">Itens: <strong>{dados.itens?.length || 0}</strong></div>
                    <div className="text-gray-600">Total: <strong className="text-green-700">{formatarMoeda(dados.valor_total_nf)}</strong></div>
                    <div className="text-indigo-700 font-semibold">{expandida ? "Fechar" : "Expandir"}</div>
                  </div>
                </button>

                <div className="px-4 py-3 border-t border-gray-100 bg-gray-50">
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => importarNaEntradaXML(imp)}
                      disabled={importandoEntradaId === imp.id}
                      className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 disabled:opacity-60"
                    >
                      {importandoEntradaId === imp.id ? "Enviando para Entrada por XML..." : "Usar esta NF na Entrada por XML"}
                    </button>

                    <button
                      type="button"
                      onClick={() => abrirEntradaXmlNovaGuia()}
                      className="px-3 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700"
                    >
                      Abrir Entrada por XML em nova guia
                    </button>
                  </div>

                  {resultadoEntradaPorId[imp.id]?.mensagem && (
                    <div
                      className={`mt-2 text-xs rounded-lg px-3 py-2 ${
                        resultadoEntradaPorId[imp.id]?.tipo === "ok"
                          ? "bg-emerald-50 border border-emerald-200 text-emerald-700"
                          : "bg-red-50 border border-red-200 text-red-700"
                      }`}
                    >
                      {resultadoEntradaPorId[imp.id]?.mensagem}
                    </div>
                  )}
                </div>

                {expandida && (
                  <>
                    {dados.aviso && (
                      <div className="bg-yellow-50 px-6 py-3 text-xs text-yellow-700 border-t border-b border-yellow-200">
                        {dados.aviso}
                      </div>
                    )}

                    <div className="p-6 border-b border-gray-100">
                      <h3 className="text-lg font-bold text-gray-800 mb-4">Dados da Nota Fiscal</h3>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">Numero / Serie:</span>
                          <span className="ml-2 font-semibold">{dados.numero_nf} / {dados.serie}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Emissao:</span>
                          <span className="ml-2 font-semibold">{dados.data_emissao}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Emitente:</span>
                          <span className="ml-2 font-semibold">{dados.emitente_nome}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">CNPJ Emitente:</span>
                          <span className="ml-2 font-semibold">{dados.emitente_cnpj}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Destinatario:</span>
                          <span className="ml-2 font-semibold">{dados.destinatario_nome || "-"}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Valor Total:</span>
                          <span className="ml-2 font-bold text-green-700 text-base">{formatarMoeda(dados.valor_total_nf)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="p-6">
                      <h4 className="text-sm font-bold text-gray-700 mb-3">Itens da Nota ({dados.itens?.length || 0})</h4>
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
                            {dados.itens?.map((item) => (
                              <tr key={`${imp.id}-${item.numero_item}`} className="hover:bg-gray-50">
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
                              <td className="px-3 py-2 text-right font-bold text-green-700">{formatarMoeda(dados.valor_total_nf)}</td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
