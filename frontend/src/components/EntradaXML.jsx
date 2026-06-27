import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../api";
import { getAccessToken } from "../auth/tokenStorage";
import { toast } from "react-hot-toast";
import { formatMoneyBRL } from "../utils/formatters";
import EntradaXmlCriarProdutoModal from "./entrada-xml/EntradaXmlCriarProdutoModal";
import EntradaXmlDetalhesModal from "./entrada-xml/EntradaXmlDetalhesModal";
import EntradaPdfUploadModal from "./entrada-xml/EntradaPdfUploadModal";
import EntradaXmlHistoricoPrecosModal from "./entrada-xml/EntradaXmlHistoricoPrecosModal";
import EntradaXmlHeader from "./entrada-xml/EntradaXmlHeader";
import EntradaXmlMetricas from "./entrada-xml/EntradaXmlMetricas";
import EntradaXmlNotasTable from "./entrada-xml/EntradaXmlNotasTable";
import EntradaXmlRascunhoDevolucaoModal from "./entrada-xml/EntradaXmlRascunhoDevolucaoModal";
import EntradaXmlRevisaoPrecosModal from "./entrada-xml/EntradaXmlRevisaoPrecosModal";
import EntradaXmlResultadoLoteModal from "./entrada-xml/EntradaXmlResultadoLoteModal";
import EntradaXmlSefazPanels from "./entrada-xml/EntradaXmlSefazPanels";
import EntradaXmlVisualizacaoNotaModal from "./entrada-xml/EntradaXmlVisualizacaoNotaModal";
import useEntradaXmlConferencia from "./entrada-xml/useEntradaXmlConferencia";
import useEntradaXmlHistoricoPrecos from "./entrada-xml/useEntradaXmlHistoricoPrecos";
import useEntradaXmlProdutos from "./entrada-xml/useEntradaXmlProdutos";
import useEntradaXmlRateio from "./entrada-xml/useEntradaXmlRateio";
import useEntradaXmlRevisaoPrecos from "./entrada-xml/useEntradaXmlRevisaoPrecos";
import useEntradaXmlSefaz from "./entrada-xml/useEntradaXmlSefaz";
import useEntradaXmlUpload from "./entrada-xml/useEntradaXmlUpload";
import {
  ACAO_CONFERENCIA_OPCOES,
  CONFERENCIA_STATUS_META,
  aplicarMultiplicadorPackAoItem,
  calcularConferenciaItem,
  formatarOpcaoProduto,
  formatarValorFiscal,
  obterConfiguracaoPackItem,
  obterCustoAquisicaoItem,
  detectarDivergencias,
  extrairMensagemErroApi,
} from "./entrada-xml/entradaXmlUtils";

