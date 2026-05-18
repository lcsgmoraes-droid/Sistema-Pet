import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import { getAccessToken } from '../auth/tokenStorage';
import { toast } from 'react-hot-toast';
import { formatMoneyBRL } from '../utils/formatters';
import EntradaXmlCriarProdutoModal from './entrada-xml/EntradaXmlCriarProdutoModal';
import EntradaXmlDetalhesModal from './entrada-xml/EntradaXmlDetalhesModal';
import EntradaXmlHistoricoPrecosModal from './entrada-xml/EntradaXmlHistoricoPrecosModal';
import EntradaXmlHeader from './entrada-xml/EntradaXmlHeader';
import EntradaXmlMetricas from './entrada-xml/EntradaXmlMetricas';
import EntradaXmlNotasTable from './entrada-xml/EntradaXmlNotasTable';
import EntradaXmlRascunhoDevolucaoModal from './entrada-xml/EntradaXmlRascunhoDevolucaoModal';
import EntradaXmlRevisaoPrecosModal from './entrada-xml/EntradaXmlRevisaoPrecosModal';
import EntradaXmlResultadoLoteModal from './entrada-xml/EntradaXmlResultadoLoteModal';
import EntradaXmlSefazPanels from './entrada-xml/EntradaXmlSefazPanels';
import EntradaXmlVisualizacaoNotaModal from './entrada-xml/EntradaXmlVisualizacaoNotaModal';
import useEntradaXmlProdutos from './entrada-xml/useEntradaXmlProdutos';
import useEntradaXmlRevisaoPrecos from './entrada-xml/useEntradaXmlRevisaoPrecos';
import useEntradaXmlSefaz from './entrada-xml/useEntradaXmlSefaz';
import useEntradaXmlUpload from './entrada-xml/useEntradaXmlUpload';
import {
  ACAO_CONFERENCIA_OPCOES,
  CONFERENCIA_STATUS_META,
  aplicarMultiplicadorPackAoItem,
  calcularConferenciaItem,
  calcularResumoConferencia,
  detectarDivergencias,
  formatarOpcaoProduto,
  formatarValorFiscal,
  montarConferenciaState,
  normalizarNumeroConferencia,
  obterConfiguracaoPackItem,
  obterCustoAquisicaoItem,
  obterDraftConferenciaItem,
} from './entrada-xml/entradaXmlUtils';

