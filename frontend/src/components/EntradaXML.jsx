import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import { getAccessToken } from '../auth/tokenStorage';
import { toast } from 'react-hot-toast';
import { formatBRL, formatMoneyBRL, formatPercent } from '../utils/formatters';
import CardFiscal from './CardFiscal';
import ExportActionButton from './ui/ExportActionButton';
import TooltipComposicao from './TooltipComposicao';
import EntradaXmlCriarProdutoModal from './entrada-xml/EntradaXmlCriarProdutoModal';
import EntradaXmlHistoricoPrecosModal from './entrada-xml/EntradaXmlHistoricoPrecosModal';
import EntradaXmlHeader from './entrada-xml/EntradaXmlHeader';
import EntradaXmlMetricas from './entrada-xml/EntradaXmlMetricas';
import EntradaXmlNotasTable from './entrada-xml/EntradaXmlNotasTable';
import EntradaXmlRascunhoDevolucaoModal from './entrada-xml/EntradaXmlRascunhoDevolucaoModal';
import EntradaXmlRevisaoPrecosModal from './entrada-xml/EntradaXmlRevisaoPrecosModal';
import EntradaXmlResultadoLoteModal from './entrada-xml/EntradaXmlResultadoLoteModal';
import EntradaXmlSefazPanels from './entrada-xml/EntradaXmlSefazPanels';
import EntradaXmlVisualizacaoNotaModal from './entrada-xml/EntradaXmlVisualizacaoNotaModal';
import SegmentedControl from './ui/SegmentedControl';

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

const CONFERENCIA_STATUS_META = {
  nao_iniciada: {
    label: 'Nao conferida',
    cls: 'bg-gray-100 text-gray-700 border-gray-200',
  },
  sem_divergencia: {
    label: 'Conferida sem divergencias',
    cls: 'bg-green-100 text-green-800 border-green-200',
  },
  com_divergencia: {
    label: 'Conferida com divergencias',
    cls: 'bg-orange-100 text-orange-800 border-orange-200',
  },
};

const BASE_CALCULO_MARGEM_OPCOES = [
  {
    value: 'nf',
    label: 'Custo da NF',
    descricao: 'Padrao. Usa o custo fiscal da NF como base da margem.',
  },
  {
    value: 'sistema',
    label: 'Custo no sistema',
    descricao: 'Usa o custo que sera aplicado no processamento da entrada.',
  },
];

const ACAO_CONFERENCIA_OPCOES = [
  { value: 'sem_acao', label: 'Sem acao' },
  { value: 'contatar_fornecedor', label: 'Contatar fornecedor' },
  { value: 'reposicao_fornecedor', label: 'Pedir reposicao' },
  { value: 'nf_devolucao', label: 'NF de devolucao' },
  { value: 'ajuste_interno', label: 'Ajuste interno' },
];

function normalizarNumeroConferencia(valor, fallback = 0) {
  const numero = Number.parseFloat(String(valor ?? '').replace(',', '.'));
  if (!Number.isFinite(numero)) return fallback;
  return Math.max(0, numero);
}

function obterDraftConferenciaItem(item) {
  const quantidadeNF = Number(item?.quantidade ?? item?.quantidade_nf ?? 0);
  const quantidadeConferida = Math.max(
    0,
    Math.min(
      Number(item?.quantidade_conferida ?? quantidadeNF),
      quantidadeNF,
    ),
  );
  const quantidadeAvariada = Math.max(
    0,
    Math.min(
      Number(item?.quantidade_avariada ?? 0),
      Math.max(0, quantidadeNF - quantidadeConferida),
    ),
  );

  return {
    quantidade_conferida: quantidadeConferida,
    quantidade_avariada: quantidadeAvariada,
    observacao_conferencia: item?.observacao_conferencia || '',
    acao_sugerida: item?.acao_sugerida || 'sem_acao',
  };
}

