import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import api from '../api';
import { toast } from 'react-hot-toast';
import { formatBRL, formatMoneyBRL, formatPercent } from '../utils/formatters';
import { jsPDF } from 'jspdf';
import CardFiscal from './CardFiscal';
import TooltipComposicao from './TooltipComposicao';

function formatarChaveAcesso(valor) {
  return String(valor).replaceAll(/\D/g, '').slice(0, 44);
}

function montarNomeXml(dados) {
  const numero = String(dados?.numero_nf || '0').replaceAll(/\D/g, '');
  const serie = String(dados?.serie || '1').replaceAll(/\D/g, '');
  const chave = String(dados?.chave_acesso || '').replaceAll(/\D/g, '').slice(-8);
  return `nfe_${numero || '0'}_${serie || '1'}_${chave || 'xml'}.xml`;
}

function formatarOpcaoProduto(produto) {
  const sku = produto?.codigo || 'Sem SKU';
  const ean = produto?.codigo_barras || produto?.gtin_ean || produto?.gtin_ean_tributario || 'Sem EAN';
  const nome = produto?.nome || 'Produto sem nome';
  const estoque = produto?.estoque_atual || 0;
  return `${sku} | EAN: ${ean} | ${nome} (Est: ${estoque})`;
}

function formatarValorFiscal(valor, casas = 4) {
  return Number(valor || 0).toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function obterCustoAquisicaoItem(item) {
  return Number(
    item?.custo_aquisicao_unitario ??
    item?.custo_aquisicao_unitario_nf ??
    item?.composicao_custo?.custo_aquisicao_unitario ??
    item?.custo_unitario_efetivo ??
    item?.custo_unitario_efetivo_nf ??
    item?.valor_unitario ??
    0
  );
}

function normalizarMultiplicadorPack(valor, fallback = 1) {
  const parsed = Number.parseInt(valor, 10);

  if (!Number.isInteger(parsed)) {
    return fallback;
  }

  return Math.max(1, Math.min(200, parsed));
}

function obterChavePackItem(item) {
  return item?.id ?? item?.item_id ?? null;
}

function itemTemOverridePack(item, multiplicadoresOverride = {}) {
  const chaveItem = obterChavePackItem(item);

  if (chaveItem === null || chaveItem === undefined) {
    return false;
  }

  return (
    Object.prototype.hasOwnProperty.call(multiplicadoresOverride, chaveItem) ||
    Object.prototype.hasOwnProperty.call(multiplicadoresOverride, String(chaveItem))
  );
}

function obterConfiguracaoPackItem(item, multiplicadoresOverride = {}) {
  const chaveItem = obterChavePackItem(item);
  const multiplicadorDetectado = normalizarMultiplicadorPack(item?.pack_multiplicador_detectado, 1);
  const overrideManual = itemTemOverridePack(item, multiplicadoresOverride);
  const overrideRaw = overrideManual
    ? (multiplicadoresOverride[chaveItem] ?? multiplicadoresOverride[String(chaveItem)])
    : null;
  const multiplicador = overrideManual
    ? normalizarMultiplicadorPack(overrideRaw, multiplicadorDetectado)
    : multiplicadorDetectado;
  const sugestaoAutomaticaDiferenteDoPadrao = multiplicadorDetectado > 1;

  return {
    chaveItem,
    multiplicador,
    multiplicadorDetectado,
    overrideManual,
    packDetectadoAutomatico: Boolean(item?.pack_detectado_automatico || sugestaoAutomaticaDiferenteDoPadrao),
    sugestaoAutomaticaDiferenteDoPadrao,
    usandoSugestaoAutomatica: sugestaoAutomaticaDiferenteDoPadrao && !overrideManual,
  };
}

function ajustarComposicaoCustoParaMultiplicador(composicao, quantidadeBase, multiplicador) {
  if (!composicao) {
    return composicao;
  }

  const quantidadeEfetiva = Number(quantidadeBase || 0) * multiplicador;
  const componentesTotal = composicao.componentes_total || {};
  const valorUnitario = (valorTotal) => (quantidadeEfetiva > 0 ? Number(valorTotal || 0) / quantidadeEfetiva : 0);

  return {
    ...composicao,
    quantidade_efetiva: quantidadeEfetiva,
    custo_bruto_unitario: valorUnitario(componentesTotal.valor_produtos),
    custo_aquisicao_unitario: valorUnitario(composicao.custo_aquisicao_total),
    componentes_unitario: {
      ...(composicao.componentes_unitario || {}),
      valor_frete: valorUnitario(componentesTotal.valor_frete),
      valor_seguro: valorUnitario(componentesTotal.valor_seguro),
      valor_outras_despesas: valorUnitario(componentesTotal.valor_outras_despesas),
      valor_desconto: valorUnitario(componentesTotal.valor_desconto),
      valor_icms_st: valorUnitario(componentesTotal.valor_icms_st),
      valor_ipi: valorUnitario(componentesTotal.valor_ipi),
      valor_icms: valorUnitario(componentesTotal.valor_icms),
      valor_pis: valorUnitario(componentesTotal.valor_pis),
      valor_cofins: valorUnitario(componentesTotal.valor_cofins),
    },
  };
}

function aplicarMultiplicadorPackAoItem(item, multiplicadoresOverride = {}) {
  if (!item) {
    return item;
  }

  const configPack = obterConfiguracaoPackItem(item, multiplicadoresOverride);
  const quantidadeNF = Number(item.quantidade_nf ?? item.quantidade ?? 0);
  const quantidadeEfetiva = quantidadeNF * configPack.multiplicador;
  const custoTotal = Number(
    item.custo_aquisicao_total_nf ??
    item.custo_aquisicao_total ??
    item.composicao_custo?.custo_aquisicao_total ??
    item.valor_total_nf ??
    item.valor_total ??
    0,
  );
  const custoUnitarioFallback = Number(
    item.custo_aquisicao_unitario_nf ??
    item.custo_aquisicao_unitario ??
    item.composicao_custo?.custo_aquisicao_unitario ??
    item.custo_unitario_efetivo_nf ??
    item.custo_unitario_efetivo ??
    item.valor_unitario_nf ??
    item.valor_unitario ??
    0,
  );
  const custoUnitarioEfetivo = quantidadeEfetiva > 0
    ? (custoTotal / quantidadeEfetiva)
    : custoUnitarioFallback;

  let produtoVinculadoAjustado = item.produto_vinculado;
  if (item.produto_vinculado) {
    const custoAnterior = Number(item.produto_vinculado.custo_anterior || 0);
    const variacaoCusto = custoAnterior > 0
      ? ((custoUnitarioEfetivo - custoAnterior) / custoAnterior) * 100
      : 0;
    const precoVendaAtual = Number(item.produto_vinculado.preco_venda_atual || 0);
    const margemReferencia = precoVendaAtual > 0 && custoAnterior > 0
      ? ((precoVendaAtual - custoAnterior) / precoVendaAtual) * 100
      : 0;
    const margemProjetada = precoVendaAtual > 0
      ? ((precoVendaAtual - custoUnitarioEfetivo) / precoVendaAtual) * 100
      : 0;

    produtoVinculadoAjustado = {
      ...item.produto_vinculado,
      custo_novo: custoUnitarioEfetivo,
      variacao_custo_percentual: Number(variacaoCusto.toFixed(2)),
      margem_atual: Number(margemReferencia.toFixed(2)),
      margem_projetada_custo_novo: Number(margemProjetada.toFixed(2)),
    };
  }

  return {
    ...item,
    pack_multiplicador_usado: configPack.multiplicador,
    pack_override_manual: configPack.overrideManual,
    pack_usa_sugestao_automatica: configPack.usandoSugestaoAutomatica,
    pack_sugestao_destacada: configPack.sugestaoAutomaticaDiferenteDoPadrao,
    quantidade_efetiva_nf: quantidadeEfetiva,
    quantidade_efetiva: quantidadeEfetiva,
    custo_unitario_efetivo_nf: custoUnitarioEfetivo,
    custo_unitario_efetivo: custoUnitarioEfetivo,
    custo_aquisicao_unitario_nf: custoUnitarioEfetivo,
    custo_aquisicao_unitario: custoUnitarioEfetivo,
    composicao_custo: ajustarComposicaoCustoParaMultiplicador(
      item.composicao_custo,
      quantidadeNF,
      configPack.multiplicador,
    ),
    produto_vinculado: produtoVinculadoAjustado,
  };
}

function aplicarOverridesPackNoPreview(preview, multiplicadoresOverride = {}) {
  if (!preview || !Array.isArray(preview.itens)) {
    return preview;
  }

  return {
    ...preview,
    itens: preview.itens.map((item) => aplicarMultiplicadorPackAoItem(item, multiplicadoresOverride)),
  };
}

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
  const [precosAjustados, setPrecosAjustados] = useState({});
  const [inputsRevisaoPrecos, setInputsRevisaoPrecos] = useState({});
  const [filtroCusto, setFiltroCusto] = useState('todos'); // 'todos', 'aumentou', 'diminuiu', 'igual'
  const [gerandoRelatorioCustos, setGerandoRelatorioCustos] = useState(false);
  
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

  // Painel de busca SEFAZ embutido
  const [mostrarPainelSefaz, setMostrarPainelSefaz] = useState(false);
  const [mostrarConfigSefaz, setMostrarConfigSefaz] = useState(false);
  const [chaveSefaz, setChaveSefaz] = useState('');
  const [consultasSefaz, setConsultasSefaz] = useState([]);
  const [consultaExpandidaId, setConsultaExpandidaId] = useState(null);
  const [importandoConsultaId, setImportandoConsultaId] = useState(null);
  const [erroSefaz, setErroSefaz] = useState('');
  const [avisoConectorSefaz, setAvisoConectorSefaz] = useState('');
  const [loadingSefaz, setLoadingSefaz] = useState(false);
  const [configSefazLoading, setConfigSefazLoading] = useState(false);
  const [salvandoRotina, setSalvandoRotina] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [mensagemRotina, setMensagemRotina] = useState('');
  const [diagnosticando, setDiagnosticando] = useState(false);
  const [resultadoDiagnostico, setResultadoDiagnostico] = useState(null);
  const [nsuStatus, setNsuStatus] = useState(null);
  const [carregandoNsu, setCarregandoNsu] = useState(false);
  const [resetandoNsu, setResetandoNsu] = useState(false);
  const [cfgSefaz, setCfgSefaz] = useState({
    enabled: false, modo: 'mock', ambiente: 'homologacao', uf: 'SP', cnpj: '',
    importacao_automatica: false, importacao_intervalo_min: 60, cert_ok: false,
    ultimo_sync_status: 'nunca', ultimo_sync_mensagem: 'Ainda nao sincronizado.',
    ultimo_sync_at: null, ultimo_sync_documentos: 0,
  });

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
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
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

  const abrirDetalhes = async (notaId) => {
    try {
            const response = await api.get(`/notas-entrada/${notaId}`);
      // Ordenar itens por ID para manter ordem consistente
      if (response.data.itens) {
        response.data.itens.sort((a, b) => a.id - b.id);
      }
      setNotaSelecionada(response.data);
      setMostrarDetalhes(true);
      setMultiplicadoresPack({}); // limpar overrides manuais ao abrir nova nota
      
      // Sincronizar estado de rateio
      setTipoRateio(response.data.tipo_rateio || 'loja');
    } catch (error) {
      toast.error('Erro ao carregar detalhes da nota');
    }
  };

  const abrirVisualizacao = async (notaId) => {
    try {
            const response = await api.get(`/notas-entrada/${notaId}`);
      setNotaSelecionada(response.data);
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
      // Ordenar itens por ID para manter ordem consistente
      if (response.data.itens) {
        response.data.itens.sort((a, b) => a.id - b.id);
      }
      setNotaSelecionada(response.data);
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
      setNotaSelecionada(response.data);
      
      // Atualizar estado local para selecao visual
      setTipoRateio(tipo);
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
    // Primeiro, buscar preview
    try {
      const response = await api.get(
        `/notas-entrada/${notaId}/preview-processamento`
      );

      const previewComOverrides = aplicarOverridesPackNoPreview(response.data, multiplicadoresPack);

      setPreviewProcessamento(previewComOverrides);
      setMostrarRevisaoPrecos(true);
      
                      // FECHAR o modal de detalhes quando abrir o de revisão
      setMostrarDetalhes(false);
      
      // Inicializar precos ajustados com valores atuais (adaptar para nova estrutura)
      const precosIniciais = {};
      const inputsIniciais = {};
      previewComOverrides.itens.forEach(item => {
        if (item.produto_vinculado) {
          const margemProjetada = Number(
            item.produto_vinculado.margem_projetada_custo_novo ??
            calcularMargem(item.produto_vinculado.preco_venda_atual, item.produto_vinculado.custo_novo)
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
      const response = await api.post(
        `/notas-entrada/${previewProcessamento.nota_id}/processar`,
        Object.keys(overridesNaoDefault).length > 0 ? { multiplicadores_override: overridesNaoDefault } : {}
      );

      toast.success(
        `✅ Nota processada! ${response.data.itens_processados} itens lançados no estoque`,
        { duration: 5000 }
      );
      
      setMostrarDetalhes(false);
      setNotaSelecionada(null);
      setMostrarRevisaoPrecos(false);
      setPreviewProcessamento(null);
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

  const formatarDataRelatorio = (valor) => {
    if (!valor) return 'Nao informado';
    const dt = new Date(valor);
    if (Number.isNaN(dt.getTime())) return 'Nao informado';
    return dt.toLocaleDateString('pt-BR');
  };

  const formatarMoedaRelatorio = (valor) => {
    const numero = Number(valor || 0);
    if (Number.isNaN(numero)) return '0,00';
    return numero.toFixed(2).replace('.', ',');
  };

  const normalizarProdutoPreview = (item) => item.produto_vinculado || {
    produto_id: item.produto_id,
    produto_nome: item.produto_nome,
    produto_codigo: item.produto_codigo,
    produto_ean: item.produto_ean,
    custo_anterior: item.custo_anterior,
    custo_novo: item.custo_novo,
    variacao_custo_percentual: item.variacao_custo_percentual
  };

  const obterHistoricoNfAnterior = (historicos, numeroNotaAtual) => {
    if (!Array.isArray(historicos) || historicos.length === 0) return null;
    const numeroAtual = String(numeroNotaAtual || '').trim();

    const candidatoNfeAnterior = historicos.find((hist) => {
      if (!hist) return false;
      const ehNfe = hist.motivo === 'nfe_entrada';
      const temNumero = !!hist.nota_numero;
      const temCusto = hist.preco_custo_novo !== null && hist.preco_custo_novo !== undefined;
      const notaDiferente = String(hist.nota_numero || '').trim() !== numeroAtual;
      return ehNfe && temNumero && temCusto && notaDiferente;
    });

    if (candidatoNfeAnterior) return candidatoNfeAnterior;

    return historicos.find((hist) =>
      hist &&
      hist.preco_custo_novo !== null &&
      hist.preco_custo_novo !== undefined
    ) || null;
  };

  const montarDadosRelatorioCustosMaiores = async () => {
    const itensAumentaram = (previewProcessamento?.itens || [])
      .filter((item) => {
        const produto = normalizarProdutoPreview(item);
        const variacao = Number(produto.variacao_custo_percentual || 0);
        return produto.produto_id && variacao > 0;
      });

    if (itensAumentaram.length === 0) {
      throw new Error('Nenhum produto com aumento de custo nesta NF.');
    }

    const linhas = await Promise.all(itensAumentaram.map(async (item) => {
      const produto = normalizarProdutoPreview(item);
      let historicos = [];

      try {
        const historicoRes = await api.get(`/produtos/${produto.produto_id}/historico-precos`, {
          params: { limit: 100 }
        });
        historicos = historicoRes.data || [];
      } catch (error) {
        console.warn(`Nao foi possivel buscar historico do produto ${produto.produto_id}`, error);
      }

      const nfAnterior = obterHistoricoNfAnterior(historicos, previewProcessamento?.numero_nota);
      const custoAnteriorNf = Number(
        nfAnterior?.preco_custo_novo ??
        nfAnterior?.preco_custo_anterior ??
        produto.custo_anterior ??
        0
      );
      const custoAtualNf = Number(
        produto.custo_novo ??
        item.custo_aquisicao_unitario_nf ??
        item.custo_unitario_efetivo_nf ??
        item.valor_unitario_nf ??
        0
      );

      return {
        produto_nome: produto.produto_nome || 'Produto sem nome',
        sku: produto.produto_codigo || '',
        ean: produto.produto_ean || '',
        fornecedor: previewProcessamento?.fornecedor_nome || '',
        nf_atual_numero: previewProcessamento?.numero_nota || '',
        nf_atual_data: previewProcessamento?.data_emissao || null,
        nf_atual_custo: custoAtualNf,
        nf_atual_quantidade: Number(item.quantidade_efetiva_nf || item.quantidade_nf || 0),
        nf_anterior_numero: nfAnterior?.nota_numero || '',
        nf_anterior_data: nfAnterior?.nota_data_emissao || nfAnterior?.data || null,
        nf_anterior_custo: custoAnteriorNf,
        variacao_percentual: Number(produto.variacao_custo_percentual || 0),
        variacao_absoluta: custoAtualNf - custoAnteriorNf,
        composicao_custo: item.composicao_custo || {}
      };
    }));

    return linhas.sort((a, b) => b.variacao_percentual - a.variacao_percentual);
  };

  const exportarRelatorioCustosMaioresCSV = async () => {
    try {
      setGerandoRelatorioCustos(true);
      const linhas = await montarDadosRelatorioCustosMaiores();
      const headers = [
        'Produto',
        'SKU',
        'EAN',
        'Fornecedor',
        'NF Atual',
        'Data NF Atual',
        'Custo Bruto Unit.',
        'Frete Unit.',
        'Seguro Unit.',
        'Outras Despesas Unit.',
        'Desconto Unit.',
        'ICMS ST Unit.',
        'IPI Unit.',
        'ICMS Unit.',
        'PIS Unit.',
        'COFINS Unit.',
        'Custo Aquisicao Unit.',
        'Qtd NF Atual',
        'NF Anterior',
        'Data NF Anterior',
        'Custo NF Anterior',
        'Variacao %',
        'Variacao R$'
      ];

      const escapeCsv = (valor) => `"${String(valor ?? '').replaceAll('"', '""')}"`;
      const corpo = linhas.map((linha) => {
        const comp = linha.composicao_custo?.componentes_unitario || {};
        const compTotal = linha.composicao_custo?.componentes_total || {};
        
        return [
          linha.produto_nome,
          linha.sku || 'Nao informado',
          linha.ean || 'Nao informado',
          linha.fornecedor,
          linha.nf_atual_numero,
          formatarDataRelatorio(linha.nf_atual_data),
          formatarMoedaRelatorio(linha.composicao_custo?.custo_bruto_unitario || 0),
          formatarMoedaRelatorio(comp.valor_frete || 0),
          formatarMoedaRelatorio(comp.valor_seguro || 0),
          formatarMoedaRelatorio(comp.valor_outras_despesas || 0),
          formatarMoedaRelatorio(-(comp.valor_desconto || 0)),
          formatarMoedaRelatorio(comp.valor_icms_st || 0),
          formatarMoedaRelatorio(comp.valor_ipi || 0),
          formatarMoedaRelatorio(comp.valor_icms || 0),
          formatarMoedaRelatorio(comp.valor_pis || 0),
          formatarMoedaRelatorio(comp.valor_cofins || 0),
          formatarMoedaRelatorio(linha.nf_atual_custo),
          linha.nf_atual_quantidade,
          linha.nf_anterior_numero || 'Nao encontrado',
          formatarDataRelatorio(linha.nf_anterior_data),
          formatarMoedaRelatorio(linha.nf_anterior_custo),
          `${linha.variacao_percentual.toFixed(2).replace('.', ',')}%`,
          formatarMoedaRelatorio(linha.variacao_absoluta)
        ].map(escapeCsv).join(';');
      });

      const csv = `\uFEFF${headers.join(';')}\n${corpo.join('\n')}`;
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `relatorio_custos_maiores_nf_${previewProcessamento?.numero_nota || 'nfe'}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success('CSV gerado com sucesso!');
    } catch (error) {
      toast.error(error.message || 'Erro ao gerar CSV');
    } finally {
      setGerandoRelatorioCustos(false);
    }
  };

  const exportarRelatorioCustosMaioresPDF = async () => {
    try {
      setGerandoRelatorioCustos(true);
      const linhas = await montarDadosRelatorioCustosMaiores();
      const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      const marginX = 10;
      const pageWidth = doc.internal.pageSize.getWidth();
      const usableWidth = pageWidth - (marginX * 2);
      const tableStartY = 30;
      const rowHeight = 6;

      const colunas = [
        { key: 'produto_nome', label: 'Produto', width: 30 },
        { key: 'sku', label: 'SKU', width: 10 },
        { key: 'nf_atual_numero', label: 'NF', width: 10 },
        { key: 'custo_bruto_unitario', label: 'Bruto', width: 10 },
        { key: 'frete_unitario', label: 'Frete', width: 10 },
        { key: 'seguro_unitario', label: 'Seguro', width: 10 },
        { key: 'outras_despesas_unitario', label: 'Desp.', width: 10 },
        { key: 'desconto_unitario', label: 'Desc.', width: 10 },
        { key: 'icms_st_unitario', label: 'ICMS ST', width: 10 },
        { key: 'ipi_unitario', label: 'IPI', width: 10 },
        { key: 'icms_unitario', label: 'ICMS', width: 10 },
        { key: 'custo_aquisicao', label: 'Custo Total', width: 12 },
        { key: 'nf_anterior_numero', label: 'NF Ant.', width: 10 },
        { key: 'nf_anterior_custo', label: 'Custo Ant.', width: 12 },
        { key: 'variacao_percentual', label: 'Var %', width: 10 },
        { key: 'variacao_absoluta', label: 'Delta R$', width: 12 }
      ];

      const larguraColunas = colunas.reduce((acc, col) => acc + col.width, 0);
      const escala = larguraColunas > usableWidth ? usableWidth / larguraColunas : 1;
      colunas.forEach((col) => { col.width = Number((col.width * escala).toFixed(2)); });

      const truncarTexto = (texto, larguraMax) => {
        const valor = String(texto ?? '');
        if (!valor) return '';
        const larguraTexto = doc.getTextWidth(valor);
        if (larguraTexto <= larguraMax) return valor;
        let corte = valor;
        while (corte.length > 1 && doc.getTextWidth(`${corte}...`) > larguraMax) {
          corte = corte.slice(0, -1);
        }
        return `${corte}...`;
      };

      const renderCabecalhoPagina = () => {
        doc.setTextColor(30, 41, 59);
        doc.setFontSize(12);
        doc.text(`Relatorio de custos maiores - NF ${previewProcessamento?.numero_nota || ''}`, marginX, 10);
        doc.setFontSize(9);
        doc.text(`Fornecedor: ${previewProcessamento?.fornecedor_nome || 'Nao informado'}`, marginX, 16);
        doc.text(`Data de emissao NF atual: ${formatarDataRelatorio(previewProcessamento?.data_emissao)}`, marginX, 21);

        doc.setFillColor(226, 232, 240);
        doc.rect(marginX, tableStartY, usableWidth, rowHeight, 'F');
        doc.setDrawColor(203, 213, 225);
        doc.setTextColor(15, 23, 42);
        doc.setFontSize(7);

        let xAtual = marginX;
        colunas.forEach((coluna) => {
          doc.rect(xAtual, tableStartY, coluna.width, rowHeight);
          doc.text(coluna.label, xAtual + 1, tableStartY + 4);
          xAtual += coluna.width;
        });
      };

      renderCabecalhoPagina();

      let y = tableStartY + rowHeight;
      linhas.forEach((linha) => {
        if (y > 190) {
          doc.addPage();
          renderCabecalhoPagina();
          y = tableStartY + rowHeight;
        }

        let xAtual = marginX;
        doc.setDrawColor(226, 232, 240);
        doc.setTextColor(15, 23, 42);
        doc.setFontSize(6.5);

        const comp = linha.composicao_custo?.componentes_unitario || {};
        const rowData = {
          produto_nome: truncarTexto(linha.produto_nome, 28),
          sku: linha.sku || '-',
          nf_atual_numero: linha.nf_atual_numero,
          custo_bruto_unitario: formatarMoedaRelatorio(linha.composicao_custo?.custo_bruto_unitario || 0),
          frete_unitario: formatarMoedaRelatorio(comp.valor_frete || 0),
          seguro_unitario: formatarMoedaRelatorio(comp.valor_seguro || 0),
          outras_despesas_unitario: formatarMoedaRelatorio(comp.valor_outras_despesas || 0),
          desconto_unitario: formatarMoedaRelatorio(-(comp.valor_desconto || 0)),
          icms_st_unitario: formatarMoedaRelatorio(comp.valor_icms_st || 0),
          ipi_unitario: formatarMoedaRelatorio(comp.valor_ipi || 0),
          icms_unitario: formatarMoedaRelatorio(comp.valor_icms || 0),
          custo_aquisicao: formatarMoedaRelatorio(linha.nf_atual_custo),
          nf_anterior_numero: linha.nf_anterior_numero || '-',
          nf_anterior_custo: formatarMoedaRelatorio(linha.nf_anterior_custo),
          variacao_percentual: `${Number(linha.variacao_percentual || 0).toFixed(2).replace('.', ',')}%`,
          variacao_absoluta: formatarMoedaRelatorio(linha.variacao_absoluta)
        };

        colunas.forEach((coluna) => {
          doc.rect(xAtual, y, coluna.width, rowHeight);
          const valor = rowData[coluna.key] || '';
          const texto = truncarTexto(valor, coluna.width - 2);
          doc.text(texto, xAtual + 1, y + 4);
          xAtual += coluna.width;
        });

        y += rowHeight;
      });

      doc.save(`relatorio_custos_maiores_nf_${previewProcessamento?.numero_nota || 'nfe'}.pdf`);
      toast.success('PDF gerado com sucesso!');
    } catch (error) {
      toast.error(error.message || 'Erro ao gerar PDF');
    } finally {
      setGerandoRelatorioCustos(false);
    }
  };

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
      // Ordenar itens por ID para manter ordem consistente
      if (response.data.itens) {
        response.data.itens.sort((a, b) => a.id - b.id);
      }
      setNotaSelecionada(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao desvincular produto');
    }
  };

  // Detectar divergências entre NF e produto vinculado
  const detectarDivergencias = (item) => {
    // Verificar se tem produto vinculado (pode estar em produto_vinculado ou produto_nome)
    const produtoNome = item.produto_vinculado?.produto_nome || item.produto_nome;
    if (!produtoNome) return [];
    
    const divergencias = [];
    const descNF = item.descricao_nf || item.descricao || '';
    const descProd = produtoNome || '';
    
    if (!descNF || !descProd) return [];
    
    const normalizarTexto = (txt) =>
      (txt || '')
        .toString()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase();

    const normalizarPesoToken = (pesoToken) => {
      const match = String(pesoToken || '').match(/(\d+(?:[.,]\d+)?)\s*(kg|g|gr|mg|ml|l|un|und|unid)/i);
      if (!match) return null;
      const valor = Number.parseFloat(match[1].replace(',', '.'));
      if (Number.isNaN(valor)) return null;
      const unidade = match[2].toLowerCase();

      if (['kg', 'g', 'gr', 'mg'].includes(unidade)) {
        const emGramas = unidade === 'kg'
          ? valor * 1000
          : unidade === 'mg'
            ? valor / 1000
            : valor;
        return { grupo: 'massa', valorBase: emGramas, texto: `${valor}${unidade}` };
      }

      if (['l', 'ml'].includes(unidade)) {
        const emMl = unidade === 'l' ? valor * 1000 : valor;
        return { grupo: 'volume', valorBase: emMl, texto: `${valor}${unidade}` };
      }

      return { grupo: 'unidade', valorBase: valor, texto: `${valor}${unidade}` };
    };

    const detectarEspecie = (txt) => {
      const t = normalizarTexto(txt);
      if (/(\bgato\b|\bcat\b|\bfelino\b)/.test(t)) return 'gato';
      if (/(\bcachorro\b|\bcao\b|\bdog\b|\bcanino\b)/.test(t)) return 'cachorro';
      return null;
    };

    const descNFLower = normalizarTexto(descNF);
    const descProdLower = normalizarTexto(descProd);
    
    // Detectar peso/tamanho
    const regexPeso = /(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|un|und|unid)/gi;
    const pesosNF = [...descNFLower.matchAll(regexPeso)];
    const pesosProd = [...descProdLower.matchAll(regexPeso)];
    
    if (pesosNF.length > 0 && pesosProd.length > 0) {
      const pesoNF = normalizarPesoToken(pesosNF[0][0]);
      const pesoProd = normalizarPesoToken(pesosProd[0][0]);

      if (pesoNF && pesoProd) {
        const mesmaCategoria = pesoNF.grupo === pesoProd.grupo;
        const tolerancia = pesoNF.grupo === 'unidade' ? 0.01 : 0.5;
        const diferente = !mesmaCategoria || Math.abs(pesoNF.valorBase - pesoProd.valorBase) > tolerancia;

        if (diferente) {
          divergencias.push(`Peso/Tamanho diferente: NF="${pesoNF.texto}" vs Produto="${pesoProd.texto}"`);
        }
      }
    }
    
    // Detectar cor
    const cores = ['preto', 'branco', 'vermelho', 'azul', 'verde', 'amarelo', 'rosa', 'roxo', 'laranja', 'marrom', 'cinza'];
    const corNF = cores.find(cor => descNFLower.includes(cor));
    const corProd = cores.find(cor => descProdLower.includes(cor));
    
    if (corNF && corProd && corNF !== corProd) {
      divergencias.push(`Cor diferente: NF="${corNF}" vs Produto="${corProd}"`);
    }
    
    // Detectar sabor (para rações)
    const sabores = ['frango', 'carne', 'peixe', 'cordeiro', 'salmao', 'salmão', 'atum', 'vegetais'];
    const saborNF = sabores.find(sabor => descNFLower.includes(sabor));
    const saborProd = sabores.find(sabor => descProdLower.includes(sabor));
    
    if (saborNF && saborProd && saborNF !== saborProd) {
      divergencias.push(`Sabor diferente: NF="${saborNF}" vs Produto="${saborProd}"`);
    }
    
    // Detectar animal (cachorro/gato)
    const especieNF = detectarEspecie(descNF);
    const especieProduto = detectarEspecie(descProd);

    if (especieNF && especieProduto && especieNF !== especieProduto) {
      if (especieNF === 'cachorro') {
        divergencias.push('⚠️ Animal diferente: NF para CACHORRO mas produto é para GATO');
      } else {
        divergencias.push('⚠️ Animal diferente: NF para GATO mas produto é para CACHORRO');
      }
    }
    
    return divergencias;
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
      
      toast.success(`✅ Produto ${response.data.produto.codigo} criado e vinculado!`);
      
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
      setNotaSelecionada(notaResponse.data);
      
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
      setNotaSelecionada(notaResponse.data);
      
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

  const carregarConfigSefaz = async () => {
    try {
      setConfigSefazLoading(true);
      const { data } = await api.get('/sefaz/config');
      setCfgSefaz(prev => ({
        ...prev,
        enabled: Boolean(data.enabled),
        modo: data.modo || 'mock',
        ambiente: data.ambiente || 'homologacao',
        uf: data.uf || 'SP',
        cnpj: data.cnpj || '',
        importacao_automatica: Boolean(data.importacao_automatica),
        importacao_intervalo_min: Number(data.importacao_intervalo_min || 15),
        cert_ok: Boolean(data.cert_ok),
        ultimo_sync_status: data.ultimo_sync_status || 'nunca',
        ultimo_sync_mensagem: data.ultimo_sync_mensagem || 'Ainda nao sincronizado.',
        ultimo_sync_at: data.ultimo_sync_at || null,
        ultimo_sync_documentos: Number(data.ultimo_sync_documentos || 0),
      }));
    } catch {
      setMensagemRotina('Nao foi possivel carregar a configuracao da SEFAZ.');
    } finally {
      setConfigSefazLoading(false);
    }
  };

  const salvarRotinaSefaz = async () => {
    setMensagemRotina('');
    try {
      setSalvandoRotina(true);
      await api.post('/sefaz/config', {
        enabled: cfgSefaz.enabled,
        modo: cfgSefaz.modo,
        ambiente: cfgSefaz.ambiente,
        uf: cfgSefaz.uf,
        cnpj: cfgSefaz.cnpj,
        importacao_automatica: cfgSefaz.importacao_automatica,
        importacao_intervalo_min: Number(cfgSefaz.importacao_intervalo_min || 15),
      });
      setMensagemRotina('Rotina automatica salva com sucesso.');
      await carregarConfigSefaz();
    } catch (err) {
      setMensagemRotina(err?.response?.data?.detail || 'Erro ao salvar rotina automatica.');
    } finally {
      setSalvandoRotina(false);
    }
  };

  const sincronizarAgoraSefaz = async () => {
    setMensagemRotina('');
    try {
      setSincronizando(true);
      const { data } = await api.post('/sefaz/sync-now');
      setMensagemRotina(data?.mensagem || 'Sincronizacao solicitada.');
      await carregarConfigSefaz();
    } catch (err) {
      setMensagemRotina(err?.response?.data?.detail || 'Erro ao sincronizar agora.');
    } finally {
      setSincronizando(false);
    }
  };

  const diagnosticarEmLote = async () => {
    setResultadoDiagnostico(null);
    setDiagnosticando(true);
    try {
      const { data } = await api.post('/sefaz/sync-diagnostico?max_lotes=5');
      setResultadoDiagnostico(data);
      await carregarConfigSefaz();
      await carregarDados();
    } catch (err) {
      setResultadoDiagnostico({ erro: err?.response?.data?.detail || 'Erro ao executar diagnostico em lote.' });
    } finally {
      setDiagnosticando(false);
    }
  };

  const verificarNsuStatus = async () => {
    setCarregandoNsu(true);
    try {
      const { data } = await api.get('/sefaz/nsu-status');
      setNsuStatus(data);
      await carregarConfigSefaz();
    } catch (err) {
      setNsuStatus({ erro: err?.response?.data?.detail || 'Erro ao consultar NSU.' });
    } finally {
      setCarregandoNsu(false);
    }
  };

  const resetarNsu = async () => {
    if (!window.confirm('Isso vai redefinir o ponto de partida da busca para o ZERO (início de tudo). As notas já importadas não serão duplicadas, mas a sincronização vai precisar paginar por todos os documentos históricos da SEFAZ.\n\nConfirma?')) return;
    setResetandoNsu(true);
    try {
      await api.post('/sefaz/reset-nsu', { nsu: '000000000000000' });
      setNsuStatus(null);
      setMensagemRotina('NSU zerado. Próxima sincronização vai buscar todos os documentos disponíveis na SEFAZ.');
      await carregarConfigSefaz();
    } catch (err) {
      setMensagemRotina(err?.response?.data?.detail || 'Erro ao resetar NSU.');
    } finally {
      setResetandoNsu(false);
    }
  };

  const consultarSefaz = async (e) => {
    e.preventDefault();
    setErroSefaz('');
    setAvisoConectorSefaz('');
    if (chaveSefaz.length !== 44) {
      setErroSefaz('A chave de acesso deve ter exatamente 44 digitos.');
      return;
    }
    try {
      setLoadingSefaz(true);
      const resp = await api.post('/sefaz/consultar', { chave_acesso: chaveSefaz });
      const novaConsulta = {
        id: `${Date.now()}-${resp.data.chave_acesso}`,
        criadoEm: new Date().toISOString(),
        dados: resp.data,
      };
      setConsultasSefaz(prev => [novaConsulta, ...prev]);
      setConsultaExpandidaId(null);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao consultar a SEFAZ.';
      const httpStatus = Number(err?.response?.status || 0);
      if (httpStatus === 501 && msg.toLowerCase().includes('conector')) {
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
      toast.error('Esta consulta nao trouxe XML completo. Tente outra chave ou rode sincronizacao real.');
      return;
    }
    try {
      setImportandoConsultaId(consulta.id);
      const fileName = montarNomeXml(consulta.dados);
      const blob = new Blob([xmlNfe], { type: 'application/xml;charset=utf-8' });
      const file = new File([blob], fileName, { type: 'text/xml' });
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await api.post('/notas-entrada/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success('NF-e importada com sucesso!');
      await carregarDados();
      const notaIdCriada = data?.nota_id;
      if (notaIdCriada) {
        await abrirDetalhes(notaIdCriada);
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Falha ao importar NF-e.';
      toast.error(msg);
    } finally {
      setImportandoConsultaId(null);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pendente: 'bg-yellow-200 text-yellow-800',
      processada: 'bg-green-200 text-green-800',
      cancelada: 'bg-red-200 text-red-800',
      erro: 'bg-red-300 text-red-900'
    };
    const labels = {
      pendente: 'Pendente',
      processada: 'Conciliada',
      cancelada: 'Cancelada',
      erro: 'Erro',
    };
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${styles[status] || 'bg-gray-200'}`}>
        {labels[status] || status.toUpperCase()}
      </span>
    );
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

  return (
    <div className="p-6">
      {/* Cabecalho + Acoes */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Central NF-e Entradas</h1>
          <p className="text-gray-600 text-sm mt-1">Gerencie todas as notas fiscais de entrada — via upload ou direto da SEFAZ</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="inline-block">
            <input type="file" accept=".xml" onChange={handleFileUpload} disabled={uploadingFile || uploadingLote} className="hidden" />
            <span className={`px-4 py-2 rounded-lg font-semibold cursor-pointer inline-block text-sm ${(uploadingFile || uploadingLote) ? 'bg-gray-300 cursor-not-allowed text-gray-500' : 'bg-blue-600 hover:bg-blue-700 text-white'}`}>
              {uploadingFile ? 'Processando...' : 'Importar XML'}
            </span>
          </label>
          <label className="inline-block">
            <input type="file" accept=".xml" multiple onChange={handleMultipleFilesUpload} disabled={uploadingFile || uploadingLote} className="hidden" />
            <span className={`px-4 py-2 rounded-lg font-semibold cursor-pointer inline-block text-sm ${(uploadingFile || uploadingLote) ? 'bg-gray-300 cursor-not-allowed text-gray-500' : 'bg-blue-500 hover:bg-blue-600 text-white'}`}>
              {uploadingLote ? 'Processando lote...' : 'Importar Varios XML'}
            </span>
          </label>
          <button
            type="button"
            onClick={() => { setMostrarPainelSefaz(v => !v); setMostrarConfigSefaz(false); }}
            className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${mostrarPainelSefaz ? 'bg-emerald-700 text-white' : 'bg-emerald-600 hover:bg-emerald-700 text-white'}`}
          >
            Buscar pela SEFAZ
          </button>
          <button
            type="button"
            onClick={() => { setMostrarConfigSefaz(v => !v); if (!mostrarConfigSefaz) { carregarConfigSefaz(); } setMostrarPainelSefaz(false); }}
            className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${mostrarConfigSefaz ? 'bg-gray-700 text-white' : 'bg-gray-600 hover:bg-gray-700 text-white'}`}
          >
            Configurar SEFAZ
          </button>
        </div>
      </div>

      {/* Painel: Buscar pela SEFAZ */}
      {mostrarPainelSefaz && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6 border-l-4 border-emerald-500">
          <h2 className="text-lg font-bold text-gray-800 mb-4">Buscar NF-e pela SEFAZ</h2>
          <form onSubmit={consultarSefaz} className="flex gap-3 mb-2">
            <input
              type="text"
              value={chaveSefaz}
              onChange={e => setChaveSefaz(formatarChaveAcesso(e.target.value))}
              onPaste={e => { e.preventDefault(); setChaveSefaz(formatarChaveAcesso(e.clipboardData?.getData('text') || '')); }}
              placeholder="Chave de acesso (44 digitos)"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              maxLength={80}
            />
            <button
              type="submit"
              disabled={loadingSefaz || chaveSefaz.length !== 44}
              className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50"
            >
              {loadingSefaz ? 'Consultando...' : 'Consultar'}
            </button>
          </form>
          <p className="text-xs text-gray-400 mb-3">{chaveSefaz.length}/44 digitos</p>
          {erroSefaz && <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{erroSefaz}</div>}
          {avisoConectorSefaz && (
            <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
              <strong>Integracao validada, etapa final pendente:</strong> {avisoConectorSefaz}
            </div>
          )}
          {consultasSefaz.length > 0 && (
            <div className="space-y-3 mt-4">
              <p className="text-sm font-semibold text-gray-700">Consultas desta sessao ({consultasSefaz.length}):</p>
              {consultasSefaz.map(consulta => {
                const exp = consultaExpandidaId === consulta.id;
                const d = consulta.dados;
                return (
                  <div key={consulta.id} className="border border-gray-200 rounded-lg overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setConsultaExpandidaId(exp ? null : consulta.id)}
                      className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-gray-800">NF {d.numero_nf}/{d.serie} — {d.emitente_nome}</span>
                        <span className="text-xs text-gray-500">{d.itens?.length || 0} itens · {formatMoneyBRL(d.valor_total_nf)}</span>
                      </div>
                    </button>
                    <div className="px-4 pb-3 bg-gray-50 border-t border-gray-100 flex flex-wrap gap-2 items-center pt-2">
                      <button
                        type="button"
                        onClick={() => usarNaEntrada(consulta)}
                        disabled={importandoConsultaId === consulta.id}
                        className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 disabled:opacity-60"
                      >
                        {importandoConsultaId === consulta.id ? 'Importando...' : 'Usar esta NF na Entrada'}
                      </button>
                    </div>
                    {exp && d.itens?.length > 0 && (
                      <div className="p-4 border-t border-gray-100 overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-gray-50 text-gray-600 uppercase">
                              <th className="text-left px-2 py-1">Cod.</th>
                              <th className="text-left px-2 py-1">Descricao</th>
                              <th className="text-right px-2 py-1">Qtd</th>
                              <th className="text-right px-2 py-1">Unit.</th>
                              <th className="text-right px-2 py-1">Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {d.itens.map(item => (
                              <tr key={item.numero_item} className="hover:bg-gray-50">
                                <td className="px-2 py-1 font-mono">{item.codigo_produto}</td>
                                <td className="px-2 py-1">{item.descricao}</td>
                                <td className="px-2 py-1 text-right">{item.quantidade}</td>
                                <td className="px-2 py-1 text-right">{formatMoneyBRL(item.valor_unitario)}</td>
                                <td className="px-2 py-1 text-right font-semibold">{formatMoneyBRL(item.valor_total)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Painel: Configurar SEFAZ */}
      {mostrarConfigSefaz && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6 border-l-4 border-gray-500">
          <h2 className="text-lg font-bold text-gray-800 mb-1">Configurar SEFAZ</h2>
          <p className="text-sm text-gray-500 mb-4">
            Certificado digital e parametros ficam em{' '}
            <Link to="/configuracoes/integracoes" className="text-indigo-600 font-semibold">Configuracoes &gt; Integracoes</Link>.
            Aqui configure apenas a rotina automatica.
          </p>
          {configSefazLoading ? (
            <p className="text-sm text-gray-500">Carregando configuracao...</p>
          ) : (
            <>
              {(!cfgSefaz.enabled || !cfgSefaz.cert_ok) && (
                <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm mb-4">
                  Integracao ainda nao esta pronta para rotina automatica. Finalize em Configuracoes &gt; Integracoes.
                </div>
              )}
              <div className="mb-4">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={cfgSefaz.importacao_automatica}
                    onChange={e => setCfgSefaz(prev => ({ ...prev, importacao_automatica: e.target.checked }))}
                  />
                  <span>Ativar importacao automatica</span>
                </label>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
                <div>Ultima sincronizacao: <strong>{cfgSefaz.ultimo_sync_at ? new Date(cfgSefaz.ultimo_sync_at).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' }) : '-'}</strong></div>
                <div>Status: <strong>{cfgSefaz.ultimo_sync_status}</strong></div>
                <div>Documentos trazidos: <strong>{cfgSefaz.ultimo_sync_documentos}</strong></div>
                <div>Modo atual: <strong>{cfgSefaz.modo}</strong></div>
                <div className="sm:col-span-2">Mensagem: <strong>{cfgSefaz.ultimo_sync_mensagem}</strong></div>
              </div>

              {mensagemRotina && (
                <div className="text-sm bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-700 mb-4">{mensagemRotina}</div>
              )}
              <div className="flex flex-wrap gap-3">
                <button type="button" onClick={salvarRotinaSefaz} disabled={salvandoRotina} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60">
                  {salvandoRotina ? 'Salvando...' : 'Salvar configuracao'}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Estatisticas */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus('todos')}>
          <div className="text-2xl font-bold text-blue-600">
            {notasEntrada.length}
          </div>
          <div className="text-sm text-gray-600">Total de Notas</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus('pendente')}>
          <div className="text-2xl font-bold text-yellow-600">
            {notasEntrada.filter(n => n.status === 'pendente').length}
          </div>
          <div className="text-sm text-gray-600">Pendentes</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFiltroStatus('processada')}>
          <div className="text-2xl font-bold text-green-600">
            {notasEntrada.filter(n => n.status === 'processada').length}
          </div>
          <div className="text-sm text-gray-600">Conciliadas</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-purple-600">
            {formatMoneyBRL(notasEntrada.filter(n => n.status === 'processada').reduce((sum, n) => sum + (n.valor_total || 0), 0))}
          </div>
          <div className="text-sm text-gray-600">Valor Conciliado</div>
        </div>
      </div>

      {/* Lista de Notas */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Notas Fiscais de Entrada</h2>
          <div className="flex flex-wrap gap-1">
            {[
              { v: 'todos', label: 'Todas' },
              { v: 'pendente', label: 'Pendentes' },
              { v: 'processada', label: 'Conciliadas' },
              { v: 'erro', label: 'Com Erro' },
            ].map(({ v, label }) => (
              <button
                key={v}
                type="button"
                onClick={() => setFiltroStatus(v)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${filtroStatus === v ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">Chave NF-e</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Fornecedor</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Data Emissao</th>
                <th className="px-4 py-3 text-right text-sm font-semibold">Valor</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">Itens</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">Status</th>
                <th className="px-4 py-3 text-center text-sm font-semibold">Acoes</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const notas = filtroStatus === 'todos' ? notasEntrada : notasEntrada.filter(n => n.status === filtroStatus);
                if (notas.length === 0) {
                  return (
                    <tr>
                      <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                        {notasEntrada.length === 0
                          ? 'Nenhuma nota fiscal importada. Importe um XML ou busque pela SEFAZ.'
                          : `Nenhuma nota com status "${filtroStatus}".`}
                      </td>
                    </tr>
                  );
                }
                return notas.map(nota => (
                  <tr
                    key={nota.id}
                    onClick={() => abrirVisualizacao(nota.id)}
                    className="border-t hover:bg-blue-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="font-mono text-xs">{nota.chave_acesso.substring(0, 20)}...</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold">{nota.fornecedor_nome}</div>
                      <div className="text-xs text-gray-500">{nota.fornecedor_cnpj}</div>
                    </td>
                    <td className="px-4 py-3">{new Date(nota.data_emissao).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right font-semibold">{formatMoneyBRL(nota.valor_total || 0)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-semibold">
                        {nota.produtos_vinculados + nota.produtos_nao_vinculados} itens
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">{getStatusBadge(nota.status)}</td>
                    <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-2 justify-center">
                        {nota.status === 'pendente' && (
                          <button
                            onClick={() => abrirDetalhes(nota.id)}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold text-sm"
                            title="Vincular produtos"
                          >
                            Vincular
                          </button>
                        )}
                        {nota.entrada_estoque_realizada ? (
                          <button
                            onClick={() => reverterNota(nota.id, nota.numero_nota)}
                            className="text-orange-600 hover:text-orange-800 font-semibold text-sm"
                            title="Reverter entrada no estoque"
                          >
                            Reverter
                          </button>
                        ) : (
                          <button
                            onClick={() => excluirNota(nota.id, nota.numero_nota)}
                            className="text-red-600 hover:text-red-800 font-semibold text-sm"
                            title="Excluir nota"
                          >
                            Excluir
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ));
              })()}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Detalhes */}
      {mostrarDetalhes && notaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
            {/* Cabecalho */}
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">Detalhes da NF-e</h2>
                <p className="text-sm text-gray-600">Chave: {notaSelecionada.chave_acesso}</p>
              </div>
              <button
                onClick={() => {
                  setMostrarDetalhes(false);
                  setNotaSelecionada(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                X
              </button>
            </div>

            {/* Informacoes da Nota */}
            <div className="px-6 py-4 border-b bg-gray-50">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Fornecedor:</span>
                  <div className="font-semibold">{notaSelecionada.fornecedor_nome}</div>
                  <div className="text-xs text-gray-500">{notaSelecionada.fornecedor_cnpj}</div>
                  {notaSelecionada.fornecedor_id && (
                    <div className="text-xs text-green-600 mt-1">Cadastrado</div>
                  )}
                </div>
                <div>
                  <span className="text-gray-600">Data Emissao:</span>
                  <div className="font-semibold">{new Date(notaSelecionada.data_emissao).toLocaleDateString()}</div>
                </div>
                <div>
                  <span className="text-gray-600">Valor Total:</span>
                  <div className="font-bold text-lg text-green-600">R$ {(notaSelecionada.valor_total || 0).toFixed(2)}</div>
                </div>
              </div>
            </div>

            {/* Alerta de Fornecedor Novo - Versao Compacta */}
            {notaSelecionada.fornecedor_id && notaSelecionada.fornecedor_criado_automaticamente && (
              <div className="px-6 py-2 bg-blue-50 border-b border-blue-200">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-blue-800">
                    <strong>{notaSelecionada.fornecedor_nome}</strong> foi cadastrado automaticamente.
                  </div>
                  <button
                    onClick={() => navigate(`/clientes/${notaSelecionada.fornecedor_id}`)}
                    className="px-3 py-1 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 text-xs"
                  >
                    Completar Cadastro
                  </button>
                </div>
              </div>
            )}

            {/* Itens da Nota */}
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-xl text-gray-800">
                  Produtos da Nota ({notaSelecionada.itens.length})
                </h3>
                
                {notaSelecionada.status === 'pendente' && 
                 notaSelecionada.itens.some(item => !item.produto_id) && (
                  <button
                    onClick={criarTodosProdutosNaoVinculados}
                    disabled={loading}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400 flex items-center gap-2 text-sm"
                    title="Cria automaticamente todos os produtos nao vinculados com os padrões: Estoque mín: 10, máx: 100, Margem: 50%"
                  >
                    <span>Criar Todos Nao Vinculados</span>
                    <span className="text-xs bg-purple-800 px-2 py-0.5 rounded">
                      {notaSelecionada.itens.filter(i => !i.produto_id).length}
                    </span>
                  </button>
                )}
              </div>
              
              <div className="space-y-3">
                {notaSelecionada.itens.map(item => {
                  const divergencias = detectarDivergencias(item);
                  const temDivergencia = divergencias.length > 0;
                  const itemAjustado = aplicarMultiplicadorPackAoItem(item, multiplicadoresPack);
                  const packConfig = obterConfiguracaoPackItem(item, multiplicadoresPack);
                  
                  return (
                    <div key={item.id} className="border-2 border-gray-400 rounded-lg overflow-hidden bg-white shadow-sm">
                      {/* Grade de 2 Colunas: NF-e (esquerda) | Conexão | Produto Sistema (direita) */}
                      <div className="grid grid-cols-[1fr_auto_1fr] gap-0">
                        {/* COLUNA ESQUERDA: Dados da NF-e */}
                        <div className="bg-blue-50 border-r-2 border-gray-300 p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold">NF-e</div>
                            {getConfiancaBadge(item.confianca_vinculo)}
                          </div>
                          
                          <div className="font-semibold text-base mb-2 text-blue-900">{item.descricao}</div>
                          
                          <div className="space-y-1.5 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600">Codigo:</span>
                              <span className="font-mono font-semibold">{item.codigo_produto}</span>
                            </div>
                            {item.ean && item.ean !== 'SEM GTIN' && (
                              <div className="flex justify-between">
                                <span className="text-gray-600">EAN:</span>
                                <span className="font-mono font-semibold">{item.ean}</span>
                              </div>
                            )}
                            <div className="flex justify-between">
                              <span className="text-gray-600">NCM:</span>
                              <span className="font-mono font-semibold">{item.ncm}</span>
                            </div>
                            <div className="flex justify-between border-t pt-1.5 mt-1.5">
                              <span className="text-gray-600">Qtd:</span>
                              <span className="font-semibold">{item.quantidade}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Valor Unit.:</span>
                              <span className="font-semibold">R$ {item.valor_unitario.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Custo Aquisição:</span>
                              <span className="font-semibold text-amber-700">R$ {formatarValorFiscal(obterCustoAquisicaoItem(itemAjustado), 4)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Total:</span>
                              <span className="font-semibold text-green-600">R$ {item.valor_total.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">CFOP:</span>
                              <span className="font-semibold">{item.cfop}</span>
                            </div>

                            {/* Pack / Caixa: multiplicador manual ou auto-detectado */}
                            {notaSelecionada.status === 'pendente' && (
                              <div className="mt-2 pt-2 border-t border-blue-200">
                                <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
                                  <span className="text-gray-600 text-xs font-semibold">Pack (unid./caixa):</span>
                                  <div className="flex items-center gap-1.5 flex-wrap justify-end">
                                    {packConfig.packDetectadoAutomatico && (
                                      <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-semibold">📦 auto</span>
                                    )}
                                    {packConfig.sugestaoAutomaticaDiferenteDoPadrao && (
                                      <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-semibold">
                                        Conferir sugestão x{packConfig.multiplicadorDetectado}
                                      </span>
                                    )}
                                    {packConfig.overrideManual && (
                                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-semibold">
                                        Usando x{packConfig.multiplicador} digitado
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <input
                                    type="number"
                                    min="1"
                                    max="200"
                                    value={packConfig.multiplicador}
                                    onChange={(e) => {
                                      const v = Math.max(1, Math.min(200, Number.parseInt(e.target.value) || 1));
                                      setMultiplicadoresPack(prev => ({ ...prev, [item.id]: v }));
                                    }}
                                    className={`w-20 px-2 py-1 border-2 rounded text-sm text-right font-semibold focus:ring-2 ${
                                      packConfig.overrideManual
                                        ? 'border-blue-400 bg-blue-50 text-blue-900 focus:ring-blue-500'
                                        : packConfig.sugestaoAutomaticaDiferenteDoPadrao
                                          ? 'border-amber-400 bg-amber-50 text-amber-900 focus:ring-amber-500'
                                          : 'border-blue-300 focus:ring-blue-500'
                                    }`}
                                  />
                                  <span className="text-xs text-gray-500">unid. por caixa</span>
                                </div>
                                {(packConfig.sugestaoAutomaticaDiferenteDoPadrao || packConfig.overrideManual) && (
                                  <div
                                    className={`mt-1.5 rounded p-2 text-xs space-y-0.5 border ${
                                      packConfig.overrideManual
                                        ? 'bg-blue-50 border-blue-200 text-blue-800'
                                        : 'bg-amber-50 border-amber-200 text-amber-800'
                                    }`}
                                  >
                                    <div>
                                      {packConfig.overrideManual
                                        ? '✏️ Valor digitado considerado nos cálculos.'
                                        : '🤖 Sugestão automática aplicada nos cálculos.'}
                                    </div>
                                    <div>
                                      🔢 Qtd efetiva: <strong>{itemAjustado.quantidade_efetiva}</strong> unid. ({item.quantidade} cx × {packConfig.multiplicador})
                                    </div>
                                    <div>
                                      💰 Custo unit.: <strong>R$ {obterCustoAquisicaoItem(itemAjustado).toFixed(4)}</strong>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                            <CardFiscal nota={notaSelecionada} item={itemAjustado} composicao={itemAjustado.composicao_custo} />
                          </div>

                          {/* Lote e Validade */}
                          {(item.lote || item.data_validade) && (
                            <div className="mt-3 pt-3 border-t space-y-2">
                              {item.lote && (
                                <div className="text-xs">
                                  <span className="text-gray-600">Lote:</span>
                                  <div className="font-semibold text-purple-800">{item.lote}</div>
                                </div>
                              )}
                              {item.data_validade && (
                                <div className="text-xs">
                                  <span className="text-gray-600">Validade:</span>
                                  <div className="font-semibold text-orange-800">
                                    {new Date(item.data_validade).toLocaleDateString('pt-BR')}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* COLUNA CENTRAL: Ícone de Conexão + Alerta de Divergência */}
                        <div className="flex flex-col items-center justify-center bg-gray-100 px-2 py-4">
                          {item.produto_id ? (
                            <>
                              <button
                                onClick={() => desvincularProduto(notaSelecionada.id, item.id)}
                                className="text-3xl text-green-600 hover:text-red-600 transition-colors mb-2"
                                title="Vinculado - Clique para desvincular"
                              >
                                V
                              </button>
                              {temDivergencia && (
                                <div className="bg-red-100 border-2 border-red-500 rounded-lg p-2 max-w-[200px]">
                                  <div className="text-center">
                                    <div className="text-2xl mb-1">⚠️</div>
                                    <div className="font-bold text-red-700 text-xs mb-1">
                                      DIVERGÊNCIA!
                                    </div>
                                    <div className="text-[10px] text-red-600 space-y-0.5">
                                      {divergencias.map((div) => (
                                        <div key={`${item.id}-${div}`}>• {div}</div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </>
                          ) : (
                            <div className="text-3xl text-gray-400" title="❌ Não vinculado">
                              X
                            </div>
                          )}
                        </div>

                        {/* COLUNA DIREITA: Produto do Sistema */}
                        <div className={`p-4 ${item.produto_id ? 'bg-green-50' : 'bg-gray-50'}`}>

                        {/* COLUNA DIREITA: Produto do Sistema */}
                        <div className={`p-4 ${item.produto_id ? 'bg-green-50' : 'bg-gray-50'}`}>
                          {notaSelecionada.status === 'pendente' ? (
                            <>
                              {item.produto_id ? (
                                <>
                                  <div className="flex items-center gap-2 mb-3">
                                    <div className="bg-green-600 text-white px-2 py-1 rounded text-xs font-bold">
                                      PRODUTO SISTEMA
                                    </div>
                                  </div>
                                  
                                  <div className="font-semibold text-base mb-3 text-green-900">
                                    {item.produto_nome}
                                  </div>

                                  <div className="mb-3 rounded border border-green-200 bg-white/80 p-2 text-xs space-y-1">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-gray-600">SKU:</span>
                                      <span className="font-mono text-gray-900">
                                        {item.produto_codigo || 'Nao informado'}
                                      </span>
                                    </div>
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-gray-600">EAN:</span>
                                      <span className="font-mono text-gray-900">
                                        {item.produto_ean || 'Nao informado'}
                                      </span>
                                    </div>
                                    {item.origem_vinculo_automatico && item.referencia_vinculo && (
                                      <div className="mt-2 rounded border border-emerald-200 bg-emerald-50 p-2 text-emerald-800">
                                        Match automatico por <strong>{item.origem_vinculo_automatico === 'codigo_barras' ? 'codigo de barras' : 'SKU'}</strong>: <strong>{item.referencia_vinculo}</strong>
                                      </div>
                                    )}
                                  </div>

                                  <div className="text-xs text-green-700 mb-3 italic">
                                    Para alterar o vinculo, selecione outro produto ou clique no V para desvincular
                                  </div>

                                  <input
                                    type="text"
                                    placeholder="Pesquisar outro produto para trocar..."
                                    value={filtroProduto[item.id] || ''}
                                    onChange={(e) => atualizarFiltroProduto(item.id, e.target.value)}
                                    className="w-full px-3 py-2 border-2 border-green-300 rounded focus:ring-2 focus:ring-green-500 text-sm mb-2"
                                  />

                                  {/* Select para trocar produto */}
                                  <select
                                    value={item.produto_id}
                                    onChange={(e) => {
                                      if (e.target.value && e.target.value != item.produto_id) {
                                        vincularProduto(notaSelecionada.id, item.id, e.target.value);
                                      }
                                    }}
                                    className="w-full px-3 py-2 border-2 border-green-400 rounded text-sm focus:ring-2 focus:ring-green-500"
                                  >
                                    <option value={item.produto_id}>
                                      {`${item.produto_codigo || 'Sem SKU'} | EAN: ${item.produto_ean || 'Sem EAN'} | ${item.produto_nome}`}
                                    </option>
                                    {(resultadosBuscaProduto[item.id] || [])
                                      .filter(p => p.id !== item.produto_id)
                                      .map(p => (
                                        <option key={p.id} value={p.id}>
                                          {formatarOpcaoProduto(p)}
                                        </option>
                                      ))}
                                  </select>
                                </>
                              ) : (
                                <>
                                  <div className="flex items-center gap-2 mb-3">
                                    <div className="bg-orange-600 text-white px-2 py-1 rounded text-xs font-bold">
                                      ⚠️ NÃO VINCULADO
                                    </div>
                                  </div>
                                  
                                  <div className="space-y-3">
                                    {/* Campo de pesquisa */}
                                    <div>
                                      <div className="block text-xs font-semibold text-gray-700 mb-1">
                                        Pesquisar produto existente:
                                      </div>
                                      <input
                                        type="text"
                                        placeholder="Digite nome ou SKU..."
                                        value={filtroProduto[item.id] || ''}
                                        onChange={(e) => atualizarFiltroProduto(item.id, e.target.value)}
                                        className="w-full px-3 py-2 border-2 border-gray-400 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                                      />
                                    </div>
                                    
                                    {/* Lista de produtos filtrados */}
                                    {filtroProduto[item.id] && filtroProduto[item.id].length >= 2 && (
                                      <div className="border-2 border-gray-300 rounded max-h-48 overflow-y-auto bg-white">
                                        {(() => {
                                          const filtrados = resultadosBuscaProduto[item.id] || [];
                                          if (buscandoProduto[item.id]) {
                                            return (
                                              <div className="px-3 py-4 text-center text-gray-500 text-xs">
                                                Buscando produtos...
                                              </div>
                                            );
                                          }
                                          if (filtrados.length === 0) {
                                            return (
                                              <div className="px-3 py-4 text-center text-gray-500 text-xs">
                                                ❌ Nenhum produto encontrado
                                              </div>
                                            );
                                          }
                                          return filtrados.map(p => (
                                            <button
                                              key={`produto-${item.id}-${p.id}`}
                                              type="button"
                                              onClick={() => {
                                                vincularProduto(notaSelecionada.id, item.id, p.id);
                                                setFiltroProduto(prev => ({ ...prev, [item.id]: '' }));
                                                setResultadosBuscaProduto(prev => ({ ...prev, [item.id]: [] }));
                                              }}
                                              className={`w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-200 last:border-b-0 text-xs ${!p.ativo ? 'text-red-600 font-bold' : ''}`}
                                            >
                                              {!p.ativo && '[INATIVO] '}{p.codigo || 'Sem SKU'} - {p.nome}
                                              <span className="text-gray-500 ml-1">| EAN: {p.codigo_barras || p.gtin_ean || p.gtin_ean_tributario || 'Sem EAN'}</span>
                                              <span className="text-gray-500 ml-1">(Est: {p.estoque_atual || 0})</span>
                                            </button>
                                          ));
                                        })()}
                                      </div>
                                    )}
                                    
                                    <div className="flex items-center gap-2">
                                      <div className="flex-1 border-t border-gray-300"></div>
                                      <span className="text-xs text-gray-500">ou</span>
                                      <div className="flex-1 border-t border-gray-300"></div>
                                    </div>

                                    <button
                                      onClick={() => abrirModalCriarProduto(item)}
                                      className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 text-sm"
                                    >
                                      ➕ Criar Novo Produto
                                    </button>
                                  </div>
                                </>
                              )}
                            </>
                          ) : (
                            // Nota ja processada - apenas visualizacao
                            <div>
                              {item.produto_id ? (
                                <>
                                  <div className="bg-green-600 text-white px-2 py-1 rounded text-xs font-bold inline-block mb-2">
                                    VINCULADO
                                  </div>
                                  <div className="font-semibold text-base text-green-900">
                                    {item.produto_nome}
                                  </div>
                                </>
                              ) : (
                                <div className="bg-gray-600 text-white px-2 py-1 rounded text-xs font-bold inline-block">
                                  ⚠️ NÃO VINCULADO
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Rateio de Estoque (se modo PARCIAL) - Expande por toda a largura */}
                      {notaSelecionada.status === 'pendente' && 
                       tipoRateio === 'parcial' && 
                       item.produto_id && (
                        <div className="col-span-3 p-4 border-t-2 border-gray-300 bg-gradient-to-r from-blue-50 via-gray-50 to-green-50">
                          <h4 className="font-medium text-gray-700 mb-3 flex items-center text-sm">
                            Quantidade destinada ao estoque online
                          </h4>
                          
                          <div className="grid grid-cols-3 gap-4">
                            <div>
                              <div className="block text-xs font-medium text-gray-600 mb-1">Total NF</div>
                              <input
                                type="number"
                                value={item.quantidade}
                                disabled
                                className="w-full px-3 py-2 border border-gray-300 rounded bg-gray-100 text-base font-semibold"
                              />
                            </div>
                            
                            <div>
                              <div className="block text-xs font-medium text-gray-700 mb-1">Online</div>
                              <input
                                type="number"
                                min="0"
                                max={item.quantidade}
                                step="0.01"
                                value={quantidadesOnline[item.id] ?? item.quantidade_online ?? 0}
                                onChange={(e) => {
                                  const valor = Number.parseFloat(e.target.value) || 0;
                                  setQuantidadesOnline({
                                    ...quantidadesOnline,
                                    [item.id]: Math.min(valor, item.quantidade)
                                  });
                                }}
                                className="w-full px-3 py-2 border-2 border-blue-400 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-base font-semibold"
                                placeholder="0"
                              />
                            </div>
                            
                            <div>
                              <div className="block text-xs font-medium text-gray-600 mb-1">Loja</div>
                              <input
                                type="number"
                                value={(item.quantidade - (quantidadesOnline[item.id] ?? item.quantidade_online ?? 0)).toFixed(2)}
                                disabled
                                className="w-full px-3 py-2 border border-gray-300 rounded bg-gray-100 text-base font-semibold"
                              />
                            </div>
                          </div>
                          
                          <div className="mt-3 text-sm text-gray-700 bg-white rounded-lg p-3 border border-gray-300 font-medium">
                            Valor online: R$ {((quantidadesOnline[item.id] ?? item.quantidade_online ?? 0) * item.valor_unitario).toFixed(2)}
                          </div>
                          
                          {(quantidadesOnline[item.id] !== undefined && 
                            quantidadesOnline[item.id] !== item.quantidade_online) ? (
                            <button
                              onClick={() => salvarQuantidadeOnlineItem(
                                notaSelecionada.id, 
                                item.id, 
                                quantidadesOnline[item.id]
                              )}
                              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 mt-3 text-sm"
                            >
                              Salvar Distribuicao
                            </button>
                          ) : (
                            item.quantidade_online !== null && item.quantidade_online !== undefined && (
                              <div className="mt-3 text-sm text-green-700 bg-green-50 rounded-lg p-3 border border-green-200 flex items-center justify-center font-medium">
                                Salvo: {item.quantidade_online} online / {(item.quantidade - item.quantidade_online).toFixed(2)} loja
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>

                    {notaSelecionada.status === 'processada' && item.produto_id && (
                      <div className="mt-3 pt-3 border-t bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <span className="text-blue-800 font-semibold">Lancado no estoque:</span>
                        <span className="ml-2">{item.produto_nome}</span>
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
            </div>

            {/* Rodape com Acoes */}
            {notaSelecionada.status === 'pendente' && (
              <div className="sticky bottom-0 bg-white border-t px-6 py-4 space-y-3">
                {/* Secao de Rateio - ANTES de processar */}
                <div className="bg-gray-50 border border-gray-200 rounded p-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-gray-700">
                      Distribuicao (informativo para relatorios)
                    </h4>
                    <div className="text-xs text-gray-500">
                      Estoque unificado - Classificacao apenas para analises
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'loja')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'loja'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      Loja
                    </button>
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'online')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'online'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      Online
                    </button>
                    <button
                      onClick={() => salvarTipoRateio(notaSelecionada.id, 'parcial')}
                      disabled={loading}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        tipoRateio === 'parcial'
                          ? 'bg-gray-800 text-white'
                          : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-100'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      Parcial
                    </button>
                    
                    {(notaSelecionada.percentual_online > 0 || notaSelecionada.tipo_rateio) && (
                      <div className="ml-auto flex gap-3 text-xs text-gray-600">
                        <span>Online: {(notaSelecionada.percentual_online || 0).toFixed(0)}%</span>
                        <span>Loja: {(notaSelecionada.percentual_loja || 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>

                  {tipoRateio === 'parcial' && (
                    <div className="mt-2 text-xs text-gray-600 bg-gray-100 rounded p-2">
                      Defina a quantidade destinada ao <strong>estoque online</strong> em cada produto acima. O sistema calcula automaticamente a % baseado nos valores.
                    </div>
                  )}
                </div>

                {/* Barra de Status e Botoes de Acao */}
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    {notaSelecionada.itens.filter(i => i.produto_id).length} de {notaSelecionada.itens.length} produtos vinculados
                  </div>
                  <div className="flex gap-3">
                    {notaSelecionada.entrada_estoque_realizada ? (
                      <button
                        onClick={() => reverterNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                        disabled={loading}
                        className="px-6 py-2 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 disabled:bg-gray-400"
                      >
                        {loading ? 'Revertendo...' : 'Reverter Entrada'}
                      </button>
                    ) : (
                      <>
                        {!notaSelecionada.entrada_estoque_realizada && (
                          <button
                            onClick={() => excluirNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                            disabled={loading}
                            className="px-6 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400"
                          >
                            Excluir Nota
                          </button>
                        )}
                        {notaSelecionada.itens.some(i => i.produto_id) && (
                          <>
                            <button
                              onClick={() => carregarPreviewProcessamento(notaSelecionada.id)}
                              disabled={loading}
                              className="px-6 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400"
                            >
                              Revisar Precos
                            </button>
                            <button
                              onClick={() => processarNota(notaSelecionada.id)}
                              disabled={loading}
                              className="px-6 py-2 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400"
                            >
                              {loading ? 'Processando...' : 'Processar Nota'}
                            </button>
                          </>
                        )}
                      </>
                    )}
                    <button
                      onClick={() => {
                        setMostrarDetalhes(false);
                        setNotaSelecionada(null);
                      }}
                      className="px-6 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
                    >
                      Fechar
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal de Criar Produto */}
      {mostrarModalCriarProduto && itemSelecionadoParaCriar && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">Criar Novo Produto</h2>
                <p className="text-sm text-gray-600">A partir do item da NF-e</p>
              </div>
              <button
                onClick={() => {
                  setMostrarModalCriarProduto(false);
                  setItemSelecionadoParaCriar(null);
                  setSugestaoSku(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                X
              </button>
            </div>

            <div className="px-6 py-4">
              {carregandoSugestao ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-600">Gerando sugestoes de SKU...</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Informações do Item da NF-e */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="font-semibold text-blue-900 mb-2">Dados da NF-e:</div>
                    <div className="text-sm space-y-1 text-blue-800">
                      <div><strong>Descricao:</strong> {itemSelecionadoParaCriar.descricao}</div>
                      <div><strong>Codigo Fornecedor:</strong> {itemSelecionadoParaCriar.codigo_produto}</div>
                      <div><strong>NCM:</strong> {itemSelecionadoParaCriar.ncm}</div>
                      {itemSelecionadoParaCriar.ean && (
                        <div><strong>EAN:</strong> {itemSelecionadoParaCriar.ean}</div>
                      )}
                      <div><strong>Valor Unitario NF:</strong> R$ {itemSelecionadoParaCriar.valor_unitario.toFixed(2)}</div>
                      <div><strong>Custo de Aquisicao:</strong> R$ {formatarValorFiscal(obterCustoAquisicaoItem(itemSelecionadoParaCriar), 4)}</div>
                    </div>
                  </div>

                  {/* Alerta de SKU existente */}
                  {sugestaoSku?.ja_existe && (
                    <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <span className="text-2xl">⚠️</span>
                        <div className="flex-1">
                          <div className="font-semibold text-yellow-900 mb-2">
                            Codigo do fornecedor "{sugestaoSku.sku_proposto}" ja está em uso!
                          </div>
                          <div className="text-sm text-yellow-800 mb-3">
                            Produto existente: <strong>{sugestaoSku.produto_existente.nome}</strong><br/>
                            <span className="text-xs">Um SKU alternativo foi sugerido automaticamente. Você pode alterar se preferir.</span>
                          </div>
                          <div className="text-sm text-yellow-800 mb-2 font-semibold">
                            Outras opcoes de SKU disponíveis:
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {sugestaoSku.sugestoes.map(sug => (
                              <button
                                key={sug.sku}
                                onClick={() => setFormProduto({ ...formProduto, sku: sug.sku })}
                                className={`px-3 py-1 rounded-lg text-sm font-semibold transition-all ${
                                  formProduto.sku === sug.sku
                                    ? 'bg-blue-600 text-white shadow-md'
                                    : 'bg-white border border-blue-300 text-blue-700 hover:bg-blue-50'
                                } ${sug.padrao ? 'ring-2 ring-yellow-400' : ''}`}
                              >
                                {sug.sku} {sug.padrao && '⭐'}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sucesso - SKU disponivel */}
                  {sugestaoSku && !sugestaoSku.ja_existe && (
                    <div className="bg-green-50 border border-green-300 rounded-lg p-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">OK</span>
                        <div className="text-sm text-green-800">
                          <strong>SKU disponivel!</strong> O codigo do fornecedor pode ser usado diretamente.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Formulario */}
                  <div className="space-y-4">
                    {/* SKU */}
                    <div>
                      <label htmlFor="novo-produto-sku" className="block text-sm font-semibold text-gray-700 mb-1">
                        SKU / Codigo do Produto *
                        <span className="text-xs text-gray-500 font-normal ml-2">(Baseado no codigo do fornecedor)</span>
                      </label>
                      <input
                        id="novo-produto-sku"
                        type="text"
                        value={formProduto.sku}
                        onChange={(e) => setFormProduto({ ...formProduto, sku: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono"
                        placeholder="Ex: MGZ-12345"
                      />
                      <p className="text-xs text-gray-500 mt-1">Voce pode editar o SKU se preferir</p>
                    </div>

                    {/* Nome */}
                    <div>
                      <label htmlFor="novo-produto-nome" className="block text-sm font-semibold text-gray-700 mb-1">
                        Nome do Produto *
                      </label>
                      <input
                        id="novo-produto-nome"
                        type="text"
                        value={formProduto.nome}
                        onChange={(e) => setFormProduto({ ...formProduto, nome: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Nome completo do produto"
                      />
                    </div>

                    {/* Descricao */}
                    <div>
                      <label htmlFor="novo-produto-descricao" className="block text-sm font-semibold text-gray-700 mb-1">
                        Descricao
                      </label>
                      <textarea
                        id="novo-produto-descricao"
                        value={formProduto.descricao}
                        onChange={(e) => setFormProduto({ ...formProduto, descricao: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        rows="2"
                        placeholder="Descricao detalhada (opcional)"
                      />
                    </div>

                    {/* Precos */}
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label htmlFor="novo-produto-preco-custo" className="block text-sm font-semibold text-gray-700 mb-1">
                          Preco de Custo *
                        </label>
                        <input
                          id="novo-produto-preco-custo"
                          type="number"
                          step="0.01"
                          value={formProduto.preco_custo}
                          onChange={(e) => {
                            const custo = e.target.value;
                            const margem = Number.parseFloat(formProduto.margem_lucro) || 0;
                            setFormProduto({ 
                              ...formProduto, 
                              preco_custo: custo,
                              preco_venda: custo ? calcularPrecoVenda(Number.parseFloat(custo), margem) : ''
                            });
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label htmlFor="novo-produto-margem" className="block text-sm font-semibold text-gray-700 mb-1">
                          Margem (%) *
                        </label>
                        <input
                          id="novo-produto-margem"
                          type="number"
                          step="0.01"
                          value={formProduto.margem_lucro}
                          onChange={(e) => {
                            const margem = e.target.value;
                            const custo = Number.parseFloat(formProduto.preco_custo) || 0;
                            setFormProduto({ 
                              ...formProduto, 
                              margem_lucro: margem,
                              preco_venda: custo && margem ? calcularPrecoVenda(custo, Number.parseFloat(margem)) : ''
                            });
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label htmlFor="novo-produto-preco-venda" className="block text-sm font-semibold text-gray-700 mb-1">
                          Preco de Venda *
                        </label>
                        <input
                          id="novo-produto-preco-venda"
                          type="number"
                          step="0.01"
                          value={formProduto.preco_venda}
                          onChange={(e) => {
                            const venda = e.target.value;
                            const custo = Number.parseFloat(formProduto.preco_custo) || 0;
                            setFormProduto({ 
                              ...formProduto, 
                              preco_venda: venda,
                              margem_lucro: custo && venda ? calcularMargemLucro(custo, Number.parseFloat(venda)) : ''
                            });
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>

                    {/* Estoque */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label htmlFor="novo-produto-estoque-minimo" className="block text-sm font-semibold text-gray-700 mb-1">
                          Estoque Minimo
                        </label>
                        <input
                          id="novo-produto-estoque-minimo"
                          type="number"
                          value={formProduto.estoque_minimo}
                          onChange={(e) => setFormProduto({ ...formProduto, estoque_minimo: Number.parseInt(e.target.value) })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label htmlFor="novo-produto-estoque-maximo" className="block text-sm font-semibold text-gray-700 mb-1">
                          Estoque Maximo
                        </label>
                        <input
                          id="novo-produto-estoque-maximo"
                          type="number"
                          value={formProduto.estoque_maximo}
                          onChange={(e) => setFormProduto({ ...formProduto, estoque_maximo: Number.parseInt(e.target.value) })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Rodapé */}
            <div className="sticky bottom-0 bg-white border-t px-6 py-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  setMostrarModalCriarProduto(false);
                  setItemSelecionadoParaCriar(null);
                  setSugestaoSku(null);
                }}
                className="px-6 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={criarProdutoNovo}
                disabled={
                  loading || 
                  !formProduto.sku || 
                  !formProduto.nome || 
                  !formProduto.preco_custo || 
                  Number.parseFloat(formProduto.preco_custo) <= 0 || 
                  !formProduto.preco_venda || 
                  Number.parseFloat(formProduto.preco_venda) <= 0
                }
                className="px-6 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? 'Criando...' : 'Criar e Vincular Produto'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Visualização da Nota */}
      {mostrarVisualizacao && notaSelecionada && (
        <div className="fixed inset-0 z-50 bg-black/50">
          <div className="bg-white w-full h-full overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      setMostrarVisualizacao(false);
                      setNotaSelecionada(null);
                    }}
                    className="px-3 py-1.5 rounded-md bg-white/15 hover:bg-white/25 text-sm font-semibold transition-colors"
                  >
                    ← Voltar
                  </button>
                  <div>
                    <h2 className="text-xl font-bold">NF-e {notaSelecionada.numero_nota}</h2>
                    <p className="text-blue-100 text-sm mt-1">Serie: {notaSelecionada.serie}</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setMostrarVisualizacao(false);
                    setNotaSelecionada(null);
                  }}
                  className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
                  title="Fechar"
                >
                  X
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {/* Informações da Nota */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Dados da Nota</h3>
                  <div className="space-y-1.5 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Data Emissao:</span>
                      <span className="font-semibold">{new Date(notaSelecionada.data_emissao).toLocaleDateString('pt-BR')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status:</span>
                      <span>{getStatusBadge(notaSelecionada.status)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Valor Total:</span>
                      <span className="font-bold text-green-600">R$ {notaSelecionada.valor_total.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Fornecedor</h3>
                  <div className="space-y-1.5 text-sm">
                    <div>
                      <span className="text-gray-600">Nome:</span>
                      <div className="font-semibold">{notaSelecionada.fornecedor_nome}</div>
                    </div>
                    <div>
                      <span className="text-gray-600">CNPJ:</span>
                      <div className="font-mono text-xs">{notaSelecionada.fornecedor_cnpj}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chave de Acesso */}
              <div className="mb-4 p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Chave de Acesso</div>
                <div className="font-mono text-xs break-all">{notaSelecionada.chave_acesso}</div>
              </div>

              {/* Status de Vinculação */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-blue-600">{notaSelecionada.itens?.length || 0}</div>
                  <div className="text-xs text-gray-600">Total Itens</div>
                </div>
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-green-600">{notaSelecionada.produtos_vinculados}</div>
                  <div className="text-xs text-gray-600">Vinculados</div>
                </div>
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-orange-600">{notaSelecionada.produtos_nao_vinculados}</div>
                  <div className="text-xs text-gray-600">Nao Vinculados</div>
                </div>
              </div>

              {/* Itens da Nota */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-2">Itens da Nota</h3>
                <div className="space-y-2">
                  {notaSelecionada.itens?.map((item, index) => (
                    <div key={item.id} className="border border-gray-200 rounded-lg p-3">
                      <div className="flex justify-between items-start mb-1.5">
                        <div className="flex-1">
                          <div className="font-semibold text-gray-800 text-sm">{item.descricao}</div>
                          <div className="text-xs text-gray-500 mt-1">
                            Codigo: {item.codigo_produto} | NCM: {item.ncm}
                          </div>
                        </div>
                        {item.vinculado ? (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">
                            Vinculado
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-semibold rounded">
                            ⚠ Não Vinculado
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs mt-2">
                        <div>
                          <span className="text-gray-600">Qtd:</span>
                          <div className="font-semibold">{item.quantidade}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Unit:</span>
                          <div className="font-semibold">R$ {item.valor_unitario.toFixed(2)}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Custo Aq.:</span>
                          <div className="font-semibold text-amber-700">R$ {formatarValorFiscal(obterCustoAquisicaoItem(item), 4)}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">Total:</span>
                          <div className="font-semibold text-green-600">R$ {item.valor_total.toFixed(2)}</div>
                        </div>
                        <div>
                          <span className="text-gray-600">CFOP:</span>
                          <div className="font-semibold">{item.cfop}</div>
                        </div>
                      </div>

                            <CardFiscal nota={notaSelecionada} item={item} composicao={item.composicao_custo} />

                      {/* Lote e Validade */}
                      {(item.lote || item.data_validade) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2 text-xs">
                          {item.lote && (
                            <div className="bg-purple-50 border border-purple-200 rounded p-2">
                              <span className="text-gray-600">Lote:</span>
                              <div className="font-semibold text-purple-800">{item.lote}</div>
                            </div>
                          )}
                          {item.data_validade && (
                            <div className="bg-orange-50 border border-orange-200 rounded p-2">
                              <span className="text-gray-600">📅 Validade:</span>
                              <div className="font-semibold text-orange-800">
                                {new Date(item.data_validade).toLocaleDateString('pt-BR')}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {item.vinculado && item.produto_nome && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <span className="text-xs text-gray-600">→ Produto vinculado: </span>
                          <span className="text-sm font-semibold text-blue-600">{item.produto_nome}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t p-4 md:p-6 bg-gray-50 flex flex-wrap justify-between items-center gap-3">
              <div className="text-sm text-gray-600">
                {notaSelecionada.entrada_estoque_realizada ? (
                  <span className="text-green-600 font-semibold">✅ Entrada realizada no estoque</span>
                ) : (
                  <span className="text-orange-600 font-semibold">⚠️ Entrada ainda nao processada</span>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {notaSelecionada.status === 'pendente' && notaSelecionada.produtos_vinculados > 0 && !notaSelecionada.entrada_estoque_realizada && (
                  <>
                    <button
                      onClick={() => {
                        setMostrarVisualizacao(false);
                        processarNota(notaSelecionada.id);
                      }}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold"
                    >
                      💰 Revisar Precos e Processar
                    </button>
                  </>
                )}
                {notaSelecionada.status === 'pendente' && (
                  <button
                    onClick={() => {
                      setMostrarVisualizacao(false);
                      abrirDetalhes(notaSelecionada.id);
                    }}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold"
                  >
                    🔗 Vincular Produtos
                  </button>
                )}
                <button
                  onClick={() => {
                    setMostrarVisualizacao(false);
                    setNotaSelecionada(null);
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
                >
                  Voltar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Revisão de Preços */}
      {mostrarRevisaoPrecos && previewProcessamento && (
        <div className="fixed inset-0 z-50 bg-black/50">
          <div className="bg-white w-full h-full overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-slate-900 text-white p-4 md:p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      setMostrarRevisaoPrecos(false);
                      setPreviewProcessamento(null);
                      setInputsRevisaoPrecos({});
                      if (notaSelecionada) {
                        setMostrarVisualizacao(true);
                      }
                    }}
                    className="px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/20 text-sm font-semibold transition-colors"
                  >
                    ← Voltar
                  </button>
                  <div>
                    <h2 className="text-xl md:text-2xl font-bold">Revisao de Precos e Custos</h2>
                    <p className="text-slate-300 mt-1 text-sm">
                      NF-e {previewProcessamento.numero_nota} - {previewProcessamento.fornecedor_nome}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Resumo de Alterações */}
            <div className="px-4 md:px-6 py-3 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-semibold text-gray-700">Filtrar:</span>
                {(() => {
                  // Adaptar para estrutura flat ou aninhada
                  const itensVinculados = previewProcessamento.itens.filter(i => 
                    i.produto_vinculado !== null || i.produto_id !== null
                  );
                  const aumentos = itensVinculados.filter(i => {
                    const variacao = i.produto_vinculado?.variacao_custo_percentual || i.variacao_custo_percentual || 0;
                    return variacao > 0;
                  }).length;
                  const reducoes = itensVinculados.filter(i => {
                    const variacao = i.produto_vinculado?.variacao_custo_percentual || i.variacao_custo_percentual || 0;
                    return variacao < 0;
                  }).length;
                  const iguais = itensVinculados.filter(i => {
                    const variacao = i.produto_vinculado?.variacao_custo_percentual || i.variacao_custo_percentual || 0;
                    return variacao === 0;
                  }).length;
                  const total = itensVinculados.length;
                  
                  return (
                    <>
                      <button
                        onClick={() => setFiltroCusto('todos')}
                        className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                          filtroCusto === 'todos' 
                            ? 'bg-slate-800 text-white' 
                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        Todos ({total})
                      </button>
                      
                      {aumentos > 0 && (
                        <button
                          onClick={() => setFiltroCusto('aumentou')}
                          className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                            filtroCusto === 'aumentou' 
                              ? 'bg-red-600 text-white' 
                              : 'bg-white border border-red-200 text-red-700 hover:bg-red-50'
                          }`}
                        >
                          {aumentos} custo{aumentos > 1 ? 's' : ''} maior{aumentos > 1 ? 'es' : ''}
                        </button>
                      )}
                      
                      {reducoes > 0 && (
                        <button
                          onClick={() => setFiltroCusto('diminuiu')}
                          className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                            filtroCusto === 'diminuiu' 
                              ? 'bg-green-700 text-white' 
                              : 'bg-white border border-green-200 text-green-700 hover:bg-green-50'
                          }`}
                        >
                          {reducoes} custo{reducoes > 1 ? 's' : ''} menor{reducoes > 1 ? 'es' : ''}
                        </button>
                      )}
                      
                      {iguais > 0 && (
                        <button
                          onClick={() => setFiltroCusto('igual')}
                          className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                            filtroCusto === 'igual' 
                              ? 'bg-gray-700 text-white' 
                              : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          {iguais} sem alteração
                        </button>
                      )}

                      <div className="ml-auto flex items-center gap-2">
                        <button
                          onClick={exportarRelatorioCustosMaioresCSV}
                          disabled={gerandoRelatorioCustos || aumentos === 0}
                          className="px-3 py-1 rounded text-sm font-semibold bg-slate-700 text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {gerandoRelatorioCustos ? 'Gerando...' : 'Exportar CSV custos maiores'}
                        </button>
                        <button
                          onClick={exportarRelatorioCustosMaioresPDF}
                          disabled={gerandoRelatorioCustos || aumentos === 0}
                          className="px-3 py-1 rounded text-sm font-semibold bg-slate-700 text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {gerandoRelatorioCustos ? 'Gerando...' : 'Exportar PDF custos maiores'}
                        </button>
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6">
              <div className="space-y-6">
                {previewProcessamento.itens
                  .filter(item => {
                    // Verificar se tem produto vinculado (pode estar em produto_vinculado ou produto_id)
                    const vinculado = item.produto_vinculado !== null || item.produto_id !== null;
                    
                    if (!vinculado) return false;
                    
                    // Pegar variação de custo (pode estar em produto_vinculado ou diretamente no item)
                    const custoVariacao = item.produto_vinculado?.variacao_custo_percentual || item.variacao_custo_percentual || 0;
                    
                    if (filtroCusto === 'todos') return true;
                    if (filtroCusto === 'aumentou') return custoVariacao > 0;
                    if (filtroCusto === 'diminuiu') return custoVariacao < 0;
                    if (filtroCusto === 'igual') return custoVariacao === 0;
                    return true;
                  })
                  .map((item) => {
                  // Adaptar para estrutura flat ou aninhada
                  const produtoVinc = item.produto_vinculado || {
                    produto_id: item.produto_id,
                    produto_nome: item.produto_nome,
                    produto_codigo: item.produto_codigo,
                    produto_ean: item.produto_ean,
                    custo_anterior: item.custo_anterior,
                    custo_novo: item.custo_novo,
                    variacao_custo_percentual: item.variacao_custo_percentual,
                    preco_venda_atual: item.preco_venda_atual,
                    margem_atual: item.margem_atual,
                    estoque_atual: item.estoque_atual
                  };
                  
                  if (!produtoVinc.produto_id) return null;
                  
                  if (!produtoVinc.produto_id) return null;
                  
                  const custoVariacao = produtoVinc.variacao_custo_percentual || 0;
                  const custoAumentou = custoVariacao > 0;
                  const margemReferencia = Number(
                    produtoVinc.margem_atual ??
                    calcularMargem(produtoVinc.preco_venda_atual || 0, produtoVinc.custo_anterior || 0)
                  );
                  const margemProjetadaComCustoNovo = calcularMargem(
                    produtoVinc.preco_venda_atual || 0,
                    produtoVinc.custo_novo || 0
                  );
                  
                  const precosAtuais = precosAjustados[produtoVinc.produto_id] || {
                    preco_venda: produtoVinc.preco_venda_atual || 0,
                    margem: produtoVinc.margem_projetada_custo_novo ?? margemProjetadaComCustoNovo
                  };

                  const camposTexto = inputsRevisaoPrecos[produtoVinc.produto_id] || {
                    preco_venda: formatBRL(precosAtuais.preco_venda),
                    margem: formatBRL(precosAtuais.margem),
                  };

                  const tooltipMargem =
                    `Margem = ((Preço de Venda - Custo) / Preço de Venda) × 100\n` +
                    `Com os valores atuais:\n` +
                    `(${formatBRL(precosAtuais.preco_venda)} - ${formatBRL(produtoVinc.custo_novo || 0)}) / ${formatBRL(precosAtuais.preco_venda)} × 100\n` +
                    `Resultado: ${formatPercent(precosAtuais.margem)}`;

                  return (
                    <div key={item.item_id} className="border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all">
                      {/* Header com nome do produto e quantidade */}
                      <div className="bg-gray-100 border-b border-gray-200 p-4">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h3 className="font-semibold text-xl text-gray-900 mb-1">{produtoVinc.produto_nome}</h3>
                            <p className="text-sm text-gray-600">
                              SKU: {produtoVinc.produto_codigo || 'Nao informado'} | EAN: {produtoVinc.produto_ean || 'Nao informado'}
                            </p>
                          </div>
                          <div className="text-right">
                            <button
                              onClick={() => buscarHistoricoPrecos(produtoVinc.produto_id, produtoVinc.produto_nome)}
                              className="px-3 py-1 border border-gray-300 text-gray-700 hover:bg-gray-50 rounded text-sm font-medium transition-colors"
                            >
                              Historico
                            </button>
                            <div className="mt-1 text-sm text-gray-700">
                              Quantidade <strong>{item.quantidade_efetiva_nf || item.quantidade || item.quantidade_nf || 0}</strong>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="p-5 bg-white space-y-4">
                        {/* Comparação de Custos */}
                        <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                          <div>
                            <div className="text-xs text-gray-500 mb-1 flex items-center justify-between">
                              <span>Custo Anterior</span>
                            </div>
                            <div className="text-2xl font-bold text-gray-700">
                              {formatMoneyBRL(produtoVinc.custo_anterior || 0)}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500 mb-1 flex items-center justify-between">
                              <span>Custo Novo</span>
                              <TooltipComposicao 
                                custo={produtoVinc.custo_novo} 
                                composicao={item.composicao_custo}
                                texto="detalhar"
                              />
                            </div>
                            <div className="text-2xl font-bold text-gray-900">
                              {formatMoneyBRL(produtoVinc.custo_novo || 0)}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500 mb-1">Variacao</div>
                            <div className={`text-2xl font-bold ${custoAumentou ? 'text-red-600' : custoVariacao < 0 ? 'text-emerald-700' : 'text-gray-600'}`}>
                              {custoVariacao > 0 ? '↗' : custoVariacao < 0 ? '↘' : '➡'} {formatPercent(Math.abs(custoVariacao))}
                            </div>
                          </div>
                        </div>

                        {/* Campos de Preço e Margem */}
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-semibold text-gray-700 mb-2">
                              Preco de Venda
                            </label>
                            <div className="relative">
                              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">R$</span>
                              <input
                                type="text"
                                inputMode="decimal"
                                value={camposTexto.preco_venda}
                                onChange={(e) => atualizarPrecoVenda(
                                  produtoVinc.produto_id,
                                  e.target.value,
                                  produtoVinc.custo_novo
                                )}
                                onBlur={() => normalizarCamposRevisaoPrecos(produtoVinc.produto_id)}
                                className="w-full pl-10 pr-3 py-3 border-2 border-gray-300 rounded-lg text-xl font-bold focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              />
                            </div>
                            <div className="mt-1 text-xs text-gray-500">
                              Anterior: {formatMoneyBRL(produtoVinc.preco_venda_atual || 0)}
                            </div>
                          </div>

                          <div>
                            <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                              Margem de Lucro
                              <span className="text-gray-400 cursor-help" title={tooltipMargem}>ⓘ</span>
                            </label>
                            <div className="relative">
                              <input
                                type="text"
                                inputMode="decimal"
                                value={camposTexto.margem}
                                onChange={(e) => atualizarMargem(
                                  produtoVinc.produto_id,
                                  e.target.value,
                                  produtoVinc.custo_novo
                                )}
                                onBlur={() => normalizarCamposRevisaoPrecos(produtoVinc.produto_id)}
                                className="w-full pr-10 pl-3 py-3 border-2 border-gray-300 rounded-lg text-xl font-bold focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              />
                              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">%</span>
                            </div>
                            <div className="mt-1 text-xs text-gray-500">
                              Com o novo custo
                            </div>
                          </div>
                        </div>

                        {/* Análise Comparativa */}
                        <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                          <h4 className="text-sm font-semibold text-gray-700 mb-3">Referencia dos valores anteriores</h4>
                          <div className="grid grid-cols-3 gap-4 text-center">
                            <div>
                              <div className="text-xs text-gray-600 mb-1">Custo Anterior</div>
                              <div className="text-lg font-bold text-gray-700">{formatMoneyBRL(produtoVinc.custo_anterior || 0)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-600 mb-1">Preco Anterior</div>
                              <div className="text-lg font-bold text-gray-700">{formatMoneyBRL(produtoVinc.preco_venda_atual || 0)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-600 mb-1">Margem Anterior</div>
                              <div className="text-lg font-bold text-gray-700">{formatPercent(margemReferencia)}</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                }).filter(Boolean)}
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 p-4 md:p-6 bg-gray-50 flex flex-wrap justify-between items-center gap-3">
              <button
                onClick={() => {
                  setMostrarRevisaoPrecos(false);
                  setPreviewProcessamento(null);
                  setInputsRevisaoPrecos({});
                  if (notaSelecionada) {
                    setMostrarVisualizacao(true);
                  }
                }}
                className="px-6 py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg font-semibold transition-colors"
              >
                Voltar
              </button>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-sm text-gray-600">Valor Total da Nota</div>
                  <div className="text-2xl font-bold text-green-600">
                    R$ {previewProcessamento.valor_total.toFixed(2)}
                  </div>
                </div>
                <button
                  onClick={confirmarProcessamento}
                  disabled={loading}
                  className="px-8 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold text-lg shadow disabled:opacity-50 transition-all"
                >
                  {loading ? 'Processando...' : 'Confirmar e Processar Nota'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Histórico de Preços */}
      {mostrarHistoricoPrecos && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6">
              <h2 className="text-2xl font-bold">📊 Histórico de Alterações de Preços</h2>
              {produtoHistorico && (
                <p className="mt-2 text-purple-100">
                  {produtoHistorico.nome}
                </p>
              )}
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto flex-1">
              {carregandoHistorico ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-600"></div>
                </div>
              ) : historicoPrecos.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500 text-lg">Nenhuma alteração de preco registrada</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {historicoPrecos.map((hist) => (
                    <div key={hist.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                      {/* Header do Item */}
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-2xl">
                              {hist.motivo === 'nfe_entrada' ? '📦' : 
                               hist.motivo === 'nfe_revisao_precos' ? '💰' : 
                               hist.motivo === 'manual' ? '✏️' : '📝'}
                            </span>
                            <span className="font-semibold text-gray-800">
                              {hist.motivo === 'nfe_entrada' ? 'Entrada NF-e' :
                               hist.motivo === 'nfe_revisao_precos' ? 'Revisão de Preços' :
                               hist.motivo === 'manual' ? 'Ajuste Manual' :
                               hist.motivo}
                            </span>
                          </div>
                          {hist.referencia && (
                            <p className="text-sm text-gray-600 mt-1">{hist.referencia}</p>
                          )}
                          {hist.nota_numero && (
                            <p className="text-sm text-blue-600 mt-1">Nota: {hist.nota_numero}</p>
                          )}
                        </div>
                        <div className="text-right text-sm text-gray-500">
                          {new Date(hist.data).toLocaleString('pt-BR')}
                          {hist.usuario && (
                            <div className="text-xs mt-1">{hist.usuario}</div>
                          )}
                        </div>
                      </div>

                      {/* Alterações de Preço */}
                      <div className="grid grid-cols-2 gap-4">
                        {/* Custo */}
                        {hist.preco_custo_anterior !== null && hist.preco_custo_novo !== null && (
                          <div className="bg-blue-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 font-semibold mb-2">💵 CUSTO</div>
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-sm text-gray-500">Anterior</div>
                                <div className="text-lg font-bold">R$ {hist.preco_custo_anterior.toFixed(2)}</div>
                              </div>
                              <div className="text-2xl">→</div>
                              <div>
                                <div className="text-sm text-gray-500">Novo</div>
                                <div className="text-lg font-bold text-blue-700">R$ {hist.preco_custo_novo.toFixed(2)}</div>
                              </div>
                            </div>
                            {hist.variacao_custo_percentual !== null && hist.variacao_custo_percentual !== 0 && (
                              <div className={`mt-2 text-sm font-semibold text-center ${
                                hist.variacao_custo_percentual > 0 ? 'text-red-600' : 'text-green-600'
                              }`}>
                                {hist.variacao_custo_percentual > 0 ? '↑' : '↓'} {Math.abs(hist.variacao_custo_percentual).toFixed(2)}%
                              </div>
                            )}
                          </div>
                        )}

                        {/* Preço de Venda */}
                        {hist.preco_venda_anterior !== null && hist.preco_venda_novo !== null && (
                          <div className="bg-green-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 font-semibold mb-2">💲 PREÇO DE VENDA</div>
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-sm text-gray-500">Anterior</div>
                                <div className="text-lg font-bold">R$ {hist.preco_venda_anterior.toFixed(2)}</div>
                              </div>
                              <div className="text-2xl">→</div>
                              <div>
                                <div className="text-sm text-gray-500">Novo</div>
                                <div className="text-lg font-bold text-green-700">R$ {hist.preco_venda_novo.toFixed(2)}</div>
                              </div>
                            </div>
                            {hist.variacao_venda_percentual !== null && hist.variacao_venda_percentual !== 0 && (
                              <div className={`mt-2 text-sm font-semibold text-center ${
                                hist.variacao_venda_percentual > 0 ? 'text-green-600' : 'text-red-600'
                              }`}>
                                {hist.variacao_venda_percentual > 0 ? '↑' : '↓'} {Math.abs(hist.variacao_venda_percentual).toFixed(2)}%
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Margens */}
                      {hist.margem_anterior !== null && hist.margem_nova !== null && (
                        <div className="mt-3 bg-purple-50 rounded-lg p-3">
                          <div className="text-xs text-gray-600 font-semibold mb-2">📈 MARGEM DE LUCRO</div>
                          <div className="flex items-center justify-around">
                            <div className="text-center">
                              <div className="text-sm text-gray-500">Anterior</div>
                              <div className="text-xl font-bold">{hist.margem_anterior.toFixed(1)}%</div>
                            </div>
                            <div className="text-2xl">→</div>
                            <div className="text-center">
                              <div className="text-sm text-gray-500">Nova</div>
                              <div className="text-xl font-bold text-purple-700">{hist.margem_nova.toFixed(1)}%</div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Observações */}
                      {hist.observacoes && (
                        <div className="mt-3 text-sm text-gray-600 italic bg-gray-50 rounded p-2">
                          {hist.observacoes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t p-6 bg-gray-50">
              <button
                onClick={() => {
                  setMostrarHistoricoPrecos(false);
                  setHistoricoPrecos([]);
                  setProdutoHistorico(null);
                }}
                className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Resultado do Lote */}
      {mostrarModalLote && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white p-6">
              <h2 className="text-2xl font-bold">
                📦 Resultado do Processamento em Lote
              </h2>
              {resultadoLote && (
                <p className="mt-2">
                  {resultadoLote.sucessos} sucesso(s) | {resultadoLote.erros} erro(s) | Total: {resultadoLote.total_arquivos}
                </p>
              )}
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto flex-1">
              {uploadingLote && !resultadoLote && (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-green-600 mb-4"></div>
                  <p className="text-lg text-gray-600">Processando arquivos...</p>
                </div>
              )}

              {resultadoLote && (
                <>
                  {/* Resumo */}
                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="bg-gray-100 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-blue-600">{resultadoLote.total_arquivos}</div>
                      <div className="text-sm text-gray-600">Total</div>
                    </div>
                    <div className="bg-green-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-green-600">{resultadoLote.sucessos}</div>
                      <div className="text-sm text-gray-600">Sucessos</div>
                    </div>
                    <div className="bg-red-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-red-600">{resultadoLote.erros}</div>
                      <div className="text-sm text-gray-600">Erros</div>
                    </div>
                  </div>

                  {/* Lista de Resultados */}
                  <div className="space-y-3">
                    {resultadoLote.resultados.map((resultado, idx) => (
                      <div
                        key={idx}
                        className={`border rounded-lg p-4 ${
                          resultado.sucesso
                            ? 'bg-green-50 border-green-200'
                            : 'bg-red-50 border-red-200'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-2xl">
                                {resultado.sucesso ? '✅' : '❌'}
                              </span>
                              <span className="font-semibold text-gray-800">
                                {resultado.arquivo}
                              </span>
                            </div>
                            
                            {resultado.sucesso ? (
                              <div className="text-sm space-y-1">
                                <p className="text-gray-700">
                                  <strong>Nota:</strong> {resultado.numero_nota}
                                </p>
                                <p className="text-gray-700">
                                  <strong>Fornecedor:</strong> {resultado.fornecedor}
                                </p>
                                <p className="text-gray-700">
                                  <strong>Valor:</strong> R$ {resultado.valor_total?.toFixed(2)}
                                </p>
                                <p className="text-gray-700">
                                  <strong>Produtos:</strong> {resultado.produtos_vinculados} vinculados, {resultado.produtos_nao_vinculados} nao vinculados
                                </p>
                              </div>
                            ) : (
                              <p className="text-sm text-red-700">{resultado.mensagem}</p>
                            )}
                          </div>
                          <span className="text-sm text-gray-500 ml-4">#{resultado.ordem}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="border-t p-6 bg-gray-50">
              <button
                onClick={() => {
                  setMostrarModalLote(false);
                  setResultadoLote(null);
                }}
                disabled={uploadingLote}
                className="w-full px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-semibold disabled:opacity-50 transition-colors"
              >
                {uploadingLote ? '⏳ Processando...' : 'Fechar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EntradaXML;