const EntradaXML = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const autoOpenNotaIdRef = useRef(null);
  const [notasEntrada, setNotasEntrada] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notaSelecionada, setNotaSelecionada] = useState(null);
  const [mostrarDetalhes, setMostrarDetalhes] = useState(false);
  const [mostrarVisualizacao, setMostrarVisualizacao] = useState(false);
  const [mostrarCamposConferencia, setMostrarCamposConferencia] = useState(false);
  const [filtroItensNota, setFiltroItensNota] = useState('todos');
  const [conferenciaItens, setConferenciaItens] = useState({});
  const [conferenciaObservacaoGeral, setConferenciaObservacaoGeral] = useState('');
  const [salvandoConferencia, setSalvandoConferencia] = useState(false);
  const [desfazendoConferencia, setDesfazendoConferencia] = useState(false);
  const [gerandoRascunhoDevolucao, setGerandoRascunhoDevolucao] = useState(false);
  const [criandoPendenciaFornecedor, setCriandoPendenciaFornecedor] = useState(false);
  const [rascunhoDevolucao, setRascunhoDevolucao] = useState(null);
  const [mostrarRascunhoDevolucao, setMostrarRascunhoDevolucao] = useState(false);
  
  // Estados para historico de precos
  const [mostrarHistoricoPrecos, setMostrarHistoricoPrecos] = useState(false);
  const [historicoPrecos, setHistoricoPrecos] = useState([]);
  const [produtoHistorico, setProdutoHistorico] = useState(null);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  
  // Estados para rateio (APENAS informativo - estoque e UNIFICADO)
  const [tipoRateio, setTipoRateio] = useState('loja'); // 'online', 'loja', 'parcial'
  const [quantidadesOnline, setQuantidadesOnline] = useState({}); // {item_id: quantidade_online}
  const [multiplicadoresPack, setMultiplicadoresPack] = useState({}); // {item_id: multiplicador} para override manual

  // Filtro de status da tabela
  const [filtroStatus, setFiltroStatus] = useState('todos');

  const aplicarNotaSelecionada = (dadosNota) => {
    const notaNormalizada = {
      ...dadosNota,
      itens: [...(dadosNota?.itens || [])].sort((a, b) => a.id - b.id),
    };

    setNotaSelecionada(notaNormalizada);
    setConferenciaItens(montarConferenciaState(notaNormalizada));
    setConferenciaObservacaoGeral(notaNormalizada?.conferencia?.observacao_geral || '');
    setTipoRateio(notaNormalizada.tipo_rateio || 'loja');

    return notaNormalizada;
  };

  const sincronizarNotaNaLista = (dadosNota) => {
    if (!dadosNota?.id) return;

    const conferenciaStatus = dadosNota?.conferencia?.status || dadosNota?.conferencia_status || 'nao_iniciada';
    const divergenciasCount = Number(
      dadosNota?.conferencia?.itens_com_divergencia ??
      dadosNota?.divergencias_count ??
      0,
    );

    setNotasEntrada((prev) => prev.map((nota) => {
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
        produtos_nao_vinculados: dadosNota.produtos_nao_vinculados ?? nota.produtos_nao_vinculados,
        entrada_estoque_realizada: dadosNota.entrada_estoque_realizada ?? nota.entrada_estoque_realizada,
        conferencia_status: conferenciaStatus,
        divergencias_count: divergenciasCount,
      };
    }));
  };

  const atualizarCampoConferenciaItem = (item, campo, valor) => {
    setConferenciaItens((prev) => {
      const atual = prev[item.id] || obterDraftConferenciaItem(item);
      const quantidadeNF = Number(item.quantidade ?? item.quantidade_nf ?? 0);
      const proximo = { ...atual };

      if (campo === 'quantidade_conferida') {
        proximo.quantidade_conferida = Math.max(
          0,
          Math.min(normalizarNumeroConferencia(valor, atual.quantidade_conferida), quantidadeNF),
        );
        proximo.quantidade_avariada = Math.min(
          Number(proximo.quantidade_avariada || 0),
          Math.max(0, quantidadeNF - proximo.quantidade_conferida),
        );
      } else if (campo === 'quantidade_avariada') {
        proximo.quantidade_avariada = Math.max(
          0,
          Math.min(
            normalizarNumeroConferencia(valor, atual.quantidade_avariada),
            Math.max(0, quantidadeNF - Number(proximo.quantidade_conferida ?? atual.quantidade_conferida ?? quantidadeNF)),
          ),
        );
      } else if (campo === 'observacao_conferencia') {
        proximo.observacao_conferencia = String(valor ?? '');
      } else if (campo === 'acao_sugerida') {
        proximo.acao_sugerida = valor || 'sem_acao';
      }

      const conferenciaItem = calcularConferenciaItem(item, proximo);
      if (!conferenciaItem.temDivergencia) {
        proximo.acao_sugerida = 'sem_acao';
      } else if (!proximo.acao_sugerida || proximo.acao_sugerida === 'sem_acao') {
        proximo.acao_sugerida = conferenciaItem.quantidadeAvariada > 0
          ? 'nf_devolucao'
          : 'contatar_fornecedor';
      }

      return {
        ...prev,
        [item.id]: proximo,
      };
    });
  };

  const construirPayloadConferencia = () => {
    if (!notaSelecionada) return null;

    return {
      observacao_geral: conferenciaObservacaoGeral || null,
      itens: notaSelecionada.itens.map((item) => {
        const conferenciaItem = calcularConferenciaItem(item, conferenciaItens[item.id]);
        return {
          item_id: item.id,
          quantidade_conferida: conferenciaItem.quantidadeConferida,
          quantidade_avariada: conferenciaItem.quantidadeAvariada,
          observacao_conferencia: conferenciaItem.observacaoConferencia || null,
          acao_sugerida: conferenciaItem.acaoSugerida,
        };
      }),
    };
  };

  const salvarConferenciaAtual = async ({ silencioso = false } = {}) => {
    if (!notaSelecionada) return false;

    setSalvandoConferencia(true);
    try {
      const payload = construirPayloadConferencia();
      await api.post(`/notas-entrada/${notaSelecionada.id}/conferencia`, payload);
      const notaResponse = await api.get(`/notas-entrada/${notaSelecionada.id}`);
      const notaAtualizada = aplicarNotaSelecionada(notaResponse.data);
      sincronizarNotaNaLista(notaAtualizada);
      await carregarDados();

      if (!silencioso) {
        toast.success('Conferencia salva com sucesso');
      }

      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar conferencia');
      return false;
    } finally {
      setSalvandoConferencia(false);
    }
  };

  const desfazerConferenciaAtual = async () => {
    if (!notaSelecionada) return false;

    const confirmou = window.confirm('Deseja desfazer a conferencia desta NF e voltar para o estado nao conferido?');
    if (!confirmou) {
      return false;
    }

    setDesfazendoConferencia(true);
    try {
      await api.post(`/notas-entrada/${notaSelecionada.id}/conferencia/desfazer`);
      const notaResponse = await api.get(`/notas-entrada/${notaSelecionada.id}`);
      const notaAtualizada = aplicarNotaSelecionada(notaResponse.data);
      sincronizarNotaNaLista(notaAtualizada);
      setMostrarCamposConferencia(false);
      await carregarDados();
      toast.success('Conferencia desfeita com sucesso');
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao desfazer conferencia');
      return false;
    } finally {
      setDesfazendoConferencia(false);
    }
  };

  const gerarRascunhoDevolucao = async () => {
    if (!notaSelecionada) return;

    if (notaSelecionada.status === 'pendente') {
      const conferenciaSalva = await salvarConferenciaAtual({ silencioso: true });
      if (!conferenciaSalva) return;
    }

    setGerandoRascunhoDevolucao(true);
    try {
      const { data } = await api.get(`/notas-entrada/${notaSelecionada.id}/devolucao-draft`);
      setRascunhoDevolucao(data);
      setMostrarRascunhoDevolucao(true);

      if (data.disponivel) {
        toast.success('Rascunho de NF de devolucao gerado');
      } else {
        toast('Nao ha itens avariados para NF de devolucao');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao gerar rascunho da NF de devolucao');
    } finally {
      setGerandoRascunhoDevolucao(false);
    }
  };

  const gerarPendenciaFornecedor = async () => {
    if (!notaSelecionada) return;

    if ((resumoConferenciaAtual?.itens_com_divergencia || 0) <= 0) {
      toast.error('Nao ha divergencias para acompanhar com o fornecedor');
      return;
    }

    if (notaSelecionada.status === 'pendente') {
      const conferenciaSalva = await salvarConferenciaAtual({ silencioso: true });
      if (!conferenciaSalva) return;
    }

    setCriandoPendenciaFornecedor(true);
    try {
      const { data } = await api.post(`/compras-pendencias/notas/${notaSelecionada.id}`, {});
      toast.success(`Pendencia ${data?.codigo || ''} criada para acompanhamento`);

      const abrirPendencias = window.confirm(
        'Pendencia criada com relatorio e texto de e-mail sugerido. Deseja abrir a tela de pendencias agora?'
      );

      if (abrirPendencias) {
        setMostrarDetalhes(false);
        navigate('/compras/pendencias');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao criar pendencia do fornecedor');
    } finally {
      setCriandoPendenciaFornecedor(false);
    }
  };

  useEffect(() => {
    console.log('?? [EntradaXML] Componente montado, iniciando carregamento...');
    carregarDados();
  }, []);

  useEffect(() => {
    const notaIdParam = searchParams.get('nota_id');
    if (!notaIdParam) return;
    if (autoOpenNotaIdRef.current === notaIdParam) return;

    const notaId = Number(notaIdParam);
    if (Number.isNaN(notaId)) return;

    autoOpenNotaIdRef.current = notaIdParam;
    abrirDetalhes(notaId).finally(() => {
      const params = new URLSearchParams(searchParams);
      params.delete('nota_id');
      setSearchParams(params, { replace: true });
    });
  }, [searchParams, setSearchParams]);

  const carregarDados = async () => {
    console.log('?? [EntradaXML] Carregando dados...');
    try {
      const token = getAccessToken();
      console.log('?? [EntradaXML] Token obtido:', token ? 'SIM' : 'NAO');
      const headers = { Authorization: `Bearer ${token}` };

      console.log('?? [EntradaXML] Fazendo requisicoes para:', {
        notasEntrada: `/notas-entrada/`
      });

      const notasRes = await api.get(`/notas-entrada/`, { headers });

      console.log('? [EntradaXML] Dados carregados:', {
        notasEntrada: notasRes.data?.length || 0
      });

      setNotasEntrada(notasRes.data);
    } catch (error) {
      console.error('? [EntradaXML] ERRO ao carregar dados:');
      console.error('  - Mensagem:', error.message);
      console.error('  - Response:', error.response?.data);
      console.error('  - Status:', error.response?.status);
      console.error('  - Stack:', error.stack);
      toast.error(`Erro ao carregar dados: ${error.response?.data?.detail || error.message}`);
    }
  };



  const abrirDetalhes = async (notaId, { abrirConferencia = false } = {}) => {
    try {
      const response = await api.get(`/notas-entrada/${notaId}`);
      const nota = aplicarNotaSelecionada(response.data);
      const temDivergenciaConferencia = (nota?.conferencia?.itens_com_divergencia || 0) > 0;
      setMostrarDetalhes(true);
      setMostrarCamposConferencia(abrirConferencia || temDivergenciaConferencia);
      setFiltroItensNota((abrirConferencia || temDivergenciaConferencia) ? 'divergencias' : 'todos');
      setMultiplicadoresPack({}); // limpar overrides manuais ao abrir nova nota
    } catch (error) {
      toast.error('Erro ao carregar detalhes da nota');
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
    mostrarModalLote,
    resultadoLote,
    uploadingFile,
    uploadingLote,
  } = useEntradaXmlUpload({
    api,
    carregarDados,
    toast,
  });

  const {
    atualizarCustoSistema,
    atualizarMargem,
    atualizarPrecoVenda,
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
    processarNota,
    setBaseCalculoMargem,
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

  const abrirVisualizacao = async (notaId) => {
    try {
      const response = await api.get(`/notas-entrada/${notaId}`);
      aplicarNotaSelecionada(response.data);
      setMostrarCamposConferencia(false);
      setFiltroItensNota('todos');
      setMostrarVisualizacao(true);
    } catch (error) {
      toast.error('Erro ao carregar nota');
    }
  };



  const salvarTipoRateio = async (notaId, tipo) => {
    try {
      await api.post(`/notas-entrada/${notaId}/rateio`, {
        tipo_rateio: tipo
      });

      let descricaoTipo = 'Rateio Parcial';
      if (tipo === 'online') descricaoTipo = '100% Online';
      if (tipo === 'loja') descricaoTipo = '100% Loja Fisica';
      toast.success(`Nota configurada: ${descricaoTipo}`);
      
      // Recarregar detalhes
      const response = await api.get(`/notas-entrada/${notaId}`);
      aplicarNotaSelecionada(response.data);
    } catch (error) {
      console.error('? Erro ao salvar tipo de rateio:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar tipo de rateio');
    }
  };

  const salvarQuantidadeOnlineItem = async (notaId, itemId, quantidadeOnline) => {
    try {
      const response = await api.post(`/notas-entrada/${notaId}/itens/${itemId}/rateio`, {
        quantidade_online: Number.parseFloat(quantidadeOnline) || 0  // Permitir 0
      });
      
      toast.success('?? Quantidade online configurada!');
      
      // Mostrar totais da nota
      const totais = response.data.nota_totais;
      toast.success(
        `Nota: ${totais.percentual_online.toFixed(1)}% Online (R$ ${totais.valor_online.toFixed(2)}) | ` +
        `${totais.percentual_loja.toFixed(1)}% Loja (R$ ${totais.valor_loja.toFixed(2)})`
      );
      
      // Atualizar apenas o item especifico e os totais da nota, sem recarregar tudo
      setNotaSelecionada(prev => ({
        ...prev,
        percentual_online: totais.percentual_online,
        percentual_loja: totais.percentual_loja,
        valor_online: totais.valor_online,
        valor_loja: totais.valor_loja,
        itens: prev.itens.map(i => 
          i.id === itemId 
            ? { ...i, quantidade_online: Number.parseFloat(quantidadeOnline) || 0 }
            : i
        )
      }));
      
      // Sincronizar estado local com valor salvo
      setQuantidadesOnline(prev => ({
        ...prev,
        [itemId]: Number.parseFloat(quantidadeOnline) || 0
      }));
    } catch (error) {
      console.error('? Erro ao salvar quantidade online:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar');
    }
  };

  const excluirNota = async (notaId, numeroNota) => {
    if (!confirm(`Tem certeza que deseja excluir a nota ${numeroNota}?`)) {
      return;
    }

    setLoading(true);
    try {
            await api.delete(`/notas-entrada/${notaId}`);

      toast.success('??? Nota excluída com sucesso!');
      
      if (mostrarDetalhes) {
        setMostrarDetalhes(false);
        setNotaSelecionada(null);
      }
      
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao excluir nota');
    } finally {
      setLoading(false);
    }
  };

  const buscarHistoricoPrecos = async (produtoId, produtoNome) => {
    setCarregandoHistorico(true);
    setProdutoHistorico({ id: produtoId, nome: produtoNome });
    setMostrarHistoricoPrecos(true);
    
    try {
            const response = await api.get(
        `/produtos/${produtoId}/historico-precos`
      );
      
      setHistoricoPrecos(response.data);
    } catch (error) {
      toast.error('Erro ao carregar historico de precos');
      setMostrarHistoricoPrecos(false);
    } finally {
      setCarregandoHistorico(false);
    }
  };

  const reverterNota = async (notaId, numeroNota) => {
    if (!confirm(`?? Tem certeza que deseja REVERTER a entrada da nota ${numeroNota}?\n\nIsso ira:\n• Remover as quantidades do estoque\n• Excluir os lotes criados\n• Estornar as contas a pagar lançadas\n• Restaurar o status da nota para pendente`)) {
      return;
    }

    setLoading(true);
    try {
            const response = await api.post(
        `/notas-entrada/${notaId}/reverter`,
        {}
      );

      toast.success(
        `? Entrada revertida! ${response.data.itens_revertidos} produtos ajustados`,
        { duration: 5000 }
      );
      
      if (mostrarDetalhes) {
        setMostrarDetalhes(false);
        setNotaSelecionada(null);
      }
      
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao reverter entrada');
    } finally {
      setLoading(false);
    }
  };






  const getConfiancaBadge = (confianca) => {
    if (!confianca) return <span className="text-gray-400 text-sm">Nao vinculado</span>;

    let nivel = 'baixa';
    if (confianca >= 90) nivel = 'alta';
    else if (confianca >= 70) nivel = 'media';

    const styles = {
      alta: 'bg-green-100 text-green-800',
      media: 'bg-yellow-100 text-yellow-800',
      baixa: 'bg-orange-100 text-orange-800'
    };

    let selo = 'BAIXA';
    if (nivel === 'alta') selo = 'OK';
    else if (nivel === 'media') selo = 'ATENCAO';
    
    return (
      <span className={`px-2 py-1 rounded text-xs font-semibold ${styles[nivel]}`}>
        {confianca.toFixed(1)}% {selo}
      </span>
    );
  };

  const resumoConferenciaAtual = notaSelecionada
    ? calcularResumoConferencia(notaSelecionada, conferenciaItens)
    : null;
  const metaConferenciaAtual = CONFERENCIA_STATUS_META[resumoConferenciaAtual?.status || 'nao_iniciada'];
  const itensNotaDetalhe = notaSelecionada?.itens || [];
  const itensComDivergenciaDetalhe = itensNotaDetalhe.filter((item) => {
    const conferenciaItem = calcularConferenciaItem(item, conferenciaItens[item.id]);
    const divergenciasCadastro = detectarDivergencias(item);
    return Boolean(item.tem_divergencia) || conferenciaItem.temDivergencia || divergenciasCadastro.length > 0;
  });
  const itensExibidosNota = filtroItensNota === 'divergencias'
    ? itensComDivergenciaDetalhe
    : itensNotaDetalhe;

  return (
    <div className="p-6">
      <EntradaXmlHeader
        mostrarConfigSefaz={mostrarConfigSefaz}
        mostrarPainelSefaz={mostrarPainelSefaz}
        onTogglePainelSefaz={alternarPainelSefaz}
        onToggleConfigSefaz={alternarConfigSefaz}
        onUploadXml={handleFileUpload}
        onUploadLote={handleMultipleFilesUpload}
        uploadingFile={uploadingFile}
        uploadingLote={uploadingLote}
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
        aberto={aberto}
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
        processarNota={processarNota}
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
          processarNota(notaId);
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
        filtroCusto={filtroCusto}
        setFiltroCusto={setFiltroCusto}
        obterResumoCustoItem={obterResumoCustoItem}
        exportarRelatorioCustosMaioresCSV={exportarRelatorioCustosMaioresCSV}
        exportarRelatorioCustosMaioresPDF={exportarRelatorioCustosMaioresPDF}
        gerandoRelatorioCustos={gerandoRelatorioCustos}
        baseCalculoMargem={baseCalculoMargem}
        setBaseCalculoMargem={setBaseCalculoMargem}
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
        onClose={() => {
          setMostrarHistoricoPrecos(false);
          setHistoricoPrecos([]);
          setProdutoHistorico(null);
        }}
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