function calcularConferenciaItem(item, draft) {
  const quantidadeNF = Number(item?.quantidade ?? item?.quantidade_nf ?? 0);
  const base = draft || obterDraftConferenciaItem(item);
  const quantidadeConferida = Math.max(
    0,
    Math.min(Number(base?.quantidade_conferida ?? quantidadeNF), quantidadeNF),
  );
  const quantidadeAvariada = Math.max(
    0,
    Math.min(Number(base?.quantidade_avariada ?? 0), Math.max(0, quantidadeNF - quantidadeConferida)),
  );
  const quantidadeFaltante = Math.max(0, quantidadeNF - quantidadeConferida - quantidadeAvariada);
  const temAvaria = quantidadeAvariada > 0;
  const temFalta = quantidadeFaltante > 0;

  let statusConferencia = 'ok';
  if (temAvaria && temFalta) statusConferencia = 'falta_avaria';
  else if (temAvaria) statusConferencia = 'avaria';
  else if (temFalta) statusConferencia = 'falta';

  const temDivergencia = statusConferencia !== 'ok';
  const acaoSugerida = temDivergencia
    ? (base?.acao_sugerida || (temAvaria ? 'nf_devolucao' : 'contatar_fornecedor'))
    : 'sem_acao';

  return {
    quantidadeNF,
    quantidadeConferida,
    quantidadeAvariada,
    quantidadeFaltante,
    statusConferencia,
    temDivergencia,
    acaoSugerida,
    observacaoConferencia: base?.observacao_conferencia || '',
  };
}

function montarConferenciaState(nota) {
  const state = {};
  (nota?.itens || []).forEach((item) => {
    state[item.id] = obterDraftConferenciaItem(item);
  });
  return state;
}

