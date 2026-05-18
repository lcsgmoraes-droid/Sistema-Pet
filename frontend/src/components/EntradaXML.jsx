import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import { getAccessToken } from '../auth/tokenStorage';
import { toast } from 'react-hot-toast';
import { formatBRL, formatMoneyBRL } from '../utils/formatters';
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
import useEntradaXmlSefaz from './entrada-xml/useEntradaXmlSefaz';
import {
  exportarRelatorioCustosMaioresCSV as exportarRelatorioCustosMaioresCSVArquivo,
  exportarRelatorioCustosMaioresPDF as exportarRelatorioCustosMaioresPDFArquivo,
} from './entrada-xml/entradaXmlRelatorioCustos';
import {
  ACAO_CONFERENCIA_OPCOES,
  BASE_CALCULO_MARGEM_OPCOES,
  CONFERENCIA_STATUS_META,
  aplicarMultiplicadorPackAoItem,
  aplicarOverridesPackNoPreview,
  calcularConferenciaItem,
  calcularResumoConferencia,
  detectarDivergencias,
  formatarOpcaoProduto,
  formatarValorFiscal,
  montarConferenciaState,
  normalizarProdutoPreview,
  normalizarNumeroConferencia,
  obterConfiguracaoPackItem,
  obterCustoBasePreviewItem,
  obterCustoAquisicaoItem,
  obterDraftConferenciaItem,
} from './entrada-xml/entradaXmlUtils';