const EntradaXML = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const autoOpenNotaIdRef = useRef(null);
  const [notasEntrada, setNotasEntrada] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mostrarDetalhes, setMostrarDetalhes] = useState(false);
  const [mostrarUploadPdf, setMostrarUploadPdf] = useState(false);
  const [mostrarVisualizacao, setMostrarVisualizacao] = useState(false);

  // Filtro de status da tabela
  const [filtroStatus, setFiltroStatus] = useState("todos");

  const {
    multiplicadoresPack,
    quantidadesOnline,
    salvarQuantidadeOnlineItem: salvarQuantidadeOnlineItemRateio,
    salvarTipoRateio: salvarTipoRateioRateio,
    setMultiplicadoresPack,
    setQuantidadesOnline,
    setTipoRateio,
    tipoRateio,
  } = useEntradaXmlRateio({ api, toast });

  const sincronizarNotaNaLista = (dadosNota) => {
    if (!dadosNota?.id) return;

    const conferenciaStatus =
      dadosNota?.conferencia?.status || dadosNota?.conferencia_status || "nao_iniciada";
    const divergenciasCount = Number(
      dadosNota?.conferencia?.itens_com_divergencia ?? dadosNota?.divergencias_count ?? 0,
    );

    setNotasEntrada((prev) =>
      prev.map((nota) => {
        if (nota.id !== dadosNota.id) {
          return nota;
        }

        return {
          ...nota,
          status: dadosNota.status ?? nota.status,
          fornecedor_nome: dadosNota.fornecedor_nome ?? nota.fornecedor_nome,
          fornecedor_cnpj: dadosNota.fornecedor_cnpj ?? nota.fornecedor_cnpj,
          data_emissao: dadosNota.data_emissao ?? nota.data_emissao,
          valor_total: dadosNota.valor_total ?? nota.valor_total,
          produtos_vinculados: dadosNota.produtos_vinculados ?? nota.produtos_vinculados,
          produtos_nao_vinculados:
            dadosNota.produtos_nao_vinculados ?? nota.produtos_nao_vinculados,
          entrada_estoque_realizada:
            dadosNota.entrada_estoque_realizada ?? nota.entrada_estoque_realizada,
          conferencia_status: conferenciaStatus,
          divergencias_count: divergenciasCount,
        };
      }),
    );
  };

  useEffect(() => {
    console.log("?? [EntradaXML] Componente montado, iniciando carregamento...");
    carregarDados();
  }, []);

  useEffect(() => {
    const notaIdParam = searchParams.get("nota_id");
    if (!notaIdParam) return;
    if (autoOpenNotaIdRef.current === notaIdParam) return;

    const notaId = Number(notaIdParam);
    if (Number.isNaN(notaId)) return;

    autoOpenNotaIdRef.current = notaIdParam;
    abrirDetalhes(notaId).finally(() => {
      const params = new URLSearchParams(searchParams);
      params.delete("nota_id");
      setSearchParams(params, { replace: true });
    });
  }, [searchParams, setSearchParams]);

  const carregarDados = async () => {
    console.log("?? [EntradaXML] Carregando dados...");
    try {
      const token = getAccessToken();
      console.log("?? [EntradaXML] Token obtido:", token ? "SIM" : "NAO");
      const headers = { Authorization: `Bearer ${token}` };

      console.log("?? [EntradaXML] Fazendo requisicoes para:", {
        notasEntrada: `/notas-entrada/`,
      });

      const notasRes = await api.get(`/notas-entrada/`, { headers });

      console.log("? [EntradaXML] Dados carregados:", {
        notasEntrada: notasRes.data?.length || 0,
      });

      setNotasEntrada(notasRes.data);
    } catch (error) {
      console.error("? [EntradaXML] ERRO ao carregar dados:");
      console.error("  - Mensagem:", error.message);
      console.error("  - Response:", error.response?.data);
      console.error("  - Status:", error.response?.status);
      console.error("  - Stack:", error.stack);
      toast.error(`Erro ao carregar dados: ${extrairMensagemErroApi(error)}`);
    }
  };

  const {
    buscarHistoricoPrecos,
    carregandoHistorico,
    fecharHistoricoPrecos,
    historicoPrecos,
    mostrarHistoricoPrecos,
    produtoHistorico,
  } = useEntradaXmlHistoricoPrecos({ api, toast });

  const {
    aplicarNotaSelecionada,
    atualizarCampoConferenciaItem,
    conferenciaItens,
    conferenciaObservacaoGeral,
    criandoPendenciaFornecedor,
    desfazendoConferencia,
    desfazerConferenciaAtual,
    filtroItensNota,
    gerandoRascunhoDevolucao,
    gerarPendenciaFornecedor,
    gerarRascunhoDevolucao,
    itensComDivergenciaDetalhe,
    itensExibidosNota,
    itensNotaDetalhe,
    metaConferenciaAtual,
    mostrarCamposConferencia,
    mostrarRascunhoDevolucao,
    notaSelecionada,
    rascunhoDevolucao,
    resumoConferenciaAtual,
    salvandoConferencia,
    salvarConferenciaAtual,
    setConferenciaObservacaoGeral,
    setFiltroItensNota,
    setMostrarCamposConferencia,
    setMostrarRascunhoDevolucao,
    setNotaSelecionada,
  } = useEntradaXmlConferencia({
    api,
    carregarDados,
    navigate,
    setMostrarDetalhes,
    setTipoRateio,
    sincronizarNotaNaLista,
    toast,
  });

  const abrirDetalhes = async (notaId, { abrirConferencia = false } = {}) => {
    try {
      const response = await api.get(`/notas-entrada/${notaId}`);
      const nota = aplicarNotaSelecionada(response.data);
      const temDivergenciaNosItens = (nota?.itens || []).some(
        (item) => Boolean(item.tem_divergencia) || detectarDivergencias(item).length > 0,
      );
      const temDivergenciaConferencia =
        (nota?.conferencia?.itens_com_divergencia || 0) > 0 || temDivergenciaNosItens;
      setMostrarDetalhes(true);
      setMostrarCamposConferencia(abrirConferencia || temDivergenciaConferencia);
      setFiltroItensNota(temDivergenciaConferencia ? "divergencias" : "todos");
      setMultiplicadoresPack({}); // limpar overrides manuais ao abrir nova nota
    } catch {
      toast.error("Erro ao carregar detalhes da nota");
    }
  };

  const {
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
  } = useEntradaXmlSefaz({
    api,
    abrirDetalhes,
    carregarDados,
    toast,
  });

  const {
    fecharResultadoLote,
    handleFileUpload,
    handleMultipleFilesUpload,
    handlePdfUpload,
    mostrarModalLote,
    resultadoLote,
    uploadingFile,
    uploadingLote,
    uploadingPdf,
  } = useEntradaXmlUpload({
    api,
    carregarDados,
    toast,
  });

  const {
    atualizarCustoSistema,
    atualizarMargem,
    atualizarPrecoVenda,
    acoesProcessamento,
    baseCalculoMargem,
    baseCalculoMargemOpcoes,
    calcularPrecoVenda,
    carregarPreviewProcessamento,
    confirmarProcessamento,
    exportarRelatorioCustosMaioresCSV,
    exportarRelatorioCustosMaioresPDF,
    filtroCusto,
    gerandoRelatorioCustos,
    inputsRevisaoCustos,
    inputsRevisaoPrecos,
    mostrarRevisaoPrecos,
    normalizarCamposRevisaoCustos,
    normalizarCamposRevisaoPrecos,
    obterResumoCustoItem,
    precosAjustados,
    previewProcessamento,
    setBaseCalculoMargem,
    setAcaoProcessamento,
    setFiltroCusto,
    voltarParaVisualizacao,
  } = useEntradaXmlRevisaoPrecos({
    api,
    carregarDados,
    multiplicadoresPack,
    notaSelecionada,
    salvarConferenciaAtual,
    setLoading,
    setMostrarDetalhes,
    setMostrarVisualizacao,
    setNotaSelecionada,
    toast,
  });

  const {
    abrirModalCriarProduto,
    atualizarFiltroProduto,
    buscandoProduto,
    calcularMargemLucro,
    carregandoSugestao,
    criarProdutoNovo,
    criarTodosProdutosNaoVinculados,
    desvincularProduto,
    fecharModalCriarProduto,
    filtroProduto,
    formProduto,
    itemSelecionadoParaCriar,
    mostrarModalCriarProduto,
    resultadosBuscaProduto,
    setFiltroProduto,
    setFormProduto,
    setResultadosBuscaProduto,
    sugestaoSku,
    vincularProduto,
  } = useEntradaXmlProdutos({
    api,
    aplicarNotaSelecionada,
    carregarDados,
    multiplicadoresPack,
    notaSelecionada,
    setLoading,
    toast,
  });

  const salvarTipoRateio = (notaId, tipo) =>
    salvarTipoRateioRateio(notaId, tipo, aplicarNotaSelecionada);

  const salvarQuantidadeOnlineItem = (notaId, itemId, quantidadeOnline) =>
    salvarQuantidadeOnlineItemRateio(notaId, itemId, quantidadeOnline, setNotaSelecionada);

  const abrirVisualizacao = async (notaId) => {
    try {
      const response = await api.get(`/notas-entrada/${notaId}`);
      aplicarNotaSelecionada(response.data);
      setMostrarCamposConferencia(false);
      setFiltroItensNota("todos");
      setMostrarVisualizacao(true);
    } catch {
      toast.error("Erro ao carregar nota");
    }
  };
  const excluirNota = async (notaId, numeroNota) => {
    if (!confirm(`Tem certeza que deseja excluir a nota ${numeroNota}?`)) {
      return;
    }

    setLoading(true);
    try {
      await api.delete(`/notas-entrada/${notaId}`);

      toast.success("??? Nota excluída com sucesso!");

      if (mostrarDetalhes) {
        setMostrarDetalhes(false);
        setNotaSelecionada(null);
      }

      carregarDados();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao excluir nota"));
    } finally {
      setLoading(false);
    }
  };

  const reverterNota = async (notaId, numeroNota) => {
    if (
      !confirm(
        `?? Tem certeza que deseja REVERTER a entrada da nota ${numeroNota}?\n\nIsso ira:\n• Remover as quantidades do estoque\n• Excluir os lotes criados\n• Estornar as contas a pagar lançadas\n• Restaurar o status da nota para pendente`,
      )
    ) {
      return;
    }

    setLoading(true);
    try {
      const response = await api.post(`/notas-entrada/${notaId}/reverter`, {});

      toast.success(`? Entrada revertida! ${response.data.itens_revertidos} produtos ajustados`, {
        duration: 5000,
      });

      if (mostrarDetalhes) {
        setMostrarDetalhes(false);
        setNotaSelecionada(null);
      }

      carregarDados();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao reverter entrada"));
    } finally {
      setLoading(false);
    }
  };

  const getConfiancaBadge = (confianca) => {
    if (!confianca) return <span className="text-gray-400 text-sm">Nao vinculado</span>;

    let nivel = "baixa";
    if (confianca >= 90) nivel = "alta";
    else if (confianca >= 70) nivel = "media";

    const styles = {
      alta: "bg-green-100 text-green-800",
      media: "bg-yellow-100 text-yellow-800",
      baixa: "bg-orange-100 text-orange-800",
    };

    let selo = "BAIXA";
    if (nivel === "alta") selo = "OK";
    else if (nivel === "media") selo = "ATENCAO";

    return (
      <span className={`px-2 py-1 rounded text-xs font-semibold ${styles[nivel]}`}>
        {confianca.toFixed(1)}% {selo}
      </span>
    );
  };

  return (
    <div className="p-6">
      <EntradaXmlHeader
        mostrarConfigSefaz={mostrarConfigSefaz}
        mostrarPainelSefaz={mostrarPainelSefaz}
        onTogglePainelSefaz={alternarPainelSefaz}
        onToggleConfigSefaz={alternarConfigSefaz}
        onUploadPdf={() => setMostrarUploadPdf(true)}
        onUploadXml={handleFileUpload}
        onUploadLote={handleMultipleFilesUpload}
        uploadingFile={uploadingFile}
        uploadingLote={uploadingLote}
        uploadingPdf={uploadingPdf}
      />

      <EntradaPdfUploadModal
        aberto={mostrarUploadPdf}
        loading={uploadingPdf}
        onClose={() => setMostrarUploadPdf(false)}
        onImportar={handlePdfUpload}
      />

      <EntradaXmlSefazPanels
        avisoConectorSefaz={avisoConectorSefaz}
        chaveSefaz={chaveSefaz}
        cfgSefaz={cfgSefaz}
        configSefazLoading={configSefazLoading}
        consultaExpandidaId={consultaExpandidaId}
        consultasSefaz={consultasSefaz}
        consultarSefaz={consultarSefaz}
        erroSefaz={erroSefaz}
        formatMoneyBRL={formatMoneyBRL}
        importandoConsultaId={importandoConsultaId}
        loadingSefaz={loadingSefaz}
        mensagemRotina={mensagemRotina}
        mostrarConfigSefaz={mostrarConfigSefaz}
        mostrarPainelSefaz={mostrarPainelSefaz}
        salvarRotinaSefaz={salvarRotinaSefaz}
        salvandoRotina={salvandoRotina}
        setCfgSefaz={setCfgSefaz}
        setChaveSefaz={setChaveSefaz}
        setConsultaExpandidaId={setConsultaExpandidaId}
        usarNaEntrada={usarNaEntrada}
      />

      <EntradaXmlMetricas
        notasEntrada={notasEntrada}
        formatMoneyBRL={formatMoneyBRL}
        onFiltroStatus={setFiltroStatus}
      />

      <EntradaXmlNotasTable
        abrirDetalhes={abrirDetalhes}
        abrirVisualizacao={abrirVisualizacao}
        conferenciaStatusMeta={CONFERENCIA_STATUS_META}
        excluirNota={excluirNota}
        filtroStatus={filtroStatus}
        formatMoneyBRL={formatMoneyBRL}
        notasEntrada={notasEntrada}
        reverterNota={reverterNota}
        setFiltroStatus={setFiltroStatus}
      />

      <EntradaXmlDetalhesModal
        acaoConferenciaOpcoes={ACAO_CONFERENCIA_OPCOES}
        aberto={mostrarDetalhes}
        abrirModalCriarProduto={abrirModalCriarProduto}
        aplicarMultiplicadorPackAoItem={aplicarMultiplicadorPackAoItem}
        atualizarCampoConferenciaItem={atualizarCampoConferenciaItem}
        atualizarFiltroProduto={atualizarFiltroProduto}
        buscandoProduto={buscandoProduto}
        calcularConferenciaItem={calcularConferenciaItem}
        carregarPreviewProcessamento={carregarPreviewProcessamento}
        conferenciaItens={conferenciaItens}
        conferenciaObservacaoGeral={conferenciaObservacaoGeral}
        criandoPendenciaFornecedor={criandoPendenciaFornecedor}
        criarTodosProdutosNaoVinculados={criarTodosProdutosNaoVinculados}
        desfazendoConferencia={desfazendoConferencia}
        desfazerConferenciaAtual={desfazerConferenciaAtual}
        desvincularProduto={desvincularProduto}
        detectarDivergencias={detectarDivergencias}
        excluirNota={excluirNota}
        filtroItensNota={filtroItensNota}
        filtroProduto={filtroProduto}
        formatarOpcaoProduto={formatarOpcaoProduto}
        formatarValorFiscal={formatarValorFiscal}
        gerandoRascunhoDevolucao={gerandoRascunhoDevolucao}
        gerarPendenciaFornecedor={gerarPendenciaFornecedor}
        gerarRascunhoDevolucao={gerarRascunhoDevolucao}
        getConfiancaBadge={getConfiancaBadge}
        itensComDivergenciaDetalhe={itensComDivergenciaDetalhe}
        itensExibidosNota={itensExibidosNota}
        itensNotaDetalhe={itensNotaDetalhe}
        loading={loading}
        metaConferenciaAtual={metaConferenciaAtual}
        mostrarCamposConferencia={mostrarCamposConferencia}
        multiplicadoresPack={multiplicadoresPack}
        navigate={navigate}
        notaSelecionada={notaSelecionada}
        obterConfiguracaoPackItem={obterConfiguracaoPackItem}
        obterCustoAquisicaoItem={obterCustoAquisicaoItem}
        quantidadesOnline={quantidadesOnline}
        resultadosBuscaProduto={resultadosBuscaProduto}
        resumoConferenciaAtual={resumoConferenciaAtual}
        reverterNota={reverterNota}
        salvandoConferencia={salvandoConferencia}
        salvarConferenciaAtual={salvarConferenciaAtual}
        salvarQuantidadeOnlineItem={salvarQuantidadeOnlineItem}
        salvarTipoRateio={salvarTipoRateio}
        setConferenciaObservacaoGeral={setConferenciaObservacaoGeral}
        setFiltroItensNota={setFiltroItensNota}
        setFiltroProduto={setFiltroProduto}
        setMostrarCamposConferencia={setMostrarCamposConferencia}
        setMostrarDetalhes={setMostrarDetalhes}
        setMultiplicadoresPack={setMultiplicadoresPack}
        setNotaSelecionada={setNotaSelecionada}
        setQuantidadesOnline={setQuantidadesOnline}
        setResultadosBuscaProduto={setResultadosBuscaProduto}
        tipoRateio={tipoRateio}
        vincularProduto={vincularProduto}
      />

      <EntradaXmlCriarProdutoModal
        aberto={mostrarModalCriarProduto}
        calcularMargemLucro={calcularMargemLucro}
        calcularPrecoVenda={calcularPrecoVenda}
        carregandoSugestao={carregandoSugestao}
        criarProdutoNovo={criarProdutoNovo}
        formProduto={formProduto}
        formatarValorFiscal={formatarValorFiscal}
        itemSelecionadoParaCriar={itemSelecionadoParaCriar}
        loading={loading}
        obterCustoAquisicaoItem={obterCustoAquisicaoItem}
        onClose={fecharModalCriarProduto}
        setFormProduto={setFormProduto}
        sugestaoSku={sugestaoSku}
      />
      <EntradaXmlVisualizacaoNotaModal
        aberto={mostrarVisualizacao}
        notaSelecionada={notaSelecionada}
        resumoConferenciaAtual={resumoConferenciaAtual}
        metaConferenciaAtual={metaConferenciaAtual}
        onClose={() => {
          setMostrarVisualizacao(false);
          setNotaSelecionada(null);
        }}
        onAbrirConferencia={(notaId) => {
          setMostrarVisualizacao(false);
          abrirDetalhes(notaId, { abrirConferencia: true });
        }}
        onAbrirDetalhes={(notaId) => {
          setMostrarVisualizacao(false);
          abrirDetalhes(notaId);
        }}
        onAjustarCustos={(notaId) => {
          setMostrarVisualizacao(false);
          carregarPreviewProcessamento(notaId);
        }}
      />
      <EntradaXmlRascunhoDevolucaoModal
        aberto={mostrarRascunhoDevolucao}
        rascunhoDevolucao={rascunhoDevolucao}
        onClose={() => setMostrarRascunhoDevolucao(false)}
      />
      <EntradaXmlRevisaoPrecosModal
        aberto={mostrarRevisaoPrecos}
        previewProcessamento={previewProcessamento}
        acoesProcessamento={acoesProcessamento}
        filtroCusto={filtroCusto}
        setFiltroCusto={setFiltroCusto}
        obterResumoCustoItem={obterResumoCustoItem}
        exportarRelatorioCustosMaioresCSV={exportarRelatorioCustosMaioresCSV}
        exportarRelatorioCustosMaioresPDF={exportarRelatorioCustosMaioresPDF}
        gerandoRelatorioCustos={gerandoRelatorioCustos}
        baseCalculoMargem={baseCalculoMargem}
        setBaseCalculoMargem={setBaseCalculoMargem}
        setAcaoProcessamento={setAcaoProcessamento}
        baseCalculoMargemOpcoes={baseCalculoMargemOpcoes}
        precosAjustados={precosAjustados}
        inputsRevisaoPrecos={inputsRevisaoPrecos}
        inputsRevisaoCustos={inputsRevisaoCustos}
        buscarHistoricoPrecos={buscarHistoricoPrecos}
        atualizarCustoSistema={atualizarCustoSistema}
        normalizarCamposRevisaoCustos={normalizarCamposRevisaoCustos}
        atualizarPrecoVenda={atualizarPrecoVenda}
        normalizarCamposRevisaoPrecos={normalizarCamposRevisaoPrecos}
        atualizarMargem={atualizarMargem}
        confirmarProcessamento={confirmarProcessamento}
        loading={loading}
        onVoltar={voltarParaVisualizacao}
      />
      <EntradaXmlHistoricoPrecosModal
        aberto={mostrarHistoricoPrecos}
        carregandoHistorico={carregandoHistorico}
        historicoPrecos={historicoPrecos}
        produtoHistorico={produtoHistorico}
        onClose={fecharHistoricoPrecos}
      />

      <EntradaXmlResultadoLoteModal
        aberto={mostrarModalLote}
        onClose={fecharResultadoLote}
        resultadoLote={resultadoLote}
        uploadingLote={uploadingLote}
      />
    </div>
  );
};

export default EntradaXML;
