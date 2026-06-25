import { useEffect, useRef, useState } from "react";

import api from "../api";
import CentralNFSaidaView from "./centralNFSaida/CentralNFSaidaView";
import { montarDetalheFallback, soDigitos } from "./centralNFSaida/centralNFSaidaUtils";

export default function CentralNFSaida() {
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroSituacao, setFiltroSituacao] = useState("");
  const [dataInicial, setDataInicial] = useState("");
  const [dataFinal, setDataFinal] = useState("");
  const [busca, setBusca] = useState("");
  const [erro, setErro] = useState("");
  const [notaSelecionada, setNotaSelecionada] = useState(null);
  const [detalheNota, setDetalheNota] = useState(null);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false);
  const [erroDetalhe, setErroDetalhe] = useState("");
  const [modalCancelar, setModalCancelar] = useState(null);
  const [justificativa, setJustificativa] = useState("");
  const [cancelando, setCancelando] = useState(false);
  const [reconciliandoNotaId, setReconciliandoNotaId] = useState("");
  const detalhesNotasCacheRef = useRef(new Map());

  const [painelSefazAberto, setPainelSefazAberto] = useState(false);
  const [chave, setChave] = useState("");
  const [consultando, setConsultando] = useState(false);
  const [erroConsulta, setErroConsulta] = useState("");
  const [consultasSessao, setConsultasSessao] = useState([]);
  const [consultaExpandidaId, setConsultaExpandidaId] = useState(null);
  const listaConsultasRef = useRef(null);

  const [cfgLoading, setCfgLoading] = useState(true);
  const [salvandoRotina, setSalvandoRotina] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [msgRotina, setMsgRotina] = useState("");
  const [cfg, setCfg] = useState({
    enabled: false,
    modo: "mock",
    importacao_automatica: false,
    importacao_intervalo_min: 15,
    cert_ok: false,
    ultimo_sync_status: "nunca",
    ultimo_sync_mensagem: "Ainda não sincronizado.",
    ultimo_sync_at: null,
    ultimo_sync_documentos: 0,
  });

  useEffect(() => {
    carregarNotas(false);
  }, [filtroSituacao, dataInicial, dataFinal]);

  useEffect(() => {
    if (painelSefazAberto && cfgLoading) {
      carregarConfigSefaz();
    }
  }, [painelSefazAberto]);

  useEffect(() => {
    if (!consultasSessao.length || !listaConsultasRef.current) return;
    listaConsultasRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [consultasSessao.length]);

  async function carregarNotas(forceRefresh = false) {
    try {
      setLoading(true);
      setErro("");
      if (forceRefresh) {
        detalhesNotasCacheRef.current.clear();
      }
      const params = new URLSearchParams();
      if (filtroSituacao) params.append("situacao", filtroSituacao);
      if (dataInicial) params.append("data_inicial", dataInicial);
      if (dataFinal) params.append("data_final", dataFinal);
      if (forceRefresh) params.append("force_refresh", "true");
      const response = await api.get(`/nfe/?${params.toString()}`);
      setNotas(response.data.notas || []);
    } catch {
      setErro("Erro ao carregar notas fiscais");
    } finally {
      setLoading(false);
    }
  }

  async function baixarDanfe(nfeId, numero) {
    try {
      const response = await api.get(`/nfe/${nfeId}/danfe`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `danfe_${numero}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert("Erro ao baixar DANFE");
    }
  }

  async function baixarXml(nfeId, numero) {
    try {
      const response = await api.get(`/nfe/${nfeId}/xml`);
      const blob = new Blob([response.data.xml], { type: "application/xml" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `nfe_${numero}.xml`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert("Erro ao baixar XML");
    }
  }

  async function reconciliarFluxoNota(nota) {
    const notaId = String(nota?.id || "").trim();
    if (!notaId) {
      alert("Não foi possível identificar esta NF para reconciliar.");
      return;
    }

    try {
      setReconciliandoNotaId(notaId);
      const response = await api.post(`/nfe/${notaId}/reconciliar-fluxo`);
      const numero = response.data?.nf_numero || nota.numero || notaId;
      alert(`Fluxo da NF ${numero} reconciliado com sucesso.`);
      await carregarNotas(true);
    } catch (error) {
      const detail =
        typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : error.response?.data?.detail?.motivo || "Erro ao reconciliar o fluxo desta NF.";
      alert(detail);
    } finally {
      setReconciliandoNotaId("");
    }
  }

  async function abrirDetalhes(nota) {
    setNotaSelecionada(nota);
    setDetalheNota(montarDetalheFallback(nota));
    setErroDetalhe("");
    try {
      setCarregandoDetalhe(true);
      const cacheKey = `${nota.id}:${nota.modelo || ""}`;
      const detalheCache = detalhesNotasCacheRef.current.get(cacheKey);
      if (detalheCache) {
        setDetalheNota(detalheCache);
        return;
      }
      const response = await api.get(`/nfe/${nota.id}`, {
        params: { modelo: nota.modelo },
      });
      detalhesNotasCacheRef.current.set(cacheKey, response.data);
      setDetalheNota(response.data);
    } catch (error) {
      setErroDetalhe(
        error.response?.data?.detail || "Não foi possível carregar todos os detalhes desta nota.",
      );
    } finally {
      setCarregandoDetalhe(false);
    }
  }

  function fecharDetalhes() {
    setNotaSelecionada(null);
    setDetalheNota(null);
    setErroDetalhe("");
    setCarregandoDetalhe(false);
  }

  async function cancelarNota() {
    if (!justificativa || justificativa.length < 15) {
      alert("A justificativa deve ter no mínimo 15 caracteres");
      return;
    }
    try {
      setCancelando(true);
      await api.post(`/nfe/${modalCancelar.id}/cancelar`, { justificativa });
      alert("Nota fiscal cancelada com sucesso!");
      setModalCancelar(null);
      setJustificativa("");
      carregarNotas(true);
    } catch (error) {
      alert(error.response?.data?.detail || "Erro ao cancelar nota fiscal");
    } finally {
      setCancelando(false);
    }
  }

  async function excluirNota(vendaId, numero) {
    if (
      !globalThis.confirm(
        `Deseja realmente excluir a nota ${numero}?\n\nIsso apenas remove os dados da nota do sistema, não cancela no Bling/SEFAZ.`,
      )
    )
      return;
    try {
      await api.delete(`/nfe/${vendaId}`);
      alert("Nota fiscal excluída com sucesso!");
      carregarNotas(true);
    } catch (error) {
      alert(error.response?.data?.detail || "Erro ao excluir nota fiscal");
    }
  }

  async function carregarConfigSefaz() {
    try {
      setCfgLoading(true);
      const { data } = await api.get("/sefaz/config");
      setCfg((atual) => ({
        ...atual,
        enabled: Boolean(data.enabled),
        modo: data.modo || "mock",
        importacao_automatica: Boolean(data.importacao_automatica),
        importacao_intervalo_min: Number(data.importacao_intervalo_min || 15),
        cert_ok: Boolean(data.cert_ok),
        ultimo_sync_status: data.ultimo_sync_status || "nunca",
        ultimo_sync_mensagem: data.ultimo_sync_mensagem || "Ainda não sincronizado.",
        ultimo_sync_at: data.ultimo_sync_at || null,
        ultimo_sync_documentos: Number(data.ultimo_sync_documentos || 0),
      }));
    } catch {
      setMsgRotina("Não foi possível carregar a configuração SEFAZ.");
    } finally {
      setCfgLoading(false);
    }
  }

  async function salvarRotina() {
    setMsgRotina("");
    try {
      setSalvandoRotina(true);
      await api.post("/sefaz/config", {
        enabled: cfg.enabled,
        modo: cfg.modo,
        importacao_automatica: cfg.importacao_automatica,
        importacao_intervalo_min: Number(cfg.importacao_intervalo_min || 15),
      });
      setMsgRotina("Rotina automática salva com sucesso.");
      await carregarConfigSefaz();
    } catch (err) {
      setMsgRotina(err?.response?.data?.detail || "Erro ao salvar rotina automática.");
    } finally {
      setSalvandoRotina(false);
    }
  }

  async function sincronizarAgora() {
    setMsgRotina("");
    try {
      setSincronizando(true);
      const { data } = await api.post("/sefaz/sync-now");
      setMsgRotina(data?.mensagem || "Sincronização solicitada.");
      await carregarConfigSefaz();
    } catch (err) {
      setMsgRotina(err?.response?.data?.detail || "Erro ao sincronizar agora.");
    } finally {
      setSincronizando(false);
    }
  }

  async function consultarChave(event) {
    event.preventDefault();
    setErroConsulta("");
    if (chave.length !== 44) {
      setErroConsulta("A chave de acesso deve ter exatamente 44 dígitos.");
      return;
    }
    try {
      setConsultando(true);
      const resp = await api.post("/sefaz/consultar", { chave_acesso: chave });
      const dados = resp.data;

      const cnpjEmpresa = soDigitos(cfg.cnpj);
      const cnpjDest = soDigitos(dados.destinatario_cnpj);
      if (cnpjEmpresa && cnpjDest && cnpjDest === cnpjEmpresa) {
        setErroConsulta(
          "Esta chave parece ser NF de entrada (para a própria empresa). Use a tela Central NF-e Entradas.",
        );
        return;
      }

      const chaveDigitos = soDigitos(chave);
      const jaExiste = notas.some((nota) => soDigitos(nota.chave) === chaveDigitos);

      setConsultasSessao((atuais) => [
        { id: `${Date.now()}-${chave}`, criadoEm: new Date().toISOString(), dados, jaExiste },
        ...atuais,
      ]);
      setChave("");
    } catch (err) {
      setErroConsulta(err?.response?.data?.detail || "Erro ao consultar a SEFAZ.");
    } finally {
      setConsultando(false);
    }
  }

  const notasFiltradas = notas.filter((nota) => {
    if (!busca) return true;
    const buscaNormalizada = busca.toLowerCase();
    return (
      nota.numero?.toLowerCase().includes(buscaNormalizada) ||
      nota.serie?.toLowerCase().includes(buscaNormalizada) ||
      nota.cliente?.nome?.toLowerCase().includes(buscaNormalizada) ||
      nota.cliente?.cpf_cnpj?.toLowerCase().includes(buscaNormalizada) ||
      nota.canal_label?.toLowerCase().includes(buscaNormalizada) ||
      nota.loja?.nome?.toLowerCase().includes(buscaNormalizada) ||
      nota.numero_pedido_loja?.toLowerCase().includes(buscaNormalizada)
    );
  });

  return (
    <CentralNFSaidaView
      painelSefazAberto={painelSefazAberto}
      setPainelSefazAberto={setPainelSefazAberto}
      consultarChave={consultarChave}
      chave={chave}
      setChave={setChave}
      consultando={consultando}
      erroConsulta={erroConsulta}
      cfgLoading={cfgLoading}
      cfg={cfg}
      setCfg={setCfg}
      msgRotina={msgRotina}
      salvarRotina={salvarRotina}
      salvandoRotina={salvandoRotina}
      sincronizarAgora={sincronizarAgora}
      sincronizando={sincronizando}
      consultasSessao={consultasSessao}
      listaConsultasRef={listaConsultasRef}
      consultaExpandidaId={consultaExpandidaId}
      setConsultaExpandidaId={setConsultaExpandidaId}
      busca={busca}
      setBusca={setBusca}
      dataInicial={dataInicial}
      setDataInicial={setDataInicial}
      dataFinal={dataFinal}
      setDataFinal={setDataFinal}
      filtroSituacao={filtroSituacao}
      setFiltroSituacao={setFiltroSituacao}
      carregarNotas={carregarNotas}
      loading={loading}
      erro={erro}
      notasFiltradas={notasFiltradas}
      setModalCancelar={setModalCancelar}
      excluirNota={excluirNota}
      reconciliarFluxoNota={reconciliarFluxoNota}
      reconciliandoNotaId={reconciliandoNotaId}
      baixarDanfe={baixarDanfe}
      baixarXml={baixarXml}
      abrirDetalhes={abrirDetalhes}
      notaSelecionada={notaSelecionada}
      detalheNota={detalheNota}
      carregandoDetalhe={carregandoDetalhe}
      erroDetalhe={erroDetalhe}
      fecharDetalhes={fecharDetalhes}
      modalCancelar={modalCancelar}
      justificativa={justificativa}
      setJustificativa={setJustificativa}
      cancelando={cancelando}
      cancelarNota={cancelarNota}
    />
  );
}