const EntradaXML = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const autoOpenNotaIdRef = useRef(null);
  const [notasEntrada, setNotasEntrada] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
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
  
  // Estados para upload em lote
  const [uploadingLote, setUploadingLote] = useState(false);
  const [mostrarModalLote, setMostrarModalLote] = useState(false);
  const [resultadoLote, setResultadoLote] = useState(null);
  
  // Estados para historico de precos
  const [mostrarHistoricoPrecos, setMostrarHistoricoPrecos] = useState(false);
  const [historicoPrecos, setHistoricoPrecos] = useState([]);
  const [produtoHistorico, setProdutoHistorico] = useState(null);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  
  // Estados para revisao de precos
  const [mostrarRevisaoPrecos, setMostrarRevisaoPrecos] = useState(false);
  const [previewProcessamento, setPreviewProcessamento] = useState(null);
  const [custosAjustados, setCustosAjustados] = useState({});
  const [inputsRevisaoCustos, setInputsRevisaoCustos] = useState({});
  const [precosAjustados, setPrecosAjustados] = useState({});
  const [inputsRevisaoPrecos, setInputsRevisaoPrecos] = useState({});
  const [filtroCusto, setFiltroCusto] = useState('todos'); // 'todos', 'aumentou', 'diminuiu', 'igual'
  const [gerandoRelatorioCustos, setGerandoRelatorioCustos] = useState(false);
  const [baseCalculoMargem, setBaseCalculoMargem] = useState('nf');
  
  // Estados para rateio (APENAS informativo - estoque e UNIFICADO)
  const [tipoRateio, setTipoRateio] = useState('loja'); // 'online', 'loja', 'parcial'
  const [quantidadesOnline, setQuantidadesOnline] = useState({}); // {item_id: quantidade_online}
  const [multiplicadoresPack, setMultiplicadoresPack] = useState({}); // {item_id: multiplicador} para override manual
  
  // Estados para criar produto
  const [mostrarModalCriarProduto, setMostrarModalCriarProduto] = useState(false);
  const [itemSelecionadoParaCriar, setItemSelecionadoParaCriar] = useState(null);
  const [sugestaoSku, setSugestaoSku] = useState(null);
  const [carregandoSugestao, setCarregandoSugestao] = useState(false);
  const [formProduto, setFormProduto] = useState({
    sku: '',
    nome: '',
    descricao: '',
    preco_custo: '',
    preco_venda: '',
    margem_lucro: '',
    estoque_minimo: 10,
    estoque_maximo: 100
  });
  
  // Estado para filtro de pesquisa de produtos (por item)
  const [filtroProduto, setFiltroProduto] = useState({});
  const [resultadosBuscaProduto, setResultadosBuscaProduto] = useState({});
  const [buscandoProduto, setBuscandoProduto] = useState({});
  const buscaProdutoTimersRef = useRef({});

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
    console.log('🔄 [EntradaXML] Componente montado, iniciando carregamento...');
    carregarDados();
  }, []);

  useEffect(() => {
    return () => {
      Object.values(buscaProdutoTimersRef.current).forEach((timerId) => {
        if (timerId) clearTimeout(timerId);
      });
      buscaProdutoTimersRef.current = {};
    };
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
    console.log('📊 [EntradaXML] Carregando dados...');
    try {
      const token = getAccessToken();
      console.log('🔑 [EntradaXML] Token obtido:', token ? 'SIM' : 'NAO');
      const headers = { Authorization: `Bearer ${token}` };

      console.log('🌐 [EntradaXML] Fazendo requisicoes para:', {
        notasEntrada: `/notas-entrada/`
      });

      const notasRes = await api.get(`/notas-entrada/`, { headers });

      console.log('✅ [EntradaXML] Dados carregados:', {
        notasEntrada: notasRes.data?.length || 0
      });

      setNotasEntrada(notasRes.data);
    } catch (error) {
      console.error('❌ [EntradaXML] ERRO ao carregar dados:');
      console.error('  - Mensagem:', error.message);
      console.error('  - Response:', error.response?.data);
      console.error('  - Status:', error.response?.status);
      console.error('  - Stack:', error.stack);
      toast.error(`Erro ao carregar dados: ${error.response?.data?.detail || error.message}`);
    }
  };

  const buscarProdutosParaVinculo = async (itemId, termo) => {
    const textoBusca = (termo || '').trim();

    if (textoBusca.length < 2) {
      setResultadosBuscaProduto(prev => ({ ...prev, [itemId]: [] }));
      setBuscandoProduto(prev => ({ ...prev, [itemId]: false }));
      return;
    }

    setBuscandoProduto(prev => ({ ...prev, [itemId]: true }));

    try {
      const palavras = textoBusca.toLowerCase().split(/\s+/).filter(Boolean);

      // Faz uma chamada por palavra (até 4 palavras, as mais longas primeiro).
      // Resultado é a UNIÃO de todos — garante que o produto apareça desde que
      // qualquer uma das palavras o encontre no servidor (ex: "bob" traz todos
      // os produtos Bob mesmo que "filhote" retorne centenas de outros produtos).
      const palavrasServidor = [...palavras]
        .sort((a, b) => b.length - a.length)
        .slice(0, 4);

      const promises = [];
      palavrasServidor.forEach((palavra) => {
        const params = { busca: palavra, ativo: null, page: 1, page_size: 300 };
        promises.push(api.get('/produtos/', { params }));
        promises.push(api.get('/produtos/', { params: { ...params, tipo_produto: 'VARIACAO' } }));
      });

      const respostas = await Promise.all(promises);

      // UNIÃO: junta tudo em um mapa por ID (sem duplicatas)
      const mapaPorId = new Map();
      respostas.forEach((res) => {
        (res.data?.items || []).forEach((p) => mapaPorId.set(p.id, p));
      });

      // Filtro client-side: TODAS as palavras devem estar no produto (qualquer ordem)
      const encontrados = Array.from(mapaPorId.values()).filter((p) => {
        const campos = [
          p.nome?.toLowerCase() || '',
          p.codigo?.toLowerCase() || '',
          p.codigo_barras?.toLowerCase() || '',
          p.descricao?.toLowerCase() || ''
        ].join(' ');
        return palavras.every((palavra) => campos.includes(palavra));
      });

      // Ordena por relevância:
      // 1. Ativos primeiro
      // 2. Quantas palavras aparecem especificamente no NOME (mais = mais próximo)
      // 3. Alfabético
      encontrados.sort((a, b) => {
        if (a.ativo !== b.ativo) return a.ativo ? -1 : 1;
        const na = (a.nome || '').toLowerCase();
        const nb = (b.nome || '').toLowerCase();
        const scoreA = palavras.filter((w) => na.includes(w)).length;
        const scoreB = palavras.filter((w) => nb.includes(w)).length;
        if (scoreA !== scoreB) return scoreB - scoreA;
        return na.localeCompare(nb);
      });

      setResultadosBuscaProduto(prev => ({ ...prev, [itemId]: encontrados.slice(0, 60) }));
    } catch (error) {
      console.error('Erro ao buscar produtos para vinculo:', error);
      setResultadosBuscaProduto(prev => ({ ...prev, [itemId]: [] }));
    } finally {
      setBuscandoProduto(prev => ({ ...prev, [itemId]: false }));
    }
  };

  const atualizarFiltroProduto = (itemId, valor) => {
    setFiltroProduto(prev => ({ ...prev, [itemId]: valor }));

    if (buscaProdutoTimersRef.current[itemId]) {
      clearTimeout(buscaProdutoTimersRef.current[itemId]);
    }

    if ((valor || '').trim().length < 2) {
      setResultadosBuscaProduto(prev => ({ ...prev, [itemId]: [] }));
      setBuscandoProduto(prev => ({ ...prev, [itemId]: false }));
      return;
    }

    buscaProdutoTimersRef.current[itemId] = setTimeout(() => {
      buscarProdutosParaVinculo(itemId, valor);
    }, 250);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    console.log('📤 [EntradaXML] Upload iniciado');
    console.log('  - Arquivo selecionado:', file?.name);
    console.log('  - Tamanho:', file?.size, 'bytes');
    console.log('  - Tipo:', file?.type);
    
    if (!file) {
      console.warn('⚠️ [EntradaXML] Nenhum arquivo selecionado');
      return;
    }

    if (!file.name.toLowerCase().endsWith('.xml')) {
      console.error('❌ [EntradaXML] Arquivo nao é XML:', file.name);
      toast.error('❌ Por favor, selecione um arquivo XML');
      return;
    }

    setUploadingFile(true);
    const formData = new FormData();
    formData.append('file', file);

    console.log('🚀 [EntradaXML] Enviando arquivo para:', `/notas-entrada/upload`);
    console.log('📦 [EntradaXML] FormData preparado:', file.name, file.size, 'bytes');

    try {
      const response = await api.post(`/notas-entrada/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('✅ [EntradaXML] Upload bem-sucedido!');
      console.log('  - Response data:', response.data);

      const itensVinculados = response.data.produtos_vinculados || 0;
      const totalItens = response.data.itens_total || 0;

      console.log(`📊 [EntradaXML] Produtos vinculados: ${itensVinculados}/${totalItens}`);

      // Mensagem de fornecedor criado
      if (response.data.fornecedor_criado_automaticamente) {
        toast.success(
          `🏢 Novo fornecedor cadastrado: ${response.data.fornecedor}`,
          { duration: 4000 }
        );
      }

      // Mensagem de produtos reativados
      if (response.data.produtos_reativados > 0) {
        toast.success(
          `♻️ ${response.data.produtos_reativados} produto(s) inativo(s) reativado(s) automaticamente`,
          { duration: 4000 }
        );
      }

      toast.success(
        `✅ NF-e ${response.data.numero_nota} processada! ${itensVinculados}/${totalItens} produtos vinculados automaticamente`,
        { duration: 5000 }
      );
      
      carregarDados();
      event.target.value = ''; // Limpar input
    } catch (error) {
      console.error('❌ [EntradaXML] ERRO no upload:');
      console.error('  - Mensagem:', error.message);
      console.error('  - Response data:', error.response?.data);
      console.error('  - Status:', error.response?.status);
      console.error('  - Headers:', error.response?.headers);
      console.error('  - Stack completo:', error.stack);
      
      const errorMsg = error.response?.data?.detail || error.message || 'Erro ao processar XML da NF-e';
      console.error('  - Mensagem para usuario:', errorMsg);
      
      toast.error(`❌ ${errorMsg}`);
    } finally {
      setUploadingFile(false);
      console.log('🏁 [EntradaXML] Upload finalizado');
    }
  };

  const handleMultipleFilesUpload = async (event) => {
    const files = Array.from(event.target.files);
    console.log('📦 [EntradaXML] Upload em lote iniciado -', files.length, 'arquivos');
    
    if (files.length === 0) {
      console.warn('⚠️ [EntradaXML] Nenhum arquivo selecionado');
      return;
    }

    // Validar se todos são XML
    const invalidFiles = files.filter(f => !f.name.toLowerCase().endsWith('.xml'));
    if (invalidFiles.length > 0) {
      toast.error(`❌ ${invalidFiles.length} arquivo(s) nao são XML: ${invalidFiles.map(f => f.name).join(', ')}`);
      return;
    }

    setUploadingLote(true);
    setMostrarModalLote(true);
    setResultadoLote(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    console.log('🚀 [EntradaXML] Enviando', files.length, 'arquivos para:', `/notas-entrada/upload-lote`);

    try {
            const response = await api.post(`/notas-entrada/upload-lote`, formData);

      console.log('✅ [EntradaXML] Upload em lote bem-sucedido!');
      console.log('  - Response:', response.data);

      setResultadoLote(response.data);
      
      if (response.data.sucessos > 0) {
        toast.success(
          `✅ ${response.data.sucessos}/${response.data.total_arquivos} nota(s) processada(s) com sucesso!`,
          { duration: 5000 }
        );
      }
      
      if (response.data.erros > 0) {
        toast.error(
          `⚠️ ${response.data.erros}/${response.data.total_arquivos} nota(s) com erro`,
          { duration: 5000 }
        );
      }
      
      carregarDados();
      event.target.value = ''; // Limpar input
    } catch (error) {
      console.error('❌ [EntradaXML] ERRO no upload em lote:', error);
      toast.error(`❌ Erro ao processar lote: ${error.response?.data?.detail || error.message}`);
      setMostrarModalLote(false);
    } finally {
      setUploadingLote(false);
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

  const vincularProduto = async (notaId, itemId, produtoId) => {
    try {
      await api.post(
        `/notas-entrada/${notaId}/itens/${itemId}/vincular?produto_id=${Number.parseInt(produtoId)}`
      );
      
      toast.success('✅ Produto vinculado com sucesso!');
      
      // Recarregar detalhes
      const response = await api.get(`/notas-entrada/${notaId}`);
      aplicarNotaSelecionada(response.data);
    } catch (error) {
      console.error('❌ Erro ao vincular produto:', error);
      toast.error(error.response?.data?.detail || 'Erro ao vincular produto');
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
      console.error('❌ Erro ao salvar tipo de rateio:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar tipo de rateio');
    }
  };

  const salvarQuantidadeOnlineItem = async (notaId, itemId, quantidadeOnline) => {
    try {
      const response = await api.post(`/notas-entrada/${notaId}/itens/${itemId}/rateio`, {
        quantidade_online: Number.parseFloat(quantidadeOnline) || 0  // Permitir 0
      });
      
      toast.success('📊 Quantidade online configurada!');
      
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
      console.error('❌ Erro ao salvar quantidade online:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar');
    }
  };

  const processarNota = async (notaId) => {
    try {
      if (notaSelecionada?.id === notaId) {
        const conferenciaSalva = await salvarConferenciaAtual({ silencioso: true });
        if (!conferenciaSalva) {
          return;
        }
      }

      const response = await api.get(
        `/notas-entrada/${notaId}/preview-processamento`
      );

      const previewComOverrides = aplicarOverridesPackNoPreview(response.data, multiplicadoresPack);

      setBaseCalculoMargem('nf');
      setPreviewProcessamento(previewComOverrides);
      setMostrarRevisaoPrecos(true);
      
                      // FECHAR o modal de detalhes quando abrir o de revisão
      setMostrarDetalhes(false);
      
      // Inicializar precos ajustados com valores atuais (adaptar para nova estrutura)
      const custosIniciais = {};
      const inputsCustosIniciais = {};
      const precosIniciais = {};
      const inputsIniciais = {};
      previewComOverrides.itens.forEach(item => {
        const itemId = item.item_id ?? item.id;
        const custoBase = obterCustoBasePreviewItem(item);
        const custoExistente = Number(custosAjustados[itemId] ?? custosAjustados[String(itemId)]);
        const custoInicial = Number.isFinite(custoExistente) && custoExistente > 0
          ? custoExistente
          : custoBase;

        custosIniciais[itemId] = custoInicial;
        inputsCustosIniciais[itemId] = formatBRL(custoInicial);

        if (item.produto_vinculado) {
          const margemProjetada = Number(
            item.produto_vinculado.margem_projetada_custo_novo ??
            calcularMargem(item.produto_vinculado.preco_venda_atual, custoInicial)
          );
          precosIniciais[item.produto_vinculado.produto_id] = {
            preco_venda: item.produto_vinculado.preco_venda_atual,
            margem: margemProjetada
          };
          inputsIniciais[item.produto_vinculado.produto_id] = {
            preco_venda: formatBRL(item.produto_vinculado.preco_venda_atual),
            margem: formatBRL(margemProjetada),
          };
        }
      });
      setCustosAjustados(custosIniciais);
      setInputsRevisaoCustos(inputsCustosIniciais);
      setPrecosAjustados(precosIniciais);
      setInputsRevisaoPrecos(inputsIniciais);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao carregar preview');
    }
  };

  // Alias para melhor semântica
  const carregarPreviewProcessamento = processarNota;

  const confirmarProcessamento = async () => {
    setLoading(true);
    try {
      // Atualizar precos se houver alterações (adaptar para nova estrutura)
      const precosParaAtualizar = [];
      Object.entries(precosAjustados).forEach(([produtoId, dados]) => {
        const itemOriginal = previewProcessamento.itens.find(i => 
          i.produto_vinculado && i.produto_vinculado.produto_id == produtoId
        );
        if (itemOriginal && itemOriginal.produto_vinculado && 
            dados.preco_venda !== itemOriginal.produto_vinculado.preco_venda_atual) {
          precosParaAtualizar.push({
            produto_id: Number.parseInt(produtoId),
            preco_venda: dados.preco_venda
          });
        }
      });
      
      if (precosParaAtualizar.length > 0) {
        await api.post(
          `/notas-entrada/${previewProcessamento.nota_id}/atualizar-precos`,
          precosParaAtualizar
        );
      }
      
      // Processar a nota (enviar overrides de multiplicador manual quando existirem)
      const overridesNaoDefault = Object.fromEntries(
        Object.entries(multiplicadoresPack).flatMap(([itemId, valor]) => {
          const multiplicador = Number.parseInt(valor, 10);

          if (!Number.isInteger(multiplicador) || multiplicador < 1 || multiplicador > 200) {
            return [];
          }

          return [[itemId, multiplicador]];
        })
      );
      const custosOverride = Object.fromEntries(
        (previewProcessamento.itens || []).flatMap((item) => {
          const itemId = item.item_id ?? item.id;
          const custoBase = obterCustoBasePreviewItem(item);
          const custoSistema = Number(custosAjustados[itemId] ?? custosAjustados[String(itemId)]);

          if (!Number.isFinite(custoSistema) || custoSistema <= 0) {
            return [];
          }

          if (Math.abs(custoSistema - custoBase) < 0.0001) {
            return [];
          }

          return [[itemId, Number(custoSistema.toFixed(4))]];
        })
      );
      const response = await api.post(
        `/notas-entrada/${previewProcessamento.nota_id}/processar`,
        {
          ...(Object.keys(overridesNaoDefault).length > 0 ? { multiplicadores_override: overridesNaoDefault } : {}),
          ...(Object.keys(custosOverride).length > 0 ? { custos_override: custosOverride } : {}),
        }
      );

      toast.success(
        `✅ Nota processada! ${response.data.itens_processados} itens lançados no estoque`,
        { duration: 5000 }
      );
      
      setMostrarDetalhes(false);
      setNotaSelecionada(null);
      setMostrarRevisaoPrecos(false);
      setPreviewProcessamento(null);
      setBaseCalculoMargem('nf');
      setCustosAjustados({});
      setInputsRevisaoCustos({});
      setInputsRevisaoPrecos({});
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao processar nota');
    } finally {
      setLoading(false);
    }
  };

  const calcularPrecoVenda = (custoNovo, margemDesejada) => {
    // Margem = (Preço Venda - Custo) / Preço Venda * 100
    // Preço Venda = Custo / (1 - Margem/100)
    if (margemDesejada >= 100) return custoNovo * 2;
    return custoNovo / (1 - margemDesejada / 100);
  };

  const parseNumeroFlexivel = (valor) => {
    if (typeof valor === 'number') {
      return Number.isFinite(valor) ? valor : 0;
    }

    let texto = String(valor || '').trim();
    if (!texto) return 0;

    texto = texto.replaceAll(/\s+/g, '');
    texto = texto.replaceAll(/[^\d,.-]/g, '');

    if (texto.includes(',') && texto.includes('.')) {
      if (texto.lastIndexOf(',') > texto.lastIndexOf('.')) {
        texto = texto.replaceAll('.', '').replace(',', '.');
      } else {
        texto = texto.replaceAll(',', '');
      }
    } else if (texto.includes(',')) {
      texto = texto.replaceAll('.', '').replace(',', '.');
    }

    const numero = Number.parseFloat(texto);
    return Number.isFinite(numero) ? numero : 0;
  };

  const calcularMargem = (precoVenda, custoNovo) => {
    // Margem = (Preço Venda - Custo) / Preço Venda * 100
    if (precoVenda <= 0) return 0;
    return ((precoVenda - custoNovo) / precoVenda) * 100;
  };

  const atualizarPrecoVenda = (produtoId, novoPrecoEntrada, custoNovo) => {
    const novoPreco = parseNumeroFlexivel(novoPrecoEntrada);
    const novaMargem = calcularMargem(novoPreco, custoNovo);
    setPrecosAjustados(prev => ({
      ...prev,
      [produtoId]: {
        preco_venda: novoPreco,
        margem: novaMargem
      }
    }));
    setInputsRevisaoPrecos(prev => ({
      ...prev,
      [produtoId]: {
        preco_venda: String(novoPrecoEntrada ?? ''),
        margem: formatBRL(novaMargem),
      }
    }));
  };

  const atualizarMargem = (produtoId, novaMargemEntrada, custoNovo) => {
    const novaMargem = parseNumeroFlexivel(novaMargemEntrada);
    const novoPreco = calcularPrecoVenda(custoNovo, novaMargem);
    setPrecosAjustados(prev => ({
      ...prev,
      [produtoId]: {
        preco_venda: novoPreco,
        margem: novaMargem
      }
    }));
    setInputsRevisaoPrecos(prev => ({
      ...prev,
      [produtoId]: {
        preco_venda: formatBRL(novoPreco),
        margem: String(novaMargemEntrada ?? ''),
      }
    }));
  };

  const normalizarCamposRevisaoPrecos = (produtoId) => {
    const dados = precosAjustados[produtoId];
    if (!dados) return;

    setInputsRevisaoPrecos(prev => ({
      ...prev,
      [produtoId]: {
        preco_venda: formatBRL(dados.preco_venda),
        margem: formatBRL(dados.margem),
      }
    }));
  };

  const atualizarCustoSistema = (item, novoCustoEntrada) => {
    const itemId = item?.item_id ?? item?.id;
    const custoBase = obterCustoBasePreviewItem(item);
    const custoDigitado = parseNumeroFlexivel(novoCustoEntrada);
    const custoAplicado = custoDigitado > 0 ? custoDigitado : 0;

    setCustosAjustados((prev) => ({
      ...prev,
      [itemId]: custoAplicado,
    }));
    setInputsRevisaoCustos((prev) => ({
      ...prev,
      [itemId]: String(novoCustoEntrada ?? ''),
    }));

    const produto = normalizarProdutoPreview(item);
    if (!produto?.produto_id) {
      return;
    }

    const precoAtual = Number(
      precosAjustados[produto.produto_id]?.preco_venda ??
      produto.preco_venda_atual ??
      0
    );
    const baseMargem = obterInfoBaseCalculoMargem({
      custoNF: custoBase,
      custoSistema: custoAplicado || custoBase,
    });
    const margemAtualizada = calcularMargem(precoAtual, baseMargem.valor);

    setPrecosAjustados((prev) => ({
      ...prev,
      [produto.produto_id]: {
        preco_venda: precoAtual,
        margem: margemAtualizada,
      }
    }));
    setInputsRevisaoPrecos((prev) => ({
      ...prev,
      [produto.produto_id]: {
        preco_venda: prev?.[produto.produto_id]?.preco_venda ?? formatBRL(precoAtual),
        margem: formatBRL(margemAtualizada),
      }
    }));
  };

  const normalizarCamposRevisaoCustos = (item) => {
    const itemId = item?.item_id ?? item?.id;
    const custoBase = obterCustoBasePreviewItem(item);
    const custoAtual = Number(custosAjustados[itemId] ?? custosAjustados[String(itemId)]);
    const custoNormalizado = Number.isFinite(custoAtual) && custoAtual > 0 ? custoAtual : custoBase;

    setCustosAjustados((prev) => ({
      ...prev,
      [itemId]: custoNormalizado,
    }));
    setInputsRevisaoCustos((prev) => ({
      ...prev,
      [itemId]: formatBRL(custoNormalizado),
    }));

    const produto = normalizarProdutoPreview(item);
    if (!produto?.produto_id) {
      return;
    }

    const precoAtual = Number(
      precosAjustados[produto.produto_id]?.preco_venda ??
      produto.preco_venda_atual ??
      0
    );
    const baseMargem = obterInfoBaseCalculoMargem({
      custoNF: custoBase,
      custoSistema: custoNormalizado,
    });
    const margemAtualizada = calcularMargem(precoAtual, baseMargem.valor);
    setPrecosAjustados((prev) => ({
      ...prev,
      [produto.produto_id]: {
        preco_venda: precoAtual,
        margem: margemAtualizada,
      }
    }));
    setInputsRevisaoPrecos((prev) => ({
      ...prev,
      [produto.produto_id]: {
        preco_venda: prev?.[produto.produto_id]?.preco_venda ?? formatBRL(precoAtual),
        margem: formatBRL(margemAtualizada),
      }
    }));
  };

  const obterCustoSistemaItem = (item) => {
    const itemId = item?.item_id ?? item?.id;
    const overrideRaw = custosAjustados[itemId] ?? custosAjustados[String(itemId)];
    const override = Number(overrideRaw);
    if (Number.isFinite(override) && override > 0) {
      return override;
    }
    return obterCustoBasePreviewItem(item);
  };

  const obterInfoBaseCalculoMargem = ({ custoNF = 0, custoSistema = 0 }) => {
    const custoNFNormalizado = Number(custoNF || 0);
    const custoSistemaNormalizado = Number(custoSistema || 0);

    if (baseCalculoMargem === 'sistema') {
      return {
        value: 'sistema',
        label: 'Custo no sistema',
        valor: custoSistemaNormalizado > 0 ? custoSistemaNormalizado : custoNFNormalizado,
        fallback: !(custoSistemaNormalizado > 0),
        descricao: custoSistemaNormalizado > 0
          ? 'Calculando sobre o custo informado no sistema.'
          : 'Sem custo informado no sistema; usando o custo da NF.',
      };
    }

    return {
      value: 'nf',
      label: 'Custo da NF',
      valor: custoNFNormalizado,
      fallback: false,
      descricao: 'Calculando sobre o custo fiscal da NF.',
    };
  };

  const obterResumoCustoItem = (item) => {
    const produto = normalizarProdutoPreview(item);
    const custoAnterior = Number(produto.custo_anterior || 0);
    const custoNF = obterCustoBasePreviewItem(item);
    const custoSistema = obterCustoSistemaItem(item);
    const precoVendaAtual = Number(produto.preco_venda_atual || 0);
    const baseMargem = obterInfoBaseCalculoMargem({ custoNF, custoSistema });
    const variacaoCustoPercentual = custoAnterior > 0
      ? Number((((custoSistema - custoAnterior) / custoAnterior) * 100).toFixed(2))
      : 0;
    const margemReferencia = Number(
      produto.margem_atual ??
      calcularMargem(precoVendaAtual, custoAnterior)
    );
    const margemProjetada = calcularMargem(precoVendaAtual, baseMargem.valor);

    return {
      produto,
      custoAnterior,
      custoNF,
      custoSistema,
      baseMargem,
      custoManual: Math.abs(custoSistema - custoNF) > 0.0001,
      variacaoCustoPercentual,
      precoVendaAtual,
      margemReferencia,
      margemProjetada,
    };
  };

  useEffect(() => {
    if (!mostrarRevisaoPrecos || !previewProcessamento?.itens?.length) {
      return;
    }

    setPrecosAjustados((prev) => {
      let mudou = false;
      const proximo = { ...prev };

      previewProcessamento.itens.forEach((item) => {
        const produto = normalizarProdutoPreview(item);
        if (!produto?.produto_id) return;

        const resumoCusto = obterResumoCustoItem(item);
        const precoAtual = Number(
          prev[produto.produto_id]?.preco_venda ??
          produto.preco_venda_atual ??
          0
        );
        const margemAtualizada = calcularMargem(precoAtual, resumoCusto.baseMargem.valor);
        const atual = prev[produto.produto_id];

        if (
          !atual ||
          Math.abs(Number(atual.preco_venda || 0) - precoAtual) > 0.0001 ||
          Math.abs(Number(atual.margem || 0) - margemAtualizada) > 0.0001
        ) {
          proximo[produto.produto_id] = {
            preco_venda: precoAtual,
            margem: margemAtualizada,
          };
          mudou = true;
        }
      });

      return mudou ? proximo : prev;
    });

    setInputsRevisaoPrecos((prev) => {
      let mudou = false;
      const proximo = { ...prev };

      previewProcessamento.itens.forEach((item) => {
        const produto = normalizarProdutoPreview(item);
        if (!produto?.produto_id) return;

        const resumoCusto = obterResumoCustoItem(item);
        const precoAtual = Number(
          precosAjustados[produto.produto_id]?.preco_venda ??
          produto.preco_venda_atual ??
          0
        );
        const margemAtualizada = calcularMargem(precoAtual, resumoCusto.baseMargem.valor);
        const precoTextoAtual = prev?.[produto.produto_id]?.preco_venda ?? formatBRL(precoAtual);
        const margemTextoAtual = formatBRL(margemAtualizada);

        if (
          !prev?.[produto.produto_id] ||
          prev[produto.produto_id].preco_venda !== precoTextoAtual ||
          prev[produto.produto_id].margem !== margemTextoAtual
        ) {
          proximo[produto.produto_id] = {
            preco_venda: precoTextoAtual,
            margem: margemTextoAtual,
          };
          mudou = true;
        }
      });

      return mudou ? proximo : prev;
    });
  }, [baseCalculoMargem, mostrarRevisaoPrecos, previewProcessamento]);

  const exportarRelatorioCustosMaioresCSV = () => exportarRelatorioCustosMaioresCSVArquivo({
    api,
    obterResumoCustoItem,
    previewProcessamento,
    setGerandoRelatorioCustos,
    toast,
  });

  const exportarRelatorioCustosMaioresPDF = () => exportarRelatorioCustosMaioresPDFArquivo({
    api,
    obterResumoCustoItem,
    previewProcessamento,
    setGerandoRelatorioCustos,
    toast,
  });

  const excluirNota = async (notaId, numeroNota) => {
    if (!confirm(`Tem certeza que deseja excluir a nota ${numeroNota}?`)) {
      return;
    }

    setLoading(true);
    try {
            await api.delete(`/notas-entrada/${notaId}`);

      toast.success('🗑️ Nota excluída com sucesso!');
      
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
    if (!confirm(`⚠️ Tem certeza que deseja REVERTER a entrada da nota ${numeroNota}?\n\nIsso ira:\n• Remover as quantidades do estoque\n• Excluir os lotes criados\n• Estornar as contas a pagar lançadas\n• Restaurar o status da nota para pendente`)) {
      return;
    }

    setLoading(true);
    try {
            const response = await api.post(
        `/notas-entrada/${notaId}/reverter`,
        {}
      );

      toast.success(
        `✅ Entrada revertida! ${response.data.itens_revertidos} produtos ajustados`,
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

  const desvincularProduto = async (notaId, itemId) => {
    try {
      await api.post(`/notas-entrada/${notaId}/itens/${itemId}/desvincular`);
      
      toast.success('✅ Produto desvinculado!');
      
      // Recarregar detalhes da nota
      const response = await api.get(`/notas-entrada/${notaId}`);
      aplicarNotaSelecionada(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao desvincular produto');
    }
  };

  const abrirModalCriarProduto = async (item) => {
    const itemAjustado = aplicarMultiplicadorPackAoItem(item, multiplicadoresPack);

    setItemSelecionadoParaCriar(itemAjustado);
    setMostrarModalCriarProduto(true);
    setCarregandoSugestao(true);
    
    // Resetar formulario
    setFormProduto({
      sku: '',
      nome: '',
      descricao: '',
      preco_custo: '',
      preco_venda: '',
      margem_lucro: '',
      estoque_minimo: 10,
      estoque_maximo: 100
    });
    
    try {
            const response = await api.get(
        `/notas-entrada/${notaSelecionada.id}/itens/${itemAjustado.id}/sugerir-sku`
      );
      
      setSugestaoSku(response.data);
      
      // Determinar qual SKU usar
      let skuParaUsar = response.data.sku_proposto || itemAjustado.codigo_produto || 'PROD-' + itemAjustado.id;
      
      // Se o SKU ja existe, usar a primeira sugestao alternativa (a recomendada com ⭐)
      if (response.data.ja_existe && response.data.sugestoes && response.data.sugestoes.length > 0) {
        const sugestaoRecomendada = response.data.sugestoes.find(s => s.padrao) || response.data.sugestoes[0];
        skuParaUsar = sugestaoRecomendada.sku;
      }
      
      // Preencher formulario com dados do item
      const custoBase = obterCustoAquisicaoItem(itemAjustado);
      setFormProduto({
        sku: skuParaUsar,
        nome: itemAjustado.descricao || itemAjustado.descricao_produto || 'Produto sem nome',
        descricao: itemAjustado.descricao || itemAjustado.descricao_produto || '',
        preco_custo: custoBase.toString(),
        preco_venda: (custoBase * 1.5).toFixed(2),
        margem_lucro: '50',
        estoque_minimo: 10,
        estoque_maximo: 100
      });
      
      console.log('✅ Formulário preenchido:', {
        sku: skuParaUsar,
        nome: itemAjustado.descricao,
        preco_custo: custoBase
      });
      
    } catch (error) {
      toast.error('Erro ao buscar sugestões de SKU');
      console.error('Erro ao buscar SKU:', error);
      
      // Preencher mesmo com erro
      const custoBase = obterCustoAquisicaoItem(itemAjustado);
      setFormProduto({
        sku: itemAjustado.codigo_produto || 'PROD-' + itemAjustado.id,
        nome: itemAjustado.descricao || 'Produto sem nome',
        descricao: itemAjustado.descricao || '',
        preco_custo: custoBase.toString(),
        preco_venda: (custoBase * 1.5).toFixed(2),
        margem_lucro: '50',
        estoque_minimo: 10,
        estoque_maximo: 100
      });
    } finally {
      setCarregandoSugestao(false);
    }
  };

  const criarProdutoNovo = async () => {
    try {
      setLoading(true);
            // Preparar dados convertendo strings para números
      const dadosProduto = {
        ...formProduto,
        preco_custo: Number.parseFloat(formProduto.preco_custo) || 0,
        preco_venda: Number.parseFloat(formProduto.preco_venda) || 0,
        margem_lucro: Number.parseFloat(formProduto.margem_lucro) || 0,
        estoque_minimo: Number.parseInt(formProduto.estoque_minimo) || 10,
        estoque_maximo: Number.parseInt(formProduto.estoque_maximo) || 100
      };
      
      const response = await api.post(
        `/notas-entrada/${notaSelecionada.id}/itens/${itemSelecionadoParaCriar.id}/criar-produto`,
        dadosProduto
      );
      
      toast.success(
        response.data.message || `✅ Produto ${response.data.produto.codigo} criado e vinculado!`
      );
      
      // Fechar modal
      setMostrarModalCriarProduto(false);
      setItemSelecionadoParaCriar(null);
      setSugestaoSku(null);
      
      // Recarregar dados
      await carregarDados();
      
      // Recarregar detalhes da nota
      const notaResponse = await api.get(
        `/notas-entrada/${notaSelecionada.id}`
      );
      aplicarNotaSelecionada(notaResponse.data);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao criar produto');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const criarTodosProdutosNaoVinculados = async () => {
    const itensNaoVinculados = notaSelecionada.itens.filter(item => !item.produto_id);
    
    if (itensNaoVinculados.length === 0) {
      toast.success('Todos os produtos ja estão vinculados!');
      return;
    }
    
    const confirmacao = globalThis.confirm(
      `Criar ${itensNaoVinculados.length} produto(s) automaticamente?\n\n` +
      `Padrões aplicados:\n` +
      `• Estoque mínimo: 10\n` +
      `• Estoque máximo: 100\n` +
      `• Margem de lucro: 50%\n\n` +
      `Você poderá editar os produtos depois no cadastro.`
    );
    
    if (!confirmacao) return;
    
    try {
      setLoading(true);
      let sucessos = 0;
      let erros = 0;
      
      const loadingToast = toast.loading(`📦 Criando ${itensNaoVinculados.length} produtos...`);
      
      for (const item of itensNaoVinculados) {
        try {
          // Buscar SKU sugerido
          const skuResponse = await api.get(
            `/notas-entrada/${notaSelecionada.id}/itens/${item.id}/sugerir-sku`
          );
          
          let skuParaUsar = skuResponse.data.sku_proposto || item.codigo_produto || `PROD-${item.id}`;
          
          // Se ja existe, usar primeira sugestao alternativa
          if (skuResponse.data.ja_existe && skuResponse.data.sugestoes?.length > 0) {
            const sugestaoRecomendada = skuResponse.data.sugestoes.find(s => s.padrao) || skuResponse.data.sugestoes[0];
            skuParaUsar = sugestaoRecomendada.sku;
          }
          
          // Criar produto com padrões
          const custoBase = obterCustoAquisicaoItem(item);
          const dadosProduto = {
            sku: skuParaUsar,
            nome: item.descricao || 'Produto sem nome',
            descricao: item.descricao || '',
            preco_custo: custoBase,
            preco_venda: Number.parseFloat((custoBase * 1.5).toFixed(2)),
            margem_lucro: 50,
            estoque_minimo: 10,
            estoque_maximo: 100
          };
          
          await api.post(
            `/notas-entrada/${notaSelecionada.id}/itens/${item.id}/criar-produto`,
            dadosProduto
          );
          
          sucessos++;
        } catch (error) {
          console.error(`Erro ao criar produto do item ${item.id}:`, error);
          erros++;
        }
      }
      
      toast.dismiss(loadingToast);
      
      if (sucessos > 0) {
        toast.success(`✅ ${sucessos} produto(s) criado(s) com sucesso!`);
      }
      
      if (erros > 0) {
        toast.error(`❌ ${erros} erro(s) ao criar produtos`);
      }
      
      // Recarregar dados
      await carregarDados();
      
      // Recarregar detalhes da nota
      const notaResponse = await api.get(`/notas-entrada/${notaSelecionada.id}`);
      aplicarNotaSelecionada(notaResponse.data);
      
    } catch (error) {
      toast.error('Erro ao criar produtos em lote');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const calcularMargemLucro = (custo, venda) => {
    if (custo === 0) return 0;
    return ((venda - custo) / custo * 100).toFixed(2);
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
        onClose={() => {
          setMostrarModalCriarProduto(false);
          setItemSelecionadoParaCriar(null);
          setSugestaoSku(null);
        }}
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
        baseCalculoMargemOpcoes={BASE_CALCULO_MARGEM_OPCOES}
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
        onVoltar={() => {
          setMostrarRevisaoPrecos(false);
          setPreviewProcessamento(null);
          setInputsRevisaoPrecos({});
          setBaseCalculoMargem('nf');
          if (notaSelecionada) {
            setMostrarVisualizacao(true);
          }
        }}
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
        onClose={() => {
          setMostrarModalLote(false);
          setResultadoLote(null);
        }}
        resultadoLote={resultadoLote}
        uploadingLote={uploadingLote}
      />
    </div>
  );
};

export default EntradaXML;