function calcularResumoConferencia(nota, conferenciaItens) {
  const itens = nota?.itens || [];
  const resumo = {
    itens_total: itens.length,
    itens_ok: 0,
    itens_com_divergencia: 0,
    itens_com_avaria: 0,
    quantidade_total_nf: 0,
    quantidade_total_conferida: 0,
    quantidade_total_avariada: 0,
    quantidade_total_faltante: 0,
  };

  itens.forEach((item) => {
    const conferenciaItem = calcularConferenciaItem(item, conferenciaItens?.[item.id]);
    resumo.quantidade_total_nf += conferenciaItem.quantidadeNF;
    resumo.quantidade_total_conferida += conferenciaItem.quantidadeConferida;
    resumo.quantidade_total_avariada += conferenciaItem.quantidadeAvariada;
    resumo.quantidade_total_faltante += conferenciaItem.quantidadeFaltante;

    if (conferenciaItem.temDivergencia) {
      resumo.itens_com_divergencia += 1;
    } else {
      resumo.itens_ok += 1;
    }

    if (conferenciaItem.quantidadeAvariada > 0) {
      resumo.itens_com_avaria += 1;
    }
  });

  const statusBase = nota?.conferencia?.status || nota?.conferencia_status || 'nao_iniciada';
  const status = statusBase === 'nao_iniciada'
    ? 'nao_iniciada'
    : (resumo.itens_com_divergencia > 0 ? 'com_divergencia' : 'sem_divergencia');

  return {
    ...resumo,
    status,
    tem_nf_devolucao_sugerida: resumo.itens_com_avaria > 0,
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
    variacao_custo_percentual: item.variacao_custo_percentual,
    preco_venda_atual: item.preco_venda_atual,
    margem_atual: item.margem_atual,
    margem_projetada_custo_novo: item.margem_projetada_custo_novo,
    estoque_atual: item.estoque_atual,
  };

  const obterCustoBasePreviewItem = (item) => Number(
    item?.produto_vinculado?.custo_novo ??
    item?.custo_novo ??
    item?.custo_aquisicao_unitario_nf ??
    item?.custo_unitario_efetivo_nf ??
    item?.valor_unitario_nf ??
    0
  );

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
        const variacao = Number(obterResumoCustoItem(item).variacaoCustoPercentual || 0);
        return produto.produto_id && variacao > 0;
      });

    if (itensAumentaram.length === 0) {
      throw new Error('Nenhum produto com aumento de custo nesta NF.');
    }

    const linhas = await Promise.all(itensAumentaram.map(async (item) => {
      const produto = normalizarProdutoPreview(item);
      const resumoCusto = obterResumoCustoItem(item);
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
        resumoCusto.custoSistema ??
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
        variacao_percentual: Number(resumoCusto.variacaoCustoPercentual || 0),
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
      const { jsPDF } = await import('jspdf');
      const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
      const marginX = 10;
      const pageWidth = doc.internal.pageSize.getWidth();
      const usableWidth = pageWidth - (marginX * 2);
      const tableStartY = 30;
      const minRowHeight = 7;
      const lineHeight = 3.4;

      const colunas = [
        { key: 'produto_nome', label: 'Produto', width: 58 },
        { key: 'sku', label: 'SKU', width: 17 },
        { key: 'nf_atual_numero', label: 'NF', width: 14 },
        { key: 'custo_bruto_unitario', label: 'Bruto', width: 15 },
        { key: 'frete_unitario', label: 'Frete', width: 14 },
        { key: 'seguro_unitario', label: 'Seguro', width: 14 },
        { key: 'outras_despesas_unitario', label: 'Desp.', width: 14 },
        { key: 'desconto_unitario', label: 'Desc.', width: 14 },
        { key: 'icms_st_unitario', label: 'ICMS ST', width: 15 },
        { key: 'ipi_unitario', label: 'IPI', width: 13 },
        { key: 'icms_unitario', label: 'ICMS', width: 13 },
        { key: 'custo_aquisicao', label: 'Custo Total', width: 18 },
        { key: 'nf_anterior_numero', label: 'NF Ant.', width: 15 },
        { key: 'nf_anterior_custo', label: 'Custo Ant.', width: 18 },
        { key: 'variacao_percentual', label: 'Var %', width: 14 },
        { key: 'variacao_absoluta', label: 'Delta R$', width: 17 }
      ];

      const larguraColunas = colunas.reduce((acc, col) => acc + col.width, 0);
      const escala = larguraColunas > usableWidth ? usableWidth / larguraColunas : 1;
      colunas.forEach((col) => { col.width = Number((col.width * escala).toFixed(2)); });

      const quebrarTexto = (texto, larguraMax, maxLinhas = 2) => {
        const valor = String(texto ?? '');
        if (!valor) return [''];
        const linhas = doc.splitTextToSize(valor, Math.max(4, larguraMax));

        if (linhas.length <= maxLinhas) {
          return linhas;
        }

        const visiveis = linhas.slice(0, maxLinhas);
        const ultima = visiveis[maxLinhas - 1] || '';
        let corte = ultima;

        while (corte.length > 1 && doc.getTextWidth(`${corte}...`) > larguraMax) {
          corte = corte.slice(0, -1);
        }

        visiveis[maxLinhas - 1] = `${corte}...`;
        return visiveis;
      };

      const desenharTextoCelula = (texto, x, y, largura, alinhamento = 'left', maxLinhas = 2) => {
        const linhas = quebrarTexto(texto, largura - 2, maxLinhas);
        linhas.forEach((linha, index) => {
          const textX = alinhamento === 'right' ? x + largura - 1 : x + 1;
          doc.text(linha, textX, y + 4 + (index * lineHeight), {
            align: alinhamento,
            maxWidth: largura - 2,
          });
        });
      };

      const renderCabecalhoPagina = () => {
        doc.setTextColor(30, 41, 59);
        doc.setFontSize(12);
        doc.text(`Relatorio de custos maiores - NF ${previewProcessamento?.numero_nota || ''}`, marginX, 10);
        doc.setFontSize(9);
        doc.text(`Fornecedor: ${previewProcessamento?.fornecedor_nome || 'Nao informado'}`, marginX, 16);
        doc.text(`Data de emissao NF atual: ${formatarDataRelatorio(previewProcessamento?.data_emissao)}`, marginX, 21);

        doc.setFillColor(226, 232, 240);
        doc.rect(marginX, tableStartY, usableWidth, minRowHeight, 'F');
        doc.setDrawColor(203, 213, 225);
        doc.setTextColor(15, 23, 42);
        doc.setFontSize(7);

        let xAtual = marginX;
        colunas.forEach((coluna) => {
          doc.rect(xAtual, tableStartY, coluna.width, minRowHeight);
          desenharTextoCelula(coluna.label, xAtual, tableStartY, coluna.width, 'left', 1);
          xAtual += coluna.width;
        });
      };

      renderCabecalhoPagina();

      let y = tableStartY + minRowHeight;
      linhas.forEach((linha) => {
        const comp = linha.composicao_custo?.componentes_unitario || {};
        const rowData = {
          produto_nome: linha.produto_nome || '-',
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

        const maxLinhasProduto = quebrarTexto(rowData.produto_nome, colunas[0].width - 2, 3).length;
        const maxLinhasSku = quebrarTexto(rowData.sku, colunas[1].width - 2, 2).length;
        const rowHeight = Math.max(minRowHeight, 4 + (Math.max(maxLinhasProduto, maxLinhasSku, 1) * lineHeight));

        if (y + rowHeight > 195) {
          doc.addPage();
          renderCabecalhoPagina();
          y = tableStartY + minRowHeight;
        }

        let xAtual = marginX;
        doc.setDrawColor(226, 232, 240);
        doc.setTextColor(15, 23, 42);
        doc.setFontSize(6.5);

        colunas.forEach((coluna) => {
          doc.rect(xAtual, y, coluna.width, rowHeight);
          const valor = rowData[coluna.key] || '';
          const alinhamento = coluna.key === 'produto_nome' || coluna.key === 'sku' || coluna.key.includes('numero')
            ? 'left'
            : 'right';
          const maxLinhas = coluna.key === 'produto_nome' ? 3 : coluna.key === 'sku' ? 2 : 1;
          desenharTextoCelula(valor, xAtual, y, coluna.width, alinhamento, maxLinhas);
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
      aplicarNotaSelecionada(response.data);
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
        onTogglePainelSefaz={() => {
          setMostrarPainelSefaz((visivel) => !visivel);
          setMostrarConfigSefaz(false);
        }}
        onToggleConfigSefaz={() => {
          setMostrarConfigSefaz((visivel) => !visivel);
          if (!mostrarConfigSefaz) {
            carregarConfigSefaz();
          }
          setMostrarPainelSefaz(false);
        }}
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

            {resumoConferenciaAtual && (
              <div className="px-6 py-4 border-b bg-emerald-50/40">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-3">
                    <div className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${metaConferenciaAtual?.cls || 'bg-gray-100 text-gray-700 border-gray-200'}`}>
                      {metaConferenciaAtual?.label || 'Nao conferida'}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div className="rounded-lg border border-white/70 bg-white/80 p-3">
                        <div className="text-gray-500 text-xs uppercase tracking-wide">Itens OK</div>
                        <div className="font-bold text-lg text-emerald-700">{resumoConferenciaAtual.itens_ok}</div>
                      </div>
                      <div className="rounded-lg border border-white/70 bg-white/80 p-3">
                        <div className="text-gray-500 text-xs uppercase tracking-wide">Divergencias</div>
                        <div className="font-bold text-lg text-orange-700">{resumoConferenciaAtual.itens_com_divergencia}</div>
                      </div>
                      <div className="rounded-lg border border-white/70 bg-white/80 p-3">
                        <div className="text-gray-500 text-xs uppercase tracking-wide">Qtd recebida</div>
                        <div className="text-[11px] text-gray-500 mt-1">Entra no estoque</div>
                        <div className="font-bold text-lg text-slate-800">{formatarValorFiscal(resumoConferenciaAtual.quantidade_total_conferida, 2)}</div>
                      </div>
                      <div className="rounded-lg border border-white/70 bg-white/80 p-3">
                        <div className="text-gray-500 text-xs uppercase tracking-wide">Falta + Avaria</div>
                        <div className="font-bold text-lg text-rose-700">
                          {formatarValorFiscal(resumoConferenciaAtual.quantidade_total_faltante + resumoConferenciaAtual.quantidade_total_avariada, 2)}
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 max-w-3xl">
                      {notaSelecionada.status === 'pendente'
                        ? (
                          <>
                            A conferência nasce assumindo tudo certo. Se a carga estiver perfeita, basta clicar em <strong>Conferido</strong>. Só mexa nos itens com falta ou avaria.
                          </>
                        )
                        : 'Conferencia ja salva. Use as acoes de divergencia para gerar a tratativa sem precisar reverter a entrada.'}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {notaSelecionada.status === 'pendente' && (
                      <>
                        <button
                          onClick={() => setMostrarCamposConferencia((prev) => !prev)}
                          className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg font-semibold hover:bg-slate-100"
                        >
                          {mostrarCamposConferencia ? 'Ocultar ajuste manual' : 'Editar quantidades e avarias'}
                        </button>
                        <button
                          onClick={() => salvarConferenciaAtual()}
                          disabled={salvandoConferencia || desfazendoConferencia}
                          className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 disabled:opacity-60"
                        >
                          {salvandoConferencia
                            ? 'Salvando...'
                            : (resumoConferenciaAtual.status === 'nao_iniciada' ? 'Conferido' : 'Atualizar conferencia')}
                        </button>
                      </>
                    )}
                    {notaSelecionada.status === 'pendente' && resumoConferenciaAtual.status !== 'nao_iniciada' && (
                      <button
                        onClick={desfazerConferenciaAtual}
                        disabled={desfazendoConferencia || salvandoConferencia || Boolean(notaSelecionada?.entrada_estoque_realizada)}
                        className="px-4 py-2 border border-amber-300 bg-amber-50 text-amber-800 rounded-lg font-semibold hover:bg-amber-100 disabled:opacity-60"
                      >
                        {desfazendoConferencia ? 'Desfazendo...' : 'Desfazer conferencia'}
                      </button>
                    )}
                    {notaSelecionada.status !== 'pendente' && resumoConferenciaAtual.itens_com_divergencia > 0 && (
                      <>
                        <button
                          onClick={() => setMostrarCamposConferencia((prev) => !prev)}
                          className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg font-semibold hover:bg-slate-100"
                        >
                          {mostrarCamposConferencia ? 'Ocultar tratativas' : 'Abrir tratativas'}
                        </button>
                        <button
                          onClick={() => salvarConferenciaAtual()}
                          disabled={salvandoConferencia || desfazendoConferencia}
                          className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 disabled:opacity-60"
                        >
                          {salvandoConferencia ? 'Salvando...' : 'Salvar tratativas'}
                        </button>
                      </>
                    )}
                    {resumoConferenciaAtual.itens_com_divergencia > 0 && (
                      <>
                        <button
                          onClick={gerarPendenciaFornecedor}
                          disabled={criandoPendenciaFornecedor || salvandoConferencia || desfazendoConferencia}
                          className="px-4 py-2 border border-blue-200 bg-blue-50 text-blue-700 rounded-lg font-semibold hover:bg-blue-100 disabled:opacity-60"
                        >
                          {criandoPendenciaFornecedor ? 'Gerando...' : 'Gerar pendencia fornecedor'}
                        </button>
                        <button
                          onClick={gerarRascunhoDevolucao}
                          disabled={gerandoRascunhoDevolucao || salvandoConferencia || desfazendoConferencia}
                          className="px-4 py-2 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 disabled:opacity-60"
                        >
                          {gerandoRascunhoDevolucao ? 'Gerando...' : 'NF Devolucao das Divergencias'}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {mostrarCamposConferencia && (
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Observacao geral da conferencia</label>
                    <textarea
                      value={conferenciaObservacaoGeral}
                      onChange={(e) => setConferenciaObservacaoGeral(e.target.value)}
                      rows="2"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500"
                      placeholder="Ex.: faltou 1 unidade do item X e 2 vieram avariadas."
                    />
                  </div>
                )}
              </div>
            )}

            {/* Itens da Nota */}
            <div className="px-6 py-4">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-bold text-xl text-gray-800">
                    Produtos da Nota ({itensExibidosNota.length}
                    {filtroItensNota === 'divergencias' ? ` de ${itensNotaDetalhe.length}` : ''})
                  </h3>
                  {itensComDivergenciaDetalhe.length > 0 && (
                    <p className="mt-1 text-xs text-orange-700">
                      {itensComDivergenciaDetalhe.length} item(ns) com divergencia ou tratativa pendente.
                    </p>
                  )}
                </div>
                
                <div className="flex flex-wrap items-center gap-2">
                  {itensComDivergenciaDetalhe.length > 0 && (
                    <SegmentedControl
                      ariaLabel="Filtrar itens da nota"
                      size="md"
                      value={filtroItensNota}
                      onChange={setFiltroItensNota}
                      options={[
                        { value: 'todos', label: 'Todos' },
                        {
                          value: 'divergencias',
                          label: `Com divergencia (${itensComDivergenciaDetalhe.length})`,
                          activeClassName: 'bg-orange-100 text-orange-800 shadow-sm',
                          onSelect: () => setMostrarCamposConferencia(true),
                        },
                      ]}
                    />
                  )}

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
              </div>
              
              <div className="space-y-3">
                {itensExibidosNota.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                    Nenhum produto encontrado para este filtro.
                  </div>
                )}
                {itensExibidosNota.map(item => {
                  const divergencias = detectarDivergencias(item);
                  const temDivergencia = divergencias.length > 0;
                  const itemAjustado = aplicarMultiplicadorPackAoItem(item, multiplicadoresPack);
                  const packConfig = obterConfiguracaoPackItem(item, multiplicadoresPack);
                  const conferenciaItem = calcularConferenciaItem(item, conferenciaItens[item.id]);
                  const mostrarTratativaItem = mostrarCamposConferencia && (
                    notaSelecionada.status === 'pendente' ||
                    conferenciaItem.temDivergencia ||
                    Boolean(item.tem_divergencia)
                  );
                  const podeEditarQuantidadesItem = notaSelecionada.status === 'pendente';
                  
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

                      {mostrarTratativaItem && (
                        <div className="border-t border-emerald-200 bg-emerald-50/60 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                            <div>
                              <h4 className="font-semibold text-emerald-900">Conferencia fisica</h4>
                              <p className="text-xs text-emerald-800">
                                {podeEditarQuantidadesItem
                                  ? 'Ajuste apenas o que realmente entrou, o que faltou e o que veio avariado.'
                                  : 'Quantidade ja lancada no estoque. Ajuste aqui a tratativa e a observacao da divergencia.'}
                              </p>
                            </div>
                            <span className={`inline-flex items-center rounded-full border px-2 py-1 text-xs font-semibold ${
                              conferenciaItem.temDivergencia
                                ? 'bg-orange-100 text-orange-800 border-orange-200'
                                : 'bg-green-100 text-green-800 border-green-200'
                            }`}>
                              {conferenciaItem.temDivergencia ? `Divergencia: ${conferenciaItem.statusConferencia}` : 'OK'}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Qtd NF</label>
                              <input
                                type="number"
                                value={conferenciaItem.quantidadeNF}
                                disabled
                                className="w-full rounded border border-gray-300 bg-gray-100 px-3 py-2 text-sm font-semibold"
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Qtd recebida</label>
                              <input
                                type="number"
                                min="0"
                                max={conferenciaItem.quantidadeNF}
                                step="0.01"
                                disabled={!podeEditarQuantidadesItem}
                                value={conferenciaItens[item.id]?.quantidade_conferida ?? conferenciaItem.quantidadeConferida}
                                onChange={(e) => atualizarCampoConferenciaItem(item, 'quantidade_conferida', e.target.value)}
                                className={`w-full rounded border px-3 py-2 text-sm font-semibold focus:ring-2 focus:ring-emerald-500 ${
                                  podeEditarQuantidadesItem
                                    ? 'border-emerald-300'
                                    : 'border-gray-300 bg-gray-100 text-gray-600'
                                }`}
                              />
                              <div className="mt-1 text-[11px] text-emerald-700 font-medium">Entra no estoque</div>
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Qtd avariada</label>
                              <input
                                type="number"
                                min="0"
                                max={Math.max(0, conferenciaItem.quantidadeNF - conferenciaItem.quantidadeConferida)}
                                step="0.01"
                                disabled={!podeEditarQuantidadesItem}
                                value={conferenciaItens[item.id]?.quantidade_avariada ?? conferenciaItem.quantidadeAvariada}
                                onChange={(e) => atualizarCampoConferenciaItem(item, 'quantidade_avariada', e.target.value)}
                                className={`w-full rounded border px-3 py-2 text-sm font-semibold focus:ring-2 focus:ring-orange-500 ${
                                  podeEditarQuantidadesItem
                                    ? 'border-orange-300'
                                    : 'border-gray-300 bg-gray-100 text-gray-600'
                                }`}
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">Qtd faltante</label>
                              <input
                                type="number"
                                value={conferenciaItem.quantidadeFaltante.toFixed(2)}
                                disabled
                                className="w-full rounded border border-gray-300 bg-gray-100 px-3 py-2 text-sm font-semibold"
                              />
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-3 mt-3">
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Tratativa sugerida</label>
                              <select
                                value={conferenciaItens[item.id]?.acao_sugerida ?? conferenciaItem.acaoSugerida}
                                onChange={(e) => atualizarCampoConferenciaItem(item, 'acao_sugerida', e.target.value)}
                                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500"
                              >
                                {ACAO_CONFERENCIA_OPCOES.map((opcao) => (
                                  <option key={opcao.value} value={opcao.value}>
                                    {opcao.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-gray-700 mb-1">Observacao</label>
                              <input
                                type="text"
                                value={conferenciaItens[item.id]?.observacao_conferencia ?? conferenciaItem.observacaoConferencia}
                                onChange={(e) => atualizarCampoConferenciaItem(item, 'observacao_conferencia', e.target.value)}
                                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500"
                                placeholder="Ex.: faltou 1 unidade, embalagem avariada, solicitar reposicao..."
                              />
                            </div>
                          </div>
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
                              Ajuste de custo
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
