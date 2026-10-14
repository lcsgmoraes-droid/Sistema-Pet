import { useState } from "react";
import { montarNomeXml } from "./entradaXmlUtils";
import { normalizarMensagemErroSefaz } from "./sefazConsultaUtils.mjs";

const CONSULTA_SEFAZ_TIMEOUT_MS = 45000;

const CONFIG_SEFAZ_INICIAL = {
  enabled: false,
  modo: "mock",
  ambiente: "homologacao",
  uf: "SP",
  cnpj: "",
  importacao_automatica: false,
  importacao_intervalo_min: 60,
  encaminhamento_email_ativo: false,
  encaminhamento_email_destino: "",
  ultimo_nsu: "000000000000000",
  ultimo_sync_max_nsu_retorno: null,
  ultimo_max_nsu_confirmado: null,
  ultimo_sync_cstat: null,
  cert_ok: false,
  mensagem: "",
  pendencias: [],
  ultimo_sync_status: "nunca",
  ultimo_sync_mensagem: "Ainda nao sincronizado.",
  ultimo_sync_at: null,
  ultimo_sync_documentos: 0,
};

export default function useEntradaXmlSefaz({ api, abrirDetalhes, carregarDados, toast }) {
  const [mostrarPainelSefaz, setMostrarPainelSefaz] = useState(false);
  const [mostrarConfigSefaz, setMostrarConfigSefaz] = useState(false);
  const [chaveSefaz, setChaveSefaz] = useState("");
  const [consultasSefaz, setConsultasSefaz] = useState([]);
  const [consultaExpandidaId, setConsultaExpandidaId] = useState(null);
  const [importandoConsultaId, setImportandoConsultaId] = useState(null);
  const [erroSefaz, setErroSefaz] = useState("");
  const [avisoConectorSefaz, setAvisoConectorSefaz] = useState("");
  const [loadingSefaz, setLoadingSefaz] = useState(false);
  const [configSefazLoading, setConfigSefazLoading] = useState(false);
  const [salvandoRotina, setSalvandoRotina] = useState(false);
  const [mensagemRotina, setMensagemRotina] = useState("");
  const [cfgSefaz, setCfgSefaz] = useState(CONFIG_SEFAZ_INICIAL);

  const carregarConfigSefaz = async () => {
    try {
      setConfigSefazLoading(true);
      const { data } = await api.get("/sefaz/config");
      setCfgSefaz((prev) => ({
        ...prev,
        enabled: Boolean(data.enabled),
        modo: data.modo || "mock",
        ambiente: data.ambiente || "homologacao",
        uf: data.uf || "SP",
        cnpj: data.cnpj || "",
        importacao_automatica: Boolean(data.importacao_automatica),
        importacao_intervalo_min: Number(data.importacao_intervalo_min || 15),
        encaminhamento_email_ativo: Boolean(data.encaminhamento_email_ativo),
        encaminhamento_email_destino: data.encaminhamento_email_destino || "",
        ultimo_nsu: data.ultimo_nsu ?? "000000000000000",
        ultimo_sync_max_nsu_retorno: data.ultimo_sync_max_nsu_retorno ?? null,
        ultimo_max_nsu_confirmado: data.ultimo_max_nsu_confirmado ?? null,
        ultimo_sync_cstat: data.ultimo_sync_cstat ?? null,
        cert_ok: Boolean(data.cert_ok),
        mensagem: data.mensagem || "",
        pendencias: Array.isArray(data.pendencias) ? data.pendencias : [],
        ultimo_sync_status: data.ultimo_sync_status || "nunca",
        ultimo_sync_mensagem: data.ultimo_sync_mensagem || "Ainda nao sincronizado.",
        ultimo_sync_at: data.ultimo_sync_at || null,
        ultimo_sync_documentos: Number(data.ultimo_sync_documentos || 0),
      }));
    } catch {
      setMensagemRotina("Nao foi possivel carregar a configuracao da SEFAZ.");
    } finally {
      setConfigSefazLoading(false);
    }
  };

  const salvarRotinaSefaz = async () => {
    setMensagemRotina("");
    try {
      setSalvandoRotina(true);
      await api.post("/sefaz/config", {
        enabled: cfgSefaz.enabled,
        modo: cfgSefaz.modo,
        ambiente: cfgSefaz.ambiente,
        uf: cfgSefaz.uf,
        cnpj: cfgSefaz.cnpj,
        importacao_automatica: cfgSefaz.importacao_automatica,
        importacao_intervalo_min: Number(cfgSefaz.importacao_intervalo_min || 15),
      });
      setMensagemRotina("Rotina automatica salva com sucesso.");
      await carregarConfigSefaz();
    } catch (err) {
      setMensagemRotina(err?.response?.data?.detail || "Erro ao salvar rotina automatica.");
    } finally {
      setSalvandoRotina(false);
    }
  };

  const consultarSefaz = async (event) => {
    event.preventDefault();
    setErroSefaz("");
    setAvisoConectorSefaz("");
    const configuracaoPronta = cfgSefaz.enabled && cfgSefaz.modo === "real" && cfgSefaz.cert_ok;
    if (!configuracaoPronta) {
      const detalhes = cfgSefaz.pendencias.length
        ? ` Pendencias: ${cfgSefaz.pendencias.join("; ")}.`
        : "";
      setErroSefaz(
        `Consulta bloqueada. Configure o certificado digital e a integracao SEFAZ em Configuracoes > Integracoes.${detalhes}`,
      );
      return;
    }
    if (chaveSefaz.length !== 44) {
      setErroSefaz("A chave de acesso deve ter exatamente 44 digitos.");
      return;
    }
    try {
      setLoadingSefaz(true);
      const resp = await api.post(
        "/sefaz/consultar",
        { chave_acesso: chaveSefaz },
        { timeout: CONSULTA_SEFAZ_TIMEOUT_MS },
      );
      const novaConsulta = {
        id: `${Date.now()}-${resp.data.chave_acesso}`,
        criadoEm: new Date().toISOString(),
        dados: resp.data,
      };
      setConsultasSefaz((prev) => [novaConsulta, ...prev]);
      setConsultaExpandidaId(null);
    } catch (err) {
      const msg = normalizarMensagemErroSefaz(err);
      const httpStatus = Number(err?.response?.status || 0);
      if (httpStatus === 501 && msg.toLowerCase().includes("conector")) {
        setAvisoConectorSefaz(msg);
      } else {
        setErroSefaz(msg);
      }
    } finally {
      setLoadingSefaz(false);
    }
  };

  const usarNaEntrada = async (consulta) => {
    const xmlNfe = consulta?.dados?.xml_nfe;
    if (!xmlNfe) {
      toast.error(
        "Esta consulta nao trouxe XML completo. Tente outra chave ou rode sincronizacao real.",
      );
      return;
    }
    try {
      setImportandoConsultaId(consulta.id);
      const fileName = montarNomeXml(consulta.dados);
      const blob = new Blob([xmlNfe], { type: "application/xml;charset=utf-8" });
      const file = new File([blob], fileName, { type: "text/xml" });
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post("/notas-entrada/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("NF-e importada com sucesso!");
      await carregarDados();
      const notaIdCriada = data?.nota_id;
      if (notaIdCriada) {
        await abrirDetalhes(notaIdCriada);
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || "Falha ao importar NF-e.";
      toast.error(msg);
    } finally {
      setImportandoConsultaId(null);
    }
  };

  const alternarPainelSefaz = () => {
    const deveCarregar = !mostrarPainelSefaz;
    setMostrarPainelSefaz((visivel) => !visivel);
    if (deveCarregar) {
      carregarConfigSefaz();
    }
    setMostrarConfigSefaz(false);
  };

  const alternarConfigSefaz = () => {
    const deveCarregar = !mostrarConfigSefaz;
    setMostrarConfigSefaz((visivel) => !visivel);
    if (deveCarregar) {
      carregarConfigSefaz();
    }
    setMostrarPainelSefaz(false);
  };

  return {
    avisoConectorSefaz,
    chaveSefaz,
    cfgSefaz,
    configSefazLoading,
    consultaExpandidaId,
    consultasSefaz,
    consultarSefaz,
    erroSefaz,
    importandoConsultaId,
    loadingSefaz,
    mensagemRotina,
    mostrarConfigSefaz,
    mostrarPainelSefaz,
    salvarRotinaSefaz,
    salvandoRotina,
    setCfgSefaz,
    setChaveSefaz,
    setConsultaExpandidaId,
    usarNaEntrada,
    alternarConfigSefaz,
    alternarPainelSefaz,
  };
}
