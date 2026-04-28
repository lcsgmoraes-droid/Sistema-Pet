import React, { useState, useEffect, useMemo, useRef } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';
import ModalConfronto from './compras/ModalConfronto';

const FORM_DATA_INICIAL = {
  fornecedor_id: '',
  data_prevista_entrega: '',
  valor_frete: '0',
  valor_desconto: '0',
  observacoes: '',
  itens: []
};

const ITEM_FORM_INICIAL = {
  produto_id: '',
  quantidade_pedida: '',
  preco_unitario: ''
};

const GRUPO_FORNECEDOR_FORM_INICIAL = {
  id: null,
  nome: '',
  descricao: '',
  fornecedor_principal_id: '',
  fornecedor_ids: []
};

const COLUNAS_DOCUMENTO_PEDIDO = [
  { chave: 'codigo', label: 'Codigo / SKU' },
  { chave: 'produto', label: 'Descricao' },
  { chave: 'quantidade', label: 'Quantidade' },
  { chave: 'preco_unitario', label: 'Custo unitario' },
  { chave: 'desconto', label: 'Desconto' },
  { chave: 'total', label: 'Total' },
];

const COLUNAS_DOCUMENTO_COMPLETO = COLUNAS_DOCUMENTO_PEDIDO.map((coluna) => coluna.chave);
const COLUNAS_DOCUMENTO_FORNECEDOR = ['codigo', 'produto', 'quantidade'];
const COLUNAS_DOCUMENTO_FINANCEIRAS = ['preco_unitario', 'desconto', 'total'];

const normalizarColunasDocumentoPedido = (colunas = []) => {
  const candidatas = Array.isArray(colunas)
    ? colunas
    : String(colunas || '').split(',');

  const selecionadas = new Set(
    candidatas
      .map((coluna) => String(coluna || '').trim().toLowerCase())
      .filter(Boolean)
  );

  return COLUNAS_DOCUMENTO_COMPLETO.filter((coluna) => selecionadas.has(coluna));
};

const documentoTemColunasFinanceiras = (colunas = []) => (
  normalizarColunasDocumentoPedido(colunas).some((coluna) => COLUNAS_DOCUMENTO_FINANCEIRAS.includes(coluna))
);

const numeroSeguro = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : 0;
};

const textoNumeroSeguro = (valor, fallback = '0') => {
  if (valor === null || valor === undefined || valor === '') {
    return fallback;
  }

  return String(valor);
};

const normalizarItemPedido = (item = {}) => {
  const quantidade = numeroSeguro(item.quantidade_pedida);
  const preco = numeroSeguro(item.preco_unitario);
  const desconto = numeroSeguro(item.desconto_item);
  const totalInformado = Number(item.total ?? item.valor_total);
  const total = Number.isFinite(totalInformado)
    ? totalInformado
    : (preco - desconto) * quantidade;

  return {
    produto_id: Number(item.produto_id),
    produto_nome: item.produto_nome || item.nome || `Produto ${item.produto_id}`,
    produto_codigo: item.produto_codigo || item.codigo || item.sku || '',
    quantidade_pedida: quantidade,
    preco_unitario: preco,
    desconto_item: desconto,
    total
  };
};

const clonarItensPedido = (itens = []) => itens.map((item) => normalizarItemPedido(item));

const consolidarItensPedido = (itensBase = [], itensAdicionais = [], estrategia = 'somar') => {
  const mapa = new Map();

  const adicionarOuSomarItem = (item) => {
    const normalizado = normalizarItemPedido(item);
    const chave = Number(normalizado.produto_id);

    if (!Number.isFinite(chave) || chave <= 0) {
      return;
    }

    const existente = mapa.get(chave);
    if (!existente) {
      mapa.set(chave, normalizado);
      return;
    }

    if (estrategia === 'maior_quantidade') {
      const quantidadeExistente = numeroSeguro(existente.quantidade_pedida);
      const quantidadeNova = numeroSeguro(normalizado.quantidade_pedida);
      const itemEscolhido = quantidadeNova >= quantidadeExistente
        ? normalizado
        : existente;
      const preco = numeroSeguro(itemEscolhido.preco_unitario);
      const desconto = numeroSeguro(itemEscolhido.desconto_item);
      const quantidade = Math.max(quantidadeExistente, quantidadeNova);

      mapa.set(chave, {
        ...existente,
        ...normalizado,
        ...itemEscolhido,
        quantidade_pedida: quantidade,
        preco_unitario: preco,
        desconto_item: desconto,
        total: (preco - desconto) * quantidade
      });
      return;
    }

    const preco = numeroSeguro(normalizado.preco_unitario) || numeroSeguro(existente.preco_unitario);
    const desconto = numeroSeguro(normalizado.desconto_item) || numeroSeguro(existente.desconto_item);
    const quantidade = numeroSeguro(existente.quantidade_pedida) + numeroSeguro(normalizado.quantidade_pedida);

    mapa.set(chave, {
      ...existente,
      ...normalizado,
      preco_unitario: preco,
      desconto_item: desconto,
      quantidade_pedida: quantidade,
      total: (preco - desconto) * quantidade
    });
  };

  clonarItensPedido(itensBase).forEach(adicionarOuSomarItem);
  clonarItensPedido(itensAdicionais).forEach(adicionarOuSomarItem);

  return Array.from(mapa.values());
};

const converterPedidoParaFormData = (pedido) => ({
  fornecedor_id: pedido?.fornecedor_id?.toString() || '',
  data_prevista_entrega: pedido?.data_prevista_entrega
    ? new Date(pedido.data_prevista_entrega).toISOString().split('T')[0]
    : '',
  valor_frete: textoNumeroSeguro(pedido?.valor_frete, '0'),
  valor_desconto: textoNumeroSeguro(pedido?.valor_desconto, '0'),
  observacoes: pedido?.observacoes || '',
  itens: clonarItensPedido(
    (pedido?.itens || []).map((item) => ({
      produto_id: item.produto_id,
      produto_nome: item.produto_nome || `Produto ${item.produto_id}`,
      produto_codigo: item.produto_codigo || item.codigo || item.sku || '',
      quantidade_pedida: item.quantidade_pedida,
      preco_unitario: item.preco_unitario,
      desconto_item: item.desconto_item || 0,
      total: item.total ?? item.valor_total
    }))
  )
});

const extrairNomeArquivoCabecalho = (contentDisposition, fallback) => {
  if (!contentDisposition) {
    return fallback;
  }

  const matchUtf8 = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (matchUtf8?.[1]) {
    try {
      return decodeURIComponent(matchUtf8[1].trim());
    } catch (_error) {
      // ignora e tenta os outros formatos
    }
  }

  const matchQuoted = contentDisposition.match(/filename\s*=\s*"([^"]+)"/i);
  if (matchQuoted?.[1]) {
    return matchQuoted[1].trim();
  }

  const matchSimple = contentDisposition.match(/filename\s*=\s*([^;]+)/i);
  if (matchSimple?.[1]) {
    return matchSimple[1].trim().replace(/^"|"$/g, '');
  }

  return fallback;
};

const baixarArquivoResposta = (response, fallback) => {
  const contentDisposition = response?.headers?.['content-disposition'] || response?.headers?.['Content-Disposition'];
  const nomeArquivo = extrairNomeArquivoCabecalho(contentDisposition, fallback);
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', nomeArquivo);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

const PedidosCompra = () => {
  const [pedidos, setPedidos] = useState([]);
  const [fornecedores, setFornecedores] = useState([]);
  const [gruposFornecedores, setGruposFornecedores] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [modoEdicao, setModoEdicao] = useState(false);
  const [pedidoEditando, setPedidoEditando] = useState(null);
  const [pedidoSelecionado, setPedidoSelecionado] = useState(null);
  const [mostrarRecebimento, setMostrarRecebimento] = useState(false);
  const [mostrarConfronto, setMostrarConfronto] = useState(false);
  const [pedidoConfronto, setPedidoConfronto] = useState(null);
  
  // Modal de envio
  const [mostrarModalEnvio, setMostrarModalEnvio] = useState(false);
  const [pedidoParaEnviar, setPedidoParaEnviar] = useState(null);
  const [emailEnvioDisponivel, setEmailEnvioDisponivel] = useState(false);
  const [mostrarModalExportacao, setMostrarModalExportacao] = useState(false);
  const [pedidoParaExportar, setPedidoParaExportar] = useState(null);
  const [exportandoArquivo, setExportandoArquivo] = useState(false);
  const [colunasDocumentoPedido, setColunasDocumentoPedido] = useState(COLUNAS_DOCUMENTO_COMPLETO);
  const [dadosEnvio, setDadosEnvio] = useState({
    email: '',
    whatsapp: '',
    formatos: {
      pdf: true,
      excel: false
    }
  });

  // 💡 Modal de Sugestão Inteligente
  const [mostrarSugestao, setMostrarSugestao] = useState(false);
  const [sugestoes, setSugestoes] = useState([]);
  const [loadingSugestao, setLoadingSugestao] = useState(false);
  const [loadingPrepararSugestao, setLoadingPrepararSugestao] = useState(false);
  const [periodoSugestao, setPeriodoSugestao] = useState(90);
  const [diasCobertura, setDiasCobertura] = useState(30);
  const [apenasCriticos, setApenasCriticos] = useState(false);
  const [incluirAlerta, setIncluirAlerta] = useState(true);
  const [produtosSelecionados, setProdutosSelecionados] = useState([]);
  const [quantidadesEditadas, setQuantidadesEditadas] = useState({});
  const [filtroSugestao, setFiltroSugestao] = useState('');
  const [mostrarSoPreenchidos, setMostrarSoPreenchidos] = useState(false);
  const [marcasSelecionadas, setMarcasSelecionadas] = useState([]);
  const [mostrarFiltroMarcas, setMostrarFiltroMarcas] = useState(false);
  const [produtoEditandoQuantidade, setProdutoEditandoQuantidade] = useState(null);
  const [mostrarModalRascunhoSugestao, setMostrarModalRascunhoSugestao] = useState(false);
  const [contextoRascunhoSugestao, setContextoRascunhoSugestao] = useState(null);
  const [modoAplicacaoSugestao, setModoAplicacaoSugestao] = useState('merge');
  const [estrategiaMesclaItens, setEstrategiaMesclaItens] = useState('somar');
  const cabecalhoTabelaSugestaoRef = useRef(null);
  const corpoTabelaSugestaoRef = useRef(null);
  const filtroMarcasRef = useRef(null);

  const [formData, setFormData] = useState(FORM_DATA_INICIAL);

  const [itemForm, setItemForm] = useState(ITEM_FORM_INICIAL);

  // Estados para inputs digitáveis
  const [fornecedorTexto, setFornecedorTexto] = useState('');
  const [produtoTexto, setProdutoTexto] = useState('');
  const [mostrarSugestoesFornecedor, setMostrarSugestoesFornecedor] = useState(false);
  const [mostrarSugestoesProduto, setMostrarSugestoesProduto] = useState(false);
  const [incluirGrupoFornecedor, setIncluirGrupoFornecedor] = useState(false);
  const [mostrarModalGruposFornecedores, setMostrarModalGruposFornecedores] = useState(false);
  const [grupoFornecedorForm, setGrupoFornecedorForm] = useState(GRUPO_FORNECEDOR_FORM_INICIAL);
  const [salvandoGrupoFornecedor, setSalvandoGrupoFornecedor] = useState(false);

  const normalizarTexto = (texto = '') =>
    texto
      .toLowerCase()
      .normalize('NFD')
      .replaceAll(/[\u0300-\u036f]/g, '');

  const fornecedoresFiltrados = useMemo(() => {
    const termo = normalizarTexto(fornecedorTexto.trim());
    if (!termo) return fornecedores.slice(0, 12);

    return fornecedores
      .filter((f) => normalizarTexto(f.nome || '').includes(termo))
      .slice(0, 12);
  }, [fornecedores, fornecedorTexto]);

  const produtosFiltrados = useMemo(() => {
    const termo = normalizarTexto(produtoTexto.trim());
    if (!termo) return produtos.slice(0, 15);

    return produtos
      .filter((p) => normalizarTexto(p.nome || '').includes(termo))
      .slice(0, 15);
  }, [produtos, produtoTexto]);

  const selecionarFornecedor = (fornecedor) => {
    setFornecedorTexto(fornecedor.nome || '');
    setFormData((prev) => ({ ...prev, fornecedor_id: fornecedor.id.toString(), itens: [] }));
    setIncluirGrupoFornecedor(Boolean(obterGrupoDoFornecedor(fornecedor.id)));
    setItemForm(ITEM_FORM_INICIAL);
    setProdutoTexto('');
    setMostrarSugestoesFornecedor(false);
    // Limpar sugestões do fornecedor anterior
    limparEstadosSugestao();
    carregarProdutosFornecedor(fornecedor.id);
  };

  const selecionarProduto = (produto) => {
    preencherPreco(produto.id.toString());
    setMostrarSugestoesProduto(false);
  };

  const obterFornecedorPorId = (fornecedorId) =>
    fornecedores.find((f) => Number(f.id) === Number(fornecedorId));

  const obterGrupoDoFornecedor = (fornecedorId) => {
    const id = Number(fornecedorId);
    if (!Number.isFinite(id) || id <= 0) {
      return null;
    }

    const fornecedor = obterFornecedorPorId(id);
    const grupoIdDireto = Number(fornecedor?.fornecedor_grupo_id);
    if (Number.isFinite(grupoIdDireto) && grupoIdDireto > 0) {
      return gruposFornecedores.find((grupo) => Number(grupo.id) === grupoIdDireto) || null;
    }

    return gruposFornecedores.find((grupo) => (
      Array.isArray(grupo.fornecedor_ids)
      && grupo.fornecedor_ids.some((grupoFornecedorId) => Number(grupoFornecedorId) === id)
    )) || null;
  };

  const grupoFornecedorAtual = useMemo(
    () => obterGrupoDoFornecedor(formData.fornecedor_id),
    [formData.fornecedor_id, fornecedores, gruposFornecedores],
  );

  const obterParametrosGrupoFornecedor = (fornecedorId = formData.fornecedor_id) => {
    const grupo = obterGrupoDoFornecedor(fornecedorId);
    if (!grupo || !incluirGrupoFornecedor) {
      return {};
    }

    return {
      incluir_grupo_fornecedor: true,
      fornecedor_grupo_id: grupo.id,
    };
  };

  const extrairEmailFornecedor = (fornecedor) => {
    if (!fornecedor) return '';

    const candidatos = [
      fornecedor.email,
      fornecedor.email_principal,
      fornecedor.email_comercial,
      fornecedor.contato_email,
      fornecedor?.contato?.email,
    ];

    const emailValido = candidatos.find(
      (valor) => typeof valor === 'string' && valor.includes('@'),
    );

    return (emailValido || '').trim();
  };

  const obterSnapshotFormularioAtual = () => ({
    ...formData,
    fornecedor_id: formData.fornecedor_id?.toString() || '',
    data_prevista_entrega: formData.data_prevista_entrega || '',
    valor_frete: textoNumeroSeguro(formData.valor_frete, '0'),
    valor_desconto: textoNumeroSeguro(formData.valor_desconto, '0'),
    observacoes: formData.observacoes || '',
    itens: clonarItensPedido(formData.itens),
  });

  const limparEstadosSugestao = () => {
    setSugestoes([]);
    setProdutosSelecionados([]);
    setQuantidadesEditadas({});
    setFiltroSugestao('');
    setMostrarSoPreenchidos(false);
    setMarcasSelecionadas([]);
    setMostrarFiltroMarcas(false);
    setProdutoEditandoQuantidade(null);
    setModoAplicacaoSugestao('merge');
  };

  const limparFormularioPedido = () => {
    setFormData(FORM_DATA_INICIAL);
    setItemForm(ITEM_FORM_INICIAL);
    setEstrategiaMesclaItens('somar');
    setFornecedorTexto('');
    setProdutoTexto('');
    setProdutos([]);
    setIncluirGrupoFornecedor(false);
    setMostrarSugestoesFornecedor(false);
    setMostrarSugestoesProduto(false);
    limparEstadosSugestao();
  };

  const fecharFormularioPedido = () => {
    setMostrarForm(false);
    setModoEdicao(false);
    setPedidoEditando(null);
    limparFormularioPedido();
  };

  const abrirNovoFormulario = () => {
    setModoEdicao(false);
    setPedidoEditando(null);
    limparFormularioPedido();
    setMostrarForm(true);
  };

  const combinarCabecalhoPedido = (formBase, formAtual) => ({
    fornecedor_id: formBase.fornecedor_id || formAtual.fornecedor_id || '',
    data_prevista_entrega: formAtual.data_prevista_entrega || formBase.data_prevista_entrega || '',
    valor_frete:
      numeroSeguro(formAtual.valor_frete) > 0
        ? textoNumeroSeguro(formAtual.valor_frete, '0')
        : textoNumeroSeguro(formBase.valor_frete, '0'),
    valor_desconto:
      numeroSeguro(formAtual.valor_desconto) > 0
        ? textoNumeroSeguro(formAtual.valor_desconto, '0')
        : textoNumeroSeguro(formBase.valor_desconto, '0'),
    observacoes: formAtual.observacoes?.trim() || formBase.observacoes || '',
  });

  const aplicarPedidoNoFormulario = async (
    pedidoCompleto,
    formDataOverride = null,
    options = {},
  ) => {
    const { mensagemSucesso = '', mostrarToast = false } = options;
    const fornecedorId = Number(pedidoCompleto?.fornecedor_id);
    const fornecedorSelecionado = obterFornecedorPorId(fornecedorId);
    const proximoFormData = formDataOverride || converterPedidoParaFormData(pedidoCompleto);

    setModoEdicao(true);
    setPedidoEditando(pedidoCompleto);
    setFormData(proximoFormData);
    setFornecedorTexto(fornecedorSelecionado?.nome || '');
    setIncluirGrupoFornecedor(Boolean(obterGrupoDoFornecedor(fornecedorId)));
    setItemForm(ITEM_FORM_INICIAL);
    setProdutoTexto('');
    setMostrarSugestoesProduto(false);
    setMostrarSugestoesFornecedor(false);
    setMostrarForm(true);
    limparEstadosSugestao();

    if (fornecedorId) {
      await carregarProdutosFornecedor(fornecedorId);
    }

    if (mostrarToast && mensagemSucesso) {
      toast.success(mensagemSucesso);
    }
  };

  const abrirModalSugestao = async (fornecedorId, modo = 'merge') => {
    setModoAplicacaoSugestao(modo);
    setMostrarSugestao(true);
    await buscarSugestoes(fornecedorId);
  };

  const abrirFluxoSugestaoInteligente = async () => {
    if (!formData.fornecedor_id) {
      toast.error('Selecione um fornecedor primeiro');
      return;
    }

    const fornecedorId = Number(formData.fornecedor_id);
    const snapshotFormulario = obterSnapshotFormularioAtual();
    const editandoMesmoRascunho =
      modoEdicao
      && pedidoEditando
      && Number(pedidoEditando.id) > 0
      && Number(pedidoEditando.fornecedor_id) === fornecedorId
      && pedidoEditando.status === 'rascunho';

    if (editandoMesmoRascunho) {
      setContextoRascunhoSugestao({
        tipo: 'atual',
        pedidoRascunho: pedidoEditando,
        pedidoNovo: snapshotFormulario,
        totalRascunhos: 1,
      });
      setMostrarModalRascunhoSugestao(true);
      return;
    }

    setLoadingPrepararSugestao(true);
    try {
      const response = await api.get(
        `/pedidos-compra/rascunho/fornecedor/${fornecedorId}`,
        { params: obterParametrosGrupoFornecedor(fornecedorId) },
      );
      const pedidoRascunho = response?.data?.pedido || null;

      if (pedidoRascunho) {
        setContextoRascunhoSugestao({
          tipo: 'externo',
          pedidoRascunho,
          pedidoNovo: snapshotFormulario,
          totalRascunhos: Number(response?.data?.total_rascunhos || 1),
        });
        setMostrarModalRascunhoSugestao(true);
        return;
      }

      await abrirModalSugestao(fornecedorId);
    } catch (error) {
      console.error('Erro ao verificar rascunho do fornecedor:', error);
      toast.error(error.response?.data?.detail || 'Erro ao verificar rascunho do fornecedor');
    } finally {
      setLoadingPrepararSugestao(false);
    }
  };

  const fecharModalRascunho = () => {
    setMostrarModalRascunhoSugestao(false);
    setContextoRascunhoSugestao(null);
  };

  const decidirAcaoRascunhoSugestao = async (acao) => {
    const contexto = contextoRascunhoSugestao;
    if (!contexto) {
      return;
    }

    const { pedidoRascunho, pedidoNovo, tipo } = contexto;
    const fornecedorId = Number(pedidoRascunho?.fornecedor_id || pedidoNovo?.fornecedor_id);

    fecharModalRascunho();
    setLoadingPrepararSugestao(true);

    try {
      if (acao === 'manter') {
      if (tipo === 'externo' && pedidoRascunho) {
        await aplicarPedidoNoFormulario(
          pedidoRascunho,
          converterPedidoParaFormData(pedidoRascunho),
          {
            mostrarToast: true,
            mensagemSucesso: 'Rascunho existente carregado e mantido como está.',
          },
        );
      } else {
        toast('O rascunho atual foi mantido sem aplicar nova sugestão.');
      }
      return;
    }

    if (tipo === 'externo' && pedidoRascunho) {
      const formRascunho = converterPedidoParaFormData(pedidoRascunho);
      const itensConsolidados = acao === 'mesclar'
        ? consolidarItensPedido(formRascunho.itens, pedidoNovo.itens, estrategiaMesclaItens)
        : clonarItensPedido(formRascunho.itens);
      const cabecalhoConsolidado = combinarCabecalhoPedido(formRascunho, pedidoNovo);

      await aplicarPedidoNoFormulario(
        pedidoRascunho,
        {
          ...formRascunho,
          ...cabecalhoConsolidado,
          itens: itensConsolidados,
        },
        {
          mostrarToast: true,
          mensagemSucesso: acao === 'mesclar'
            ? 'Rascunho existente carregado para mesclar com o pedido atual.'
            : 'Rascunho existente mantido e pronto para receber só a nova sugestão.',
        },
      );

      await abrirModalSugestao(
        fornecedorId,
        acao === 'substituir' ? 'replace' : 'merge',
      );
      return;
    }

    await abrirModalSugestao(
      fornecedorId,
      acao === 'substituir' ? 'replace' : 'merge',
    );
    } catch (error) {
      console.error('Erro ao preparar consolidação do rascunho:', error);
      toast.error(error.response?.data?.detail || 'Erro ao preparar a sugestão inteligente');
    } finally {
      setLoadingPrepararSugestao(false);
    }
  };

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    try {
      const [pedidosRes, fornecedoresRes, gruposRes, envioStatusRes] = await Promise.all([
        api.get('/pedidos-compra/'),
        api.get('/clientes/?tipo_cadastro=fornecedor&apenas_ativos=true'),
        api.get('/fornecedor-grupos/'),
        api.get('/pedidos-compra/envio/status').catch(() => ({ data: { email_configurado: false } }))
      ]);

      // Tratar resposta dos pedidos (pode ser array direto ou objeto paginado)
      const pedidosData = Array.isArray(pedidosRes.data) 
        ? pedidosRes.data 
        : (pedidosRes.data.items || pedidosRes.data.pedidos || []);
      
      // Tratar resposta dos fornecedores
      const fornecedoresData = Array.isArray(fornecedoresRes.data) 
        ? fornecedoresRes.data 
        : (fornecedoresRes.data.items || fornecedoresRes.data.clientes || []);
      const gruposData = Array.isArray(gruposRes.data)
        ? gruposRes.data
        : (gruposRes.data.items || gruposRes.data.grupos || []);

      setPedidos(pedidosData);
      setFornecedores(fornecedoresData);
      setGruposFornecedores(gruposData);
      setEmailEnvioDisponivel(Boolean(envioStatusRes?.data?.email_configurado));
      // NÃO carregar produtos aqui - apenas quando fornecedor for selecionado
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar dados');
    }
  };

  const carregarProdutosFornecedor = async (fornecedorId) => {
    if (!fornecedorId) {
      setProdutos([]);
      return;
    }
    try {
      const response = await api.get(
        `/produtos/?fornecedor_id=${fornecedorId}`
      );
      
      // API pode retornar array direto ou objeto paginado
      let produtosData;
      if (Array.isArray(response.data)) {
        produtosData = response.data;
      } else if (response.data.items) {
        produtosData = response.data.items;
      } else if (response.data.produtos) {
        produtosData = response.data.produtos;
      } else {
        produtosData = [];
      }
      
      if (produtosData.length === 0) {
        toast('⚠️ Este fornecedor não possui produtos vinculados. Edite os produtos para vincular ao fornecedor.');
      }
      
      setProdutos(produtosData);
    } catch (error) {
      console.error('Erro ao carregar produtos:', error);
      toast.error('Erro ao carregar produtos do fornecedor');
    }
  };

  const abrirNovoGrupoFornecedor = () => {
    const fornecedorId = Number(formData.fornecedor_id);
    setGrupoFornecedorForm({
      ...GRUPO_FORNECEDOR_FORM_INICIAL,
      fornecedor_principal_id: Number.isFinite(fornecedorId) && fornecedorId > 0 ? fornecedorId.toString() : '',
      fornecedor_ids: Number.isFinite(fornecedorId) && fornecedorId > 0 ? [fornecedorId] : [],
    });
    setMostrarModalGruposFornecedores(true);
  };

  const editarGrupoFornecedor = (grupo) => {
    setGrupoFornecedorForm({
      id: grupo.id,
      nome: grupo.nome || '',
      descricao: grupo.descricao || '',
      fornecedor_principal_id: grupo.fornecedor_principal_id?.toString() || '',
      fornecedor_ids: (grupo.fornecedor_ids || []).map((id) => Number(id)),
    });
  };

  const alternarFornecedorNoGrupoForm = (fornecedorId) => {
    const id = Number(fornecedorId);
    setGrupoFornecedorForm((prev) => {
      const idsAtuais = new Set((prev.fornecedor_ids || []).map((item) => Number(item)));
      if (idsAtuais.has(id)) {
        idsAtuais.delete(id);
      } else {
        idsAtuais.add(id);
      }

      const fornecedorIds = Array.from(idsAtuais).sort((a, b) => a - b);
      const principalAtual = Number(prev.fornecedor_principal_id);
      const fornecedorPrincipalValido = fornecedorIds.includes(principalAtual)
        ? prev.fornecedor_principal_id
        : (fornecedorIds[0]?.toString() || '');

      return {
        ...prev,
        fornecedor_ids: fornecedorIds,
        fornecedor_principal_id: fornecedorPrincipalValido,
      };
    });
  };

  const salvarGrupoFornecedor = async (event) => {
    event.preventDefault();

    const fornecedorIds = (grupoFornecedorForm.fornecedor_ids || [])
      .map((id) => Number(id))
      .filter((id) => Number.isFinite(id) && id > 0);

    if (!grupoFornecedorForm.nome.trim()) {
      toast.error('Informe o nome do grupo');
      return;
    }

    if (fornecedorIds.length < 2) {
      toast.error('Selecione pelo menos 2 CNPJs para unificar em grupo');
      return;
    }

    setSalvandoGrupoFornecedor(true);
    try {
      const payload = {
        nome: grupoFornecedorForm.nome.trim(),
        descricao: grupoFornecedorForm.descricao?.trim() || null,
        fornecedor_principal_id: Number(grupoFornecedorForm.fornecedor_principal_id) || fornecedorIds[0],
        fornecedor_ids: fornecedorIds,
        ativo: true,
      };

      if (grupoFornecedorForm.id) {
        await api.patch(`/fornecedor-grupos/${grupoFornecedorForm.id}`, payload);
        toast.success('Grupo de fornecedor atualizado');
      } else {
        await api.post('/fornecedor-grupos/', payload);
        toast.success('Grupo de fornecedor criado');
      }

      setGrupoFornecedorForm(GRUPO_FORNECEDOR_FORM_INICIAL);
      await carregarDados();
    } catch (error) {
      console.error('Erro ao salvar grupo de fornecedor:', error);
      toast.error(error.response?.data?.detail || 'Erro ao salvar grupo de fornecedor');
    } finally {
      setSalvandoGrupoFornecedor(false);
    }
  };

  const excluirGrupoFornecedor = async (grupo) => {
    const confirmar = window.confirm(`Excluir o grupo "${grupo.nome}" e liberar os fornecedores vinculados?`);
    if (!confirmar) {
      return;
    }

    try {
      await api.delete(`/fornecedor-grupos/${grupo.id}`);
      toast.success('Grupo de fornecedor excluido');
      if (grupoFornecedorForm.id === grupo.id) {
        setGrupoFornecedorForm(GRUPO_FORNECEDOR_FORM_INICIAL);
      }
      await carregarDados();
    } catch (error) {
      console.error('Erro ao excluir grupo de fornecedor:', error);
      toast.error(error.response?.data?.detail || 'Erro ao excluir grupo de fornecedor');
    }
  };

  const preencherPreco = (produtoId) => {
    const produto = produtos.find(p => p.id === parseInt(produtoId));
    if (produto) {
      setProdutoTexto(produto.nome);
      if (produto.preco_custo) {
        setItemForm({
          ...itemForm,
          produto_id: produtoId,
          preco_unitario: produto.preco_custo.toFixed(2)
        });
      } else {
        setItemForm({ ...itemForm, produto_id: produtoId });
      }
    }
  };

  const adicionarItem = () => {
    if (!itemForm.produto_id || !itemForm.quantidade_pedida || !itemForm.preco_unitario) {
      toast.error('Preencha todos os campos do item');
      return;
    }

    const produto = produtos.find(p => p.id === parseInt(itemForm.produto_id));
    const quantidade = parseFloat(itemForm.quantidade_pedida);
    const preco = parseFloat(itemForm.preco_unitario);
    const produtoId = parseInt(itemForm.produto_id);
    const produtoCodigo = produto?.codigo || produto?.sku || '';

    // Verificar se produto já existe no pedido
    const itemExistenteIndex = formData.itens.findIndex(item => item.produto_id === produtoId);
    
    if (itemExistenteIndex !== -1) {
      // Produto já existe - perguntar ao usuário
      const itemExistente = formData.itens[itemExistenteIndex];
      const confirmar = window.confirm(
        `⚠️ O produto "${produto.nome}" já está no pedido!\n\n` +
        `Quantidade atual: ${itemExistente.quantidade_pedida}\n` +
        `Preço atual: R$ ${itemExistente.preco_unitario.toFixed(2)}\n\n` +
        `Nova quantidade: ${quantidade}\n` +
        `Novo preço: R$ ${preco.toFixed(2)}\n\n` +
        `Deseja SOMAR a quantidade ao item existente?\n\n` +
        `✅ OK = Somar quantidade (${itemExistente.quantidade_pedida} + ${quantidade} = ${itemExistente.quantidade_pedida + quantidade})\n` +
        `❌ CANCELAR = Não adicionar`
      );

      if (confirmar) {
        // Somar quantidade ao item existente
        const novosItens = [...formData.itens];
        novosItens[itemExistenteIndex] = {
          ...itemExistente,
          produto_codigo: itemExistente.produto_codigo || produtoCodigo,
          quantidade_pedida: itemExistente.quantidade_pedida + quantidade,
          preco_unitario: preco, // Atualiza com o novo preço
          total: (itemExistente.quantidade_pedida + quantidade) * preco
        };

        setFormData({
          ...formData,
          itens: novosItens
        });

        toast.success(`✅ Quantidade somada! Total: ${itemExistente.quantidade_pedida + quantidade}`);
      } else {
        toast('Adição cancelada');
      }

      // Limpar form
      setProdutoTexto('');
      setMostrarSugestoesProduto(false);
      setItemForm(ITEM_FORM_INICIAL);
      return;
    }

    // Produto novo - adicionar normalmente
    setFormData({
      ...formData,
      itens: [
        ...formData.itens,
        {
          produto_id: produtoId,
          produto_nome: produto.nome,
          produto_codigo: produtoCodigo,
          quantidade_pedida: quantidade,
          preco_unitario: preco,
          desconto_item: 0,
          total: quantidade * preco
        }
      ]
    });

    // Limpar apenas os campos do item, mantendo o texto do produto limpo
    setProdutoTexto('');
    setMostrarSugestoesProduto(false);
    setItemForm(ITEM_FORM_INICIAL);
  };

  const removerItem = (index) => {
    setFormData({
      ...formData,
      itens: formData.itens.filter((_, i) => i !== index)
    });
  };

  const atualizarItemPedido = (index, campo, valor) => {
    setFormData((prev) => {
      const itens = prev.itens.map((item, itemIndex) => {
        if (itemIndex !== index) {
          return item;
        }

        const proximoItem = {
          ...item,
          [campo]: numeroSeguro(valor)
        };
        const quantidade = numeroSeguro(proximoItem.quantidade_pedida);
        const preco = numeroSeguro(proximoItem.preco_unitario);
        const desconto = numeroSeguro(proximoItem.desconto_item);

        return {
          ...proximoItem,
          quantidade_pedida: quantidade,
          preco_unitario: preco,
          desconto_item: desconto,
          total: (preco - desconto) * quantidade
        };
      });

      return {
        ...prev,
        itens
      };
    });
  };

  const obterSkuItemPedido = (item) => {
    if (item?.produto_codigo) {
      return item.produto_codigo;
    }

    const produto = produtos.find((produtoAtual) => produtoAtual.id === Number(item?.produto_id));
    return produto?.codigo || produto?.sku || '';
  };

  const copiarSkuItemPedido = async (item) => {
    const sku = obterSkuItemPedido(item);

    if (!sku) {
      toast.error('SKU não disponível para este item');
      return;
    }

    try {
      await navigator.clipboard.writeText(sku);
      toast.success(`SKU ${sku} copiado`);
    } catch (_error) {
      toast.error('Não foi possível copiar o SKU');
    }
  };

  const calcularTotal = () => {
    const subtotal = formData.itens.reduce((sum, item) => sum + item.total, 0);
    const frete = parseFloat(formData.valor_frete || 0);
    const desconto = parseFloat(formData.valor_desconto || 0);
    return subtotal + frete - desconto;
  };

  // 💡 FUNÇÕES DE SUGESTÃO INTELIGENTE
  const buscarSugestoes = async (fornecedorIdOverride = null) => {
    const fornecedorId = fornecedorIdOverride || formData.fornecedor_id;

    if (!fornecedorId) {
      toast.error('Selecione um fornecedor primeiro');
      return;
    }

    setLoadingSugestao(true);
    try {
      const response = await api.get(
        `/pedidos-compra/sugestao/${fornecedorId}`,
        {
          params: {
            periodo_dias: periodoSugestao,
            dias_cobertura: diasCobertura,
            apenas_criticos: apenasCriticos,
            incluir_alerta: incluirAlerta,
            marca_ids: marcasSelecionadas,
            ...obterParametrosGrupoFornecedor(fornecedorId)
          },
          timeout: 60000
        }
      );

      setSugestoes(response.data.sugestoes || []);
      setProdutosSelecionados([]);
      setQuantidadesEditadas({});

      if (response.data.sugestoes.length === 0) {
        toast('Nenhuma sugestão encontrada com os filtros aplicados');
      } else {
        toast.success(`${response.data.sugestoes.length} produtos analisados`);
      }
    } catch (error) {
      console.error('Erro ao buscar sugestões:', error);
      toast.error('Erro ao gerar sugestões');
    } finally {
      setLoadingSugestao(false);
    }
  };

  const toggleSelecionarProduto = (produtoId) => {
    setProdutosSelecionados(prev => 
      prev.includes(produtoId)
        ? prev.filter(id => id !== produtoId)
        : [...prev, produtoId]
    );
  };

  const sanitizarQuantidadeInteira = (valor) => {
    const somenteDigitos = String(valor ?? '').replace(/\D+/g, '');
    return somenteDigitos ? parseInt(somenteDigitos, 10) : 0;
  };

  const atualizarQuantidadeSugerida = (produtoId, novaQuantidade) => {
    setQuantidadesEditadas(prev => ({
      ...prev,
      [produtoId]: sanitizarQuantidadeInteira(novaQuantidade)
    }));
  };

  const obterQuantidadeFinal = (sugestao) => {
    return quantidadesEditadas[sugestao.produto_id] !== undefined 
      ? quantidadesEditadas[sugestao.produto_id] 
      : sugestao.quantidade_sugerida;
  };

  const obterQuantidadeInteira = (sugestao) => Math.max(0, Math.ceil(obterQuantidadeFinal(sugestao)));

  const sugestoesFiltradas = useMemo(() => {
    const q = filtroSugestao.trim().toLowerCase();
    return sugestoes.filter((s) => {
      const passaBusca = !q
        || (s.produto_nome || '').toLowerCase().includes(q)
        || (s.produto_sku || '').toLowerCase().includes(q)
        || (s.produto_codigo_barras || '').toLowerCase().includes(q);

      if (!passaBusca) {
        return false;
      }

      if (!mostrarSoPreenchidos) {
        return true;
      }

      if (produtoEditandoQuantidade === s.produto_id) {
        return true;
      }

      return obterQuantidadeInteira(s) > 0;
    });
  }, [
    sugestoes,
    filtroSugestao,
    mostrarSoPreenchidos,
    quantidadesEditadas,
    produtoEditandoQuantidade,
  ]);

  const marcasFornecedor = useMemo(() => {
    const mapa = new Map();
    const registrarMarca = (origem) => {
      const marcaId = Number(origem?.marca_id);
      if (!Number.isFinite(marcaId) || marcaId <= 0) {
        return;
      }

      const nomeMarca = String(
        origem?.marca_nome
          || origem?.marca?.nome
          || origem?.marca
          || ''
      ).trim();

      if (!nomeMarca) {
        return;
      }

      if (!mapa.has(marcaId)) {
        mapa.set(marcaId, { id: marcaId, nome: nomeMarca });
      }
    };

    produtos.forEach(registrarMarca);
    sugestoes.forEach(registrarMarca);

    return Array.from(mapa.values()).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [produtos, sugestoes]);

  const selecionadosComQuantidade = useMemo(
    () => sugestoes
      .filter((s) => produtosSelecionados.includes(s.produto_id))
      .filter((s) => obterQuantidadeInteira(s) > 0),
    [sugestoes, produtosSelecionados, quantidadesEditadas],
  );

  const resumoMarcasSelecionadas = useMemo(() => {
    if (marcasSelecionadas.length === 0 || marcasSelecionadas.length === marcasFornecedor.length) {
      return 'Todas';
    }

    if (marcasSelecionadas.length === 1) {
      return marcasFornecedor.find((marca) => marca.id === marcasSelecionadas[0])?.nome || '1 marca';
    }

    return `${marcasSelecionadas.length} marcas`;
  }, [marcasFornecedor, marcasSelecionadas]);

  const fecharModalSugestao = () => {
    setMostrarSugestao(false);
    setProdutosSelecionados([]);
    setQuantidadesEditadas({});
    setFiltroSugestao('');
    setMostrarSoPreenchidos(false);
    setMarcasSelecionadas([]);
    setMostrarFiltroMarcas(false);
    setProdutoEditandoQuantidade(null);
    setModoAplicacaoSugestao('merge');
  };

  // Fechar modal com ESC
  useEffect(() => {
    if (!mostrarSugestao) return;
    const handleKeyDown = (e) => {
      if (e.key !== 'Escape') return;

      if (mostrarFiltroMarcas) {
        setMostrarFiltroMarcas(false);
        return;
      }

      fecharModalSugestao();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mostrarSugestao, mostrarFiltroMarcas]);

  useEffect(() => {
    if (!mostrarSugestao || !mostrarFiltroMarcas) {
      return undefined;
    }

    const handleClickFora = (event) => {
      if (!filtroMarcasRef.current?.contains(event.target)) {
        setMostrarFiltroMarcas(false);
      }
    };

    window.addEventListener('mousedown', handleClickFora);
    return () => window.removeEventListener('mousedown', handleClickFora);
  }, [mostrarSugestao, mostrarFiltroMarcas]);

  useEffect(() => {
    if (!mostrarSugestao) {
      return undefined;
    }

    const cabecalho = cabecalhoTabelaSugestaoRef.current;
    const corpo = corpoTabelaSugestaoRef.current;
    if (!cabecalho || !corpo) {
      return undefined;
    }

    const sincronizarScrollHorizontal = () => {
      if (cabecalho.scrollLeft !== corpo.scrollLeft) {
        cabecalho.scrollLeft = corpo.scrollLeft;
      }
    };

    sincronizarScrollHorizontal();
    corpo.addEventListener('scroll', sincronizarScrollHorizontal, { passive: true });
    window.addEventListener('resize', sincronizarScrollHorizontal);

    return () => {
      corpo.removeEventListener('scroll', sincronizarScrollHorizontal);
      window.removeEventListener('resize', sincronizarScrollHorizontal);
    };
  }, [mostrarSugestao, sugestoesFiltradas.length]);

  const selecionarTodosCriticos = () => {
    const criticos = sugestoes
      .filter(s => s.prioridade === 'CRÍTICO' && obterQuantidadeInteira(s) > 0)
      .map(s => s.produto_id);
    setProdutosSelecionados(criticos);
  };

  const selecionarPreenchidosVisiveis = () => {
    const preenchidos = sugestoesFiltradas
      .filter((s) => obterQuantidadeInteira(s) > 0)
      .map((s) => s.produto_id);
    setProdutosSelecionados(preenchidos);
  };

  const desmarcarVisiveis = () => {
    const idsVisiveis = new Set(sugestoesFiltradas.map((s) => s.produto_id));
    setProdutosSelecionados((prev) => prev.filter((id) => !idsVisiveis.has(id)));
  };

  const alternarMarcaSelecionada = (marcaId) => {
    setMarcasSelecionadas((marcasAtuais) => {
      if (marcasAtuais.length === 0) {
        return [marcaId];
      }

      const jaSelecionada = marcasAtuais.includes(marcaId);
      const proximasMarcas = jaSelecionada
        ? marcasAtuais.filter((id) => id !== marcaId)
        : [...marcasAtuais, marcaId].sort((a, b) => a - b);

      if (
        proximasMarcas.length === 0
        || proximasMarcas.length === marcasFornecedor.length
      ) {
        return [];
      }

      return proximasMarcas;
    });
  };

  const classeCabecalhoTabelaSugestao = 'border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.04em] text-slate-600 whitespace-nowrap shadow-[inset_0_-1px_0_rgba(203,213,225,0.9)]';
  const classeTabelaSugestao = 'w-full min-w-[1180px] table-fixed border-separate border-spacing-0';
  const renderColGroupSugestao = () => (
    <colgroup>
      <col style={{ width: '3%' }} />
      <col style={{ width: '8%' }} />
      <col style={{ width: '34%' }} />
      <col style={{ width: '7%' }} />
      <col style={{ width: '8%' }} />
      <col style={{ width: '8%' }} />
      <col style={{ width: '9%' }} />
      <col style={{ width: '8%' }} />
      <col style={{ width: '8%' }} />
      <col style={{ width: '7%' }} />
    </colgroup>
  );

  const adicionarSugestoesAoPedido = () => {
    if (produtosSelecionados.length === 0) {
      toast.error('Selecione pelo menos um produto');
      return;
    }

    const produtosParaAdicionar = sugestoes
      .filter((s) => produtosSelecionados.includes(s.produto_id))
      .map((sugestao) => ({
        sugestao,
        quantidade: obterQuantidadeInteira(sugestao),
      }))
      .filter((item) => item.quantidade > 0);

    if (produtosParaAdicionar.length === 0) {
      toast.error('Os produtos selecionados estão com quantidade 0. Preencha pelo menos 1 unidade.');
      return;
    }

    const novosItens = produtosParaAdicionar.map(({ sugestao, quantidade }) => {
      return {
        produto_id: sugestao.produto_id,
        produto_nome: sugestao.produto_nome,
        produto_codigo: sugestao.produto_sku || '',
        quantidade_pedida: quantidade,
        preco_unitario: sugestao.preco_unitario,
        desconto_item: 0,
        total: quantidade * sugestao.preco_unitario
      };
    });

    const itensAtualizados = modoAplicacaoSugestao === 'replace'
      ? clonarItensPedido(novosItens)
      : consolidarItensPedido(formData.itens, novosItens, estrategiaMesclaItens);

    setFormData({
      ...formData,
      itens: itensAtualizados
    });

    toast.success(
      modoAplicacaoSugestao === 'replace'
        ? `${novosItens.length} produtos aplicados substituindo o rascunho atual`
        : `${novosItens.length} produtos consolidados no pedido`
    );
    fecharModalSugestao();
  };


  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.itens.length === 0) {
      toast.error('Adicione pelo menos 1 item ao pedido');
      return;
    }

    setLoading(true);
    try {
      const dadosEnvio = {
        ...formData,
        fornecedor_id: parseInt(formData.fornecedor_id),
        valor_frete: parseFloat(formData.valor_frete),
        valor_desconto: parseFloat(formData.valor_desconto),
        data_prevista_entrega: formData.data_prevista_entrega ? `${formData.data_prevista_entrega}T12:00:00` : null,
        itens: formData.itens.map((item) => ({
          produto_id: item.produto_id,
          quantidade_pedida: parseFloat(item.quantidade_pedida),
          preco_unitario: parseFloat(item.preco_unitario),
          desconto_item: parseFloat(item.desconto_item || 0)
        }))
      };
      await api.post('/pedidos-compra/', dadosEnvio);

      toast.success('✅ Pedido criado com sucesso!');
      fecharFormularioPedido();
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao criar pedido');
    } finally {
      setLoading(false);
    }
  };

  const enviarPedido = async (pedido) => {
    const fornecedor = obterFornecedorPorId(pedido.fornecedor_id);
    const emailFornecedor = extrairEmailFornecedor(fornecedor);

    // Abrir modal de envio ao invés de enviar direto
    setPedidoParaEnviar(pedido.id);
    setDadosEnvio({
      email: emailFornecedor,
      whatsapp: '',
      formatos: {
        pdf: true,
        excel: false
      }
    });
    setMostrarModalEnvio(true);
  };

  const atualizarColunasDocumento = (colunas) => {
    setColunasDocumentoPedido(normalizarColunasDocumentoPedido(colunas));
  };

  const abrirModalExportacao = (pedido, formato) => {
    setPedidoParaExportar({
      id: pedido.id,
      numero_pedido: pedido.numero_pedido,
      formato,
    });
    setMostrarModalExportacao(true);
  };

  const fecharModalExportacao = () => {
    if (exportandoArquivo) {
      return;
    }
    setMostrarModalExportacao(false);
    setPedidoParaExportar(null);
  };
  
  const confirmarEnvioPedido = async () => {
    if (!dadosEnvio.email && !dadosEnvio.whatsapp) {
      toast.error('Informe um e-mail ou WhatsApp');
      return;
    }

    if (!emailEnvioDisponivel) {
      toast.error('O servidor ainda não está configurado para enviar e-mails');
      return;
    }
    
    if (!dadosEnvio.formatos.pdf && !dadosEnvio.formatos.excel) {
      toast.error('Selecione pelo menos um formato (PDF ou Excel)');
      return;
    }

    if (normalizarColunasDocumentoPedido(colunasDocumentoPedido).length === 0) {
      toast.error('Selecione pelo menos uma coluna para o documento');
      return;
    }

    try {
            // Aqui você pode implementar o envio real por e-mail/WhatsApp no futuro
      // Por enquanto, apenas marca como enviado
      const response = await api.post(`/pedidos-compra/${pedidoParaEnviar}/enviar`, {
        email: dadosEnvio.email,
        whatsapp: dadosEnvio.whatsapp,
        formatos: dadosEnvio.formatos,
        colunas_exportacao: normalizarColunasDocumentoPedido(colunasDocumentoPedido)
      });

      const tipoEnvio = response?.data?.tipo_envio;
      if (tipoEnvio === 'email') {
        toast.success('Pedido enviado por e-mail com sucesso');
      } else if (tipoEnvio === 'manual') {
        toast.success('Pedido marcado como enviado manualmente');
      } else {
        toast.success(response?.data?.message || 'Pedido processado com sucesso');
      }

      setMostrarModalEnvio(false);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao enviar pedido');
    }
  };
  
  const marcarComoEnviadoManualmente = async () => {
    try {
      const response = await api.post(`/pedidos-compra/${pedidoParaEnviar}/enviar`, {
        envio_manual: true
      });
      
      toast.success('✅ Pedido marcado como enviado manualmente!');
      setMostrarModalEnvio(false);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao marcar pedido');
    }
  };

  const confirmarPedido = async (id) => {
    try {
      await api.post(`/pedidos-compra/${id}/confirmar`, {});
      toast.success('✅ Pedido confirmado!');
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao confirmar pedido');
    }
  };

  const exportarPDF = async (id) => {
    const pedido = pedidos.find((item) => Number(item.id) === Number(id));
    if (!pedido) {
      toast.error('Pedido nao encontrado para exportacao');
      return;
    }
    abrirModalExportacao(pedido, 'pdf');
  };

  const exportarExcel = async (id) => {
    const pedido = pedidos.find((item) => Number(item.id) === Number(id));
    if (!pedido) {
      toast.error('Pedido nao encontrado para exportacao');
      return;
    }
    abrirModalExportacao(pedido, 'excel');
  };

  const confirmarExportacaoPedido = async () => {
    if (!pedidoParaExportar) {
      return;
    }

    const colunasNormalizadas = normalizarColunasDocumentoPedido(colunasDocumentoPedido);
    if (colunasNormalizadas.length === 0) {
      toast.error('Selecione pelo menos uma coluna para o documento');
      return;
    }

    const { id, formato } = pedidoParaExportar;
    const rota = formato === 'pdf'
      ? `/pedidos-compra/${id}/export/pdf`
      : `/pedidos-compra/${id}/export/excel`;
    const fallback = formato === 'pdf'
      ? `pedido_${id}.pdf`
      : `pedido_${id}.xlsx`;

    setExportandoArquivo(true);
    try {
      const response = await api.get(
        rota,
        {
          params: {
            colunas: colunasNormalizadas.join(','),
          },
          responseType: 'blob'
        }
      );
      baixarArquivoResposta(response, fallback);
      toast.success(`${formato.toUpperCase()} exportado com sucesso!`);
      fecharModalExportacao();
    } catch (error) {
      toast.error(`Erro ao exportar ${formato.toUpperCase()}`);
    } finally {
      setExportandoArquivo(false);
    }
  };

  const verDetalhes = async (pedido) => {
    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      setPedidoSelecionado(response.data);
      setMostrarRecebimento(true);
    } catch (error) {
      toast.error('Erro ao carregar detalhes do pedido');
    }
  };

  const reverterStatus = async (id) => {
    if (!confirm('⚠️ Deseja reverter o status deste pedido para a etapa anterior?')) {
      return;
    }
    try {
      const response = await api.post(
        `/pedidos-compra/${id}/reverter`,
        {}
      );
      toast.success(`⏪ Status revertido: ${response.data.status_anterior} → ${response.data.status_atual}`);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao reverter status');
    }
  };

  const cancelarPedido = async (pedido) => {
    const acao = pedido.status === 'rascunho' ? 'cancelar/excluir' : 'cancelar';
    const motivo = window.prompt(
      `Informe o motivo para ${acao} o pedido ${pedido.numero_pedido}:`,
      'Cancelado pelo usuário',
    );

    if (!motivo) return;

    const motivoLimpo = motivo.trim();
    if (motivoLimpo.length < 10) {
      toast.error('Informe um motivo com pelo menos 10 caracteres');
      return;
    }

    try {
      await api.post(`/pedidos-compra/${pedido.id}/cancelar`, null, {
        params: { motivo: motivoLimpo },
      });
      toast.success('✅ Pedido cancelado com sucesso');
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao cancelar pedido');
    }
  };

  const abrirEdicao = async (pedido) => {
    if (pedido.status !== 'rascunho') {
      toast.error('⚠️ Apenas pedidos em rascunho podem ser editados');
      return;
    }

    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      
      const pedidoCompleto = response.data;
      await aplicarPedidoNoFormulario(pedidoCompleto, null, {
        mostrarToast: true,
        mensagemSucesso: 'Modo de edição ativado',
      });
      return;
      
      setModoEdicao(true);
      setPedidoEditando(pedidoCompleto);
      setFormData({
        fornecedor_id: pedidoCompleto.fornecedor_id?.toString() || '',
        data_prevista_entrega: pedidoCompleto.data_prevista_entrega 
          ? new Date(pedidoCompleto.data_prevista_entrega).toISOString().split('T')[0] 
          : '',
        valor_frete: pedidoCompleto.valor_frete?.toString() || '0',
        valor_desconto: pedidoCompleto.valor_desconto?.toString() || '0',
        observacoes: pedidoCompleto.observacoes || '',
        itens: pedidoCompleto.itens.map(item => ({
          produto_id: item.produto_id,
          produto_nome: item.produto_nome || `Produto ${item.produto_id}`,
          quantidade_pedida: item.quantidade_pedida,
          preco_unitario: item.preco_unitario,
          desconto_item: item.desconto_item || 0,
          total: (item.quantidade_pedida * item.preco_unitario) - (item.desconto_item || 0)
        }))
      });
      
      // Carregar produtos do fornecedor
      if (pedidoCompleto.fornecedor_id) {
        const fornecedorSelecionado = fornecedores.find(
          (f) => f.id === pedidoCompleto.fornecedor_id,
        );
        setFornecedorTexto(fornecedorSelecionado?.nome || '');
        carregarProdutosFornecedor(pedidoCompleto.fornecedor_id);
      }
      
      setMostrarForm(true);
      toast.success('📝 Modo de edição ativado');
    } catch (error) {
      toast.error('Erro ao carregar pedido para edição');
    }
  };

  const editarPedido = async (e) => {
    e.preventDefault();
    
    if (formData.itens.length === 0) {
      toast.error('⚠️ Adicione pelo menos um item ao pedido');
      return;
    }

    try {
      setLoading(true);
      
      const dadosEnvio = {
        ...formData,
        fornecedor_id: parseInt(formData.fornecedor_id),
        valor_frete: parseFloat(formData.valor_frete),
        valor_desconto: parseFloat(formData.valor_desconto),
        data_prevista_entrega: formData.data_prevista_entrega 
          ? `${formData.data_prevista_entrega}T12:00:00` 
          : null,
        itens: formData.itens.map(item => ({
          produto_id: item.produto_id,
          quantidade_pedida: parseFloat(item.quantidade_pedida),
          preco_unitario: parseFloat(item.preco_unitario),
          desconto_item: parseFloat(item.desconto_item || 0)
        }))
      };

      await api.put(
        `/pedidos-compra/${pedidoEditando.id}`, 
        dadosEnvio
      );

      toast.success('✏️ Pedido atualizado com sucesso!');
      fecharFormularioPedido();
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar pedido');
    } finally {
      setLoading(false);
    }
  };

  const abrirRecebimento = async (pedido) => {
    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      setPedidoSelecionado(response.data);
      setMostrarRecebimento(true);
    } catch (error) {
      toast.error('Erro ao carregar detalhes do pedido');
    }
  };

  const abrirConfronto = async (pedido) => {
    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      setPedidoConfronto(response.data);
      setMostrarConfronto(true);
    } catch (error) {
      toast.error('Erro ao carregar detalhes do pedido');
    }
  };

  const receberPedido = async (itensRecebimento) => {
    try {
      await api.post(
        `/pedidos-compra/${pedidoSelecionado.id}/receber`,
        { itens: itensRecebimento }
      );
      toast.success('✅ Recebimento processado com sucesso!');
      setMostrarRecebimento(false);
      setPedidoSelecionado(null);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao processar recebimento');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      rascunho: 'bg-gray-200 text-gray-800',
      enviado: 'bg-blue-200 text-blue-800',
      confirmado: 'bg-green-200 text-green-800',
      recebido_parcial: 'bg-yellow-200 text-yellow-800',
      recebido_total: 'bg-green-500 text-white',
      cancelado: 'bg-red-200 text-red-800'
    };
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${styles[status] || 'bg-gray-200'}`}>
        {status.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">🛒 Pedidos de Compra</h1>
          <p className="text-gray-600">Gerencie seus pedidos aos fornecedores</p>
        </div>
        <button
          onClick={() => {
            if (mostrarForm) {
              fecharFormularioPedido();
              return;
            }

            abrirNovoFormulario();
          }}
          className="inline-flex items-center gap-2 border border-blue-200 bg-blue-50 text-blue-700 px-5 py-2.5 rounded-lg font-semibold hover:bg-blue-100 transition-colors"
        >
          {mostrarForm ? '❌ Cancelar' : '➕ Novo Pedido'}
        </button>
      </div>

      {/* Formulário de Novo/Editar Pedido */}
      {mostrarForm && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">
              {modoEdicao ? '✏️ Editar Pedido' : 'Novo Pedido de Compra'}
            </h2>
            <button
              type="button"
              onClick={fecharFormularioPedido}
              className="text-gray-500 hover:text-gray-700"
            >
              ✖️
            </button>
          </div>
          <form onSubmit={modoEdicao ? editarPedido : handleSubmit} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Fornecedor *
                </label>
                <div className="relative">
                <input
                  value={fornecedorTexto}
                  onChange={(e) => {
                    const valor = e.target.value;
                    setFornecedorTexto(valor);
                    setMostrarSugestoesFornecedor(true);

                    // Mantém selecionado só quando casar exatamente (digitado/manual)
                    const fornecedorExato = fornecedores.find(
                      (f) => (f.nome || '').toLowerCase() === valor.toLowerCase(),
                    );
                    if (fornecedorExato) {
                      selecionarFornecedor(fornecedorExato);
                    } else {
                      setFormData((prev) => ({ ...prev, fornecedor_id: '', itens: [] }));
                      setProdutos([]);
                      setIncluirGrupoFornecedor(false);
                      setProdutoTexto('');
                      setMostrarSugestoesProduto(false);
                      setItemForm(ITEM_FORM_INICIAL);
                      limparEstadosSugestao();
                    }
                  }}
                  onFocus={() => setMostrarSugestoesFornecedor(true)}
                  onBlur={() => {
                    // Pequeno delay para permitir clique na sugestão
                    setTimeout(() => setMostrarSugestoesFornecedor(false), 120);
                  }}
                  placeholder="Digite ou selecione o fornecedor"
                  required={!!formData.fornecedor_id}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                {mostrarSugestoesFornecedor && fornecedoresFiltrados.length > 0 && (
                  <div className="absolute z-20 mt-1 w-full max-h-60 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg">
                    {fornecedoresFiltrados.map((f) => (
                      <button
                        type="button"
                        key={f.id}
                        onMouseDown={(ev) => ev.preventDefault()}
                        onClick={() => selecionarFornecedor(f)}
                        className="w-full px-4 py-2 text-left hover:bg-blue-50 border-b border-gray-100 last:border-b-0"
                      >
                        <div className="font-medium text-gray-800">{f.nome}</div>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                          {(f.cpf_cnpj || f.cnpj || f.cpf) && (
                            <span>{f.cpf_cnpj || f.cnpj || f.cpf}</span>
                          )}
                          {obterGrupoDoFornecedor(f.id) && (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-700">
                              Grupo: {obterGrupoDoFornecedor(f.id).nome}
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <p className="text-xs text-gray-500">Digite ou selecione um fornecedor para carregar seus produtos</p>
                  <button
                    type="button"
                    onClick={abrirNovoGrupoFornecedor}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    Grupos de fornecedor
                  </button>
                </div>
                {formData.fornecedor_id && grupoFornecedorAtual && (
                  <label className="mt-2 flex cursor-pointer items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
                    <input
                      type="checkbox"
                      checked={incluirGrupoFornecedor}
                      onChange={(e) => {
                        setIncluirGrupoFornecedor(e.target.checked);
                        limparEstadosSugestao();
                      }}
                      className="mt-0.5 h-4 w-4 rounded"
                    />
                    <span>
                      <strong>Unificar CNPJs do grupo {grupoFornecedorAtual.nome}</strong>
                      <span className="block text-emerald-700">
                        A sugestao inteligente considera todos os fornecedores vinculados ao grupo.
                      </span>
                    </span>
                  </label>
                )}
                {formData.fornecedor_id && !grupoFornecedorAtual && (
                  <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    Este fornecedor ainda nao esta em um grupo. Use "Grupos de fornecedor" para unificar CNPJs.
                  </div>
                )}
                {formData.fornecedor_id && (
                  <button
                    type="button"
                    onClick={abrirFluxoSugestaoInteligente}
                    disabled={loadingPrepararSugestao}
                    className="mt-2 w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2"
                  >
                    {loadingPrepararSugestao ? 'Verificando rascunho...' : '💡 Sugestão Inteligente de Pedido'}
                  </button>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Data Prevista Entrega
                </label>
                <input
                  type="date"
                  value={formData.data_prevista_entrega}
                  onChange={(e) => setFormData({ ...formData, data_prevista_entrega: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Adicionar Itens */}
            <div className="border-t pt-4">
              <h3 className="font-semibold mb-4">Itens do Pedido</h3>
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div className="col-span-2 relative">
                  <input
                    value={produtoTexto}
                    onChange={(e) => {
                      const valor = e.target.value;
                      setProdutoTexto(valor);
                      setMostrarSugestoesProduto(true);

                      const produtoExato = produtos.find(
                        (p) => (p.nome || '').toLowerCase() === valor.toLowerCase(),
                      );

                      if (produtoExato) {
                        selecionarProduto(produtoExato);
                      } else {
                        setItemForm((prev) => ({ ...prev, produto_id: '' }));
                      }
                    }}
                    onFocus={() => {
                      if (formData.fornecedor_id) {
                        setMostrarSugestoesProduto(true);
                      }
                    }}
                    onBlur={() => {
                      setTimeout(() => setMostrarSugestoesProduto(false), 120);
                    }}
                    placeholder={!formData.fornecedor_id ? 'Selecione um fornecedor primeiro' : 'Digite ou selecione o produto'}
                    disabled={!formData.fornecedor_id}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100 focus:ring-2 focus:ring-blue-500"
                  />
                  {mostrarSugestoesProduto && produtosFiltrados.length > 0 && formData.fornecedor_id && (
                    <div className="absolute z-20 mt-1 w-full max-h-60 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg">
                      {produtosFiltrados.map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          onMouseDown={(ev) => ev.preventDefault()}
                          onClick={() => selecionarProduto(p)}
                          className="w-full px-4 py-2 text-left hover:bg-blue-50 border-b border-gray-100 last:border-b-0"
                        >
                          <div className="font-medium text-gray-800">{p.nome}</div>
                          <div className="text-xs text-gray-500">
                            SKU: {p.sku || p.codigo || 'N/A'} | Barras: {p.codigo_barras || 'N/A'} | Estoque: {p.estoque_atual || 0}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <input
                  type="number"
                  step="0.01"
                  placeholder="Quantidade"
                  value={itemForm.quantidade_pedida}
                  onChange={(e) => setItemForm({ ...itemForm, quantidade_pedida: e.target.value })}
                  className="px-4 py-2 border border-gray-300 rounded-lg"
                />
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Preço"
                    value={itemForm.preco_unitario}
                    onChange={(e) => setItemForm({ ...itemForm, preco_unitario: e.target.value })}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
                  />
                  <button
                    type="button"
                    onClick={adicionarItem}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                  >
                    ➕
                  </button>
                </div>
              </div>

              {/* Lista de Itens */}
              {formData.itens.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Produto</th>
                        <th className="px-4 py-2 text-right text-sm font-semibold">Qtd</th>
                        <th className="px-4 py-2 text-right text-sm font-semibold">Preço</th>
                        <th className="px-4 py-2 text-right text-sm font-semibold">Total</th>
                        <th className="px-4 py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {formData.itens.map((item, index) => (
                        <tr key={index} className="border-t">
                          <td className="px-4 py-2">
                            <div className="font-medium text-gray-900">{item.produto_nome}</div>
                            <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                              <span>SKU: {obterSkuItemPedido(item) || 'N/A'}</span>
                              <button
                                type="button"
                                onClick={() => copiarSkuItemPedido(item)}
                                className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 text-slate-500 transition hover:border-blue-300 hover:text-blue-600"
                                title="Copiar SKU"
                                aria-label={`Copiar SKU de ${item.produto_nome}`}
                              >
                                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
                                  <rect x="9" y="9" width="11" height="11" rx="2" />
                                  <path d="M6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1" />
                                </svg>
                              </button>
                            </div>
                          </td>
                          <td className="px-4 py-2 text-right">
                            <input
                              type="number"
                              min="0.01"
                              step="0.01"
                              value={item.quantidade_pedida}
                              onChange={(e) => atualizarItemPedido(index, 'quantidade_pedida', e.target.value)}
                              className="w-24 rounded-lg border border-gray-300 px-3 py-2 text-right focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                            />
                          </td>
                          <td className="px-4 py-2 text-right">R$ {numeroSeguro(item.preco_unitario).toFixed(2)}</td>
                          <td className="px-4 py-2 text-right font-semibold">R$ {numeroSeguro(item.total).toFixed(2)}</td>
                          <td className="px-4 py-2 text-right">
                            <button
                              type="button"
                              onClick={() => removerItem(index)}
                              className="text-red-600 hover:text-red-800"
                            >
                              🗑️
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Totais */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Frete (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.valor_frete}
                  onChange={(e) => setFormData({ ...formData, valor_frete: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Desconto (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.valor_desconto}
                  onChange={(e) => setFormData({ ...formData, valor_desconto: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Total</label>
                <div className="text-2xl font-bold text-green-600">
                  R$ {calcularTotal().toFixed(2)}
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading 
                ? '⏳ Processando...' 
                : modoEdicao 
                  ? '✏️ Salvar Alterações' 
                  : '✅ Criar Pedido'
              }
            </button>
          </form>
        </div>
      )}

      {/* Lista de Pedidos */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold">Número</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Fornecedor</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Data</th>
              <th className="px-4 py-3 text-right text-sm font-semibold">Valor</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Status</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody>
            {pedidos.map(pedido => (
              <tr 
                key={pedido.id} 
                className={`border-t hover:bg-gray-50 ${
                  pedido.status === 'rascunho' ? 'cursor-pointer' : ''
                }`}
                onClick={() => pedido.status === 'rascunho' && abrirEdicao(pedido)}
                title={pedido.status === 'rascunho' ? 'Clique para editar' : ''}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {pedido.numero_pedido}
                    {pedido.foi_alterado_apos_envio && (
                      <span className="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded font-semibold" title="Este pedido foi alterado após o envio">
                        ⚠️ Alterado
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">{obterFornecedorPorId(pedido.fornecedor_id)?.nome || pedido.fornecedor_id}</td>
                <td className="px-4 py-3">{new Date(pedido.data_pedido).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-right font-semibold">R$ {pedido.valor_final.toFixed(2)}</td>
                <td className="px-4 py-3 text-center">{getStatusBadge(pedido.status)}</td>
                <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                  <div className="flex justify-center gap-2">
                    {/* Botão Ver Detalhes */}
                    <button
                      onClick={() => verDetalhes(pedido)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 border border-gray-200 bg-white text-gray-700 rounded-md hover:bg-gray-50 text-xs font-semibold"
                      title="Ver detalhes completos do pedido"
                    >
                      🔍 Ver
                    </button>

                    {/* Botões de exportação - sempre disponíveis */}
                    <button
                      onClick={() => exportarPDF(pedido.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 border border-red-200 bg-white text-red-700 rounded-md hover:bg-red-50 text-xs font-semibold"
                      title="Exportar PDF"
                    >
                      📄 PDF
                    </button>
                    <button
                      onClick={() => exportarExcel(pedido.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 border border-emerald-200 bg-white text-emerald-700 rounded-md hover:bg-emerald-50 text-xs font-semibold"
                      title="Exportar Excel"
                    >
                      📊 Excel
                    </button>
                    
                    {/* Ações por status */}
                    {pedido.status === 'rascunho' && (
                      <button
                        onClick={() => enviarPedido(pedido)}
                        className="inline-flex items-center gap-1 px-3 py-1 border border-blue-200 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 text-xs font-semibold"
                        title="Enviar pedido ao fornecedor"
                      >
                        📤 Enviar
                      </button>
                    )}
                    {pedido.status === 'enviado' && (
                      <button
                        onClick={() => confirmarPedido(pedido.id)}
                        className="inline-flex items-center gap-1 px-3 py-1 border border-emerald-200 bg-emerald-50 text-emerald-700 rounded-md hover:bg-emerald-100 text-xs font-semibold"
                        title="Confirmar recebimento do pedido pelo fornecedor"
                      >
                        ✅ Confirmar
                      </button>
                    )}
                    {(pedido.status === 'confirmado' || pedido.status === 'recebido_parcial') && (
                      <button
                        onClick={() => abrirConfronto(pedido)}
                        className="inline-flex items-center gap-1 px-3 py-1 border border-violet-200 bg-violet-50 text-violet-700 rounded-md hover:bg-violet-100 text-xs font-semibold"
                        title="Confrontar pedido com NF fiscal"
                      >
                        🔍 Conferir NF
                      </button>
                    )}
                    {(pedido.status === 'confirmado' || pedido.status === 'recebido_parcial') && (
                      <button
                        onClick={() => abrirRecebimento(pedido)}
                        className="inline-flex items-center gap-1 px-3 py-1 border border-gray-200 bg-gray-50 text-gray-600 rounded-md hover:bg-gray-100 text-xs font-semibold"
                        title="Registrar entrada de produtos no estoque (legado)"
                      >
                        📦 Receber
                      </button>
                    )}

                    {/* Botão Reverter - exceto para rascunho */}
                    {pedido.status !== 'rascunho' && pedido.status !== 'recebido_total' && (
                      <button
                        onClick={() => reverterStatus(pedido.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 border border-amber-200 bg-amber-50 text-amber-700 rounded-md hover:bg-amber-100 text-xs font-semibold"
                        title="Reverter para status anterior"
                      >
                        ⏪ Reverter
                      </button>
                    )}

                    {pedido.status !== 'recebido_total' && pedido.status !== 'cancelado' && (
                      <button
                        onClick={() => cancelarPedido(pedido)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 border border-rose-200 bg-rose-50 text-rose-700 rounded-md hover:bg-rose-100 text-xs font-semibold"
                        title={pedido.status === 'rascunho' ? 'Cancelar/Excluir pedido em rascunho' : 'Cancelar pedido'}
                      >
                        🗑️ {pedido.status === 'rascunho' ? 'Excluir' : 'Cancelar'}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal de Recebimento */}
      {mostrarRecebimento && pedidoSelecionado && (
        <ModalRecebimento
          pedido={pedidoSelecionado}
          onClose={() => {
            setMostrarRecebimento(false);
            setPedidoSelecionado(null);
          }}
          onReceber={receberPedido}
        />
      )}

      {/* Modal de Confronto Pedido x NF */}
      {mostrarConfronto && pedidoConfronto && (
        <ModalConfronto
          pedido={pedidoConfronto}
          onClose={() => { setMostrarConfronto(false); setPedidoConfronto(null); }}
          onPedidoComplementarCriado={() => { carregarDados(); }}
        />
      )}
      
      {/* Modal de Envio */}
      {mostrarModalEnvio && (
        <ModalEnvioPedido
          pedidoId={pedidoParaEnviar}
          onClose={() => setMostrarModalEnvio(false)}
          onEnviar={confirmarEnvioPedido}
          onEnvioManual={marcarComoEnviadoManualmente}
          emailEnvioDisponivel={emailEnvioDisponivel}
          dadosEnvio={dadosEnvio}
          setDadosEnvio={setDadosEnvio}
          colunasSelecionadas={colunasDocumentoPedido}
          onChangeColunas={atualizarColunasDocumento}
        />
      )}

      {mostrarModalExportacao && pedidoParaExportar && (
        <ModalExportacaoPedido
          pedido={pedidoParaExportar}
          onClose={fecharModalExportacao}
          onConfirmar={confirmarExportacaoPedido}
          loading={exportandoArquivo}
          colunasSelecionadas={colunasDocumentoPedido}
          onChangeColunas={atualizarColunasDocumento}
        />
      )}

      {mostrarModalRascunhoSugestao && contextoRascunhoSugestao && (
        <ModalDecisaoRascunho
          contexto={contextoRascunhoSugestao}
          estrategiaMesclaItens={estrategiaMesclaItens}
          setEstrategiaMesclaItens={setEstrategiaMesclaItens}
          onClose={fecharModalRascunho}
          onSelecionar={decidirAcaoRascunhoSugestao}
        />
      )}

      {/* 💡 MODAL DE SUGESTÃO INTELIGENTE */}
      {mostrarModalGruposFornecedores && (
        <ModalGruposFornecedores
          grupos={gruposFornecedores}
          fornecedores={fornecedores}
          form={grupoFornecedorForm}
          setForm={setGrupoFornecedorForm}
          salvando={salvandoGrupoFornecedor}
          onClose={() => {
            setMostrarModalGruposFornecedores(false);
            setGrupoFornecedorForm(GRUPO_FORNECEDOR_FORM_INICIAL);
          }}
          onSubmit={salvarGrupoFornecedor}
          onNovo={() => setGrupoFornecedorForm(GRUPO_FORNECEDOR_FORM_INICIAL)}
          onEditar={editarGrupoFornecedor}
          onExcluir={excluirGrupoFornecedor}
          onToggleFornecedor={alternarFornecedorNoGrupoForm}
        />
      )}

      {mostrarSugestao && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white w-full h-full flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 via-violet-600 to-indigo-600 px-4 py-3 text-white shadow-sm">
              <div className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-purple-100/90">
                      Sugestão Inteligente
                    </div>
                    <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <h2 className="text-lg font-bold leading-tight">Pedido guiado por vendas e estoque</h2>
                      <p className="text-xs text-purple-100/85">
                        Ajuste rápido dos filtros sem perder área útil.
                      </p>
                      </div>
                    </div>
                  <button
                    onClick={fecharModalSugestao}
                    className="shrink-0 rounded-lg p-2 text-white transition hover:bg-white/15"
                  >
                    ✕
                  </button>
                </div>

                {/* Filtros */}
                <div className="grid gap-2 xl:grid-cols-12">
                  <div className="xl:col-span-4">
                    <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-purple-100">Buscar por nome ou SKU</label>
                    <input
                      type="text"
                      placeholder="Ex: Special Dog, SKU 211..."
                      value={filtroSugestao}
                      onChange={(e) => setFiltroSugestao(e.target.value)}
                      className="h-11 w-full rounded-lg border border-white/20 bg-white px-3 text-gray-800 shadow-sm focus:ring-2 focus:ring-purple-300"
                    />
                  </div>
                  <div ref={filtroMarcasRef} className="relative sm:col-span-2 xl:col-span-3">
                    <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-purple-100">Marcas</label>
                    <button
                      type="button"
                      onClick={() => setMostrarFiltroMarcas((aberto) => !aberto)}
                      className="flex h-11 w-full items-center justify-between rounded-lg border border-white/20 bg-white px-3 text-left text-gray-800 shadow-sm transition hover:bg-purple-50"
                    >
                      <span className="truncate">
                        {resumoMarcasSelecionadas}
                      </span>
                      <span className={`ml-3 text-sm transition-transform ${mostrarFiltroMarcas ? 'rotate-180' : ''}`}>
                        ▾
                      </span>
                    </button>

                    {mostrarFiltroMarcas && (
                      <div className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-purple-200 bg-white text-gray-800 shadow-2xl">
                        <button
                          type="button"
                          onClick={() => setMarcasSelecionadas([])}
                          className="flex w-full items-center justify-between border-b border-gray-100 px-3 py-2 text-sm font-medium transition hover:bg-purple-50"
                        >
                          <span className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={marcasSelecionadas.length === 0}
                              readOnly
                              className="h-4 w-4 rounded"
                            />
                            Todas
                          </span>
                          <span className="text-xs text-gray-500">
                            {marcasSelecionadas.length === 0 ? 'sem filtro' : 'limpar'}
                          </span>
                        </button>

                        <div className="max-h-56 overflow-y-auto py-1">
                          {marcasFornecedor.map((marca) => (
                            <label
                              key={marca.id}
                              className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm transition hover:bg-purple-50"
                            >
                              <input
                                type="checkbox"
                                checked={marcasSelecionadas.includes(marca.id)}
                                onChange={() => alternarMarcaSelecionada(marca.id)}
                                className="h-4 w-4 rounded"
                              />
                              <span className="truncate">{marca.nome}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="sm:col-span-1 xl:col-span-2">
                    <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-purple-100">Período</label>
                    <select
                      value={periodoSugestao}
                      onChange={(e) => setPeriodoSugestao(parseInt(e.target.value))}
                      className="h-11 w-full rounded-lg border border-white/20 bg-white px-3 text-gray-800 shadow-sm focus:ring-2 focus:ring-purple-300"
                    >
                      <option value={30}>Últimos 30 dias</option>
                      <option value={60}>Últimos 60 dias</option>
                      <option value={90}>Últimos 90 dias</option>
                      <option value={180}>Últimos 180 dias</option>
                    </select>
                  </div>
                  <div className="sm:col-span-1 xl:col-span-2">
                    <label className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-purple-100">Cobertura</label>
                    <select
                      value={diasCobertura}
                      onChange={(e) => setDiasCobertura(parseInt(e.target.value))}
                      className="h-11 w-full rounded-lg border border-white/20 bg-white px-3 text-gray-800 shadow-sm focus:ring-2 focus:ring-purple-300"
                    >
                      <option value={15}>15 dias</option>
                      <option value={30}>30 dias</option>
                      <option value={45}>45 dias</option>
                      <option value={60}>60 dias</option>
                      <option value={90}>90 dias</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2 xl:col-span-1 flex flex-col justify-end">
                    <span className="mb-1 block text-[11px] font-medium uppercase tracking-[0.12em] text-transparent select-none">
                      Atualizar
                    </span>
                    <button
                      onClick={() => buscarSugestoes()}
                      disabled={loadingSugestao}
                      className="flex h-11 w-full items-center justify-center rounded-lg bg-white px-4 text-sm font-semibold text-purple-700 shadow-sm transition hover:bg-purple-50 disabled:opacity-50"
                    >
                      {loadingSugestao ? '🔄 Analisando...' : '🔍 Atualizar'}
                    </button>
                  </div>
                  <div className="xl:col-span-12">
                    <div className="flex flex-col gap-2 rounded-2xl border border-white/15 bg-white/10 px-3 py-2 xl:flex-row xl:items-center xl:justify-between">
                      <div className="flex flex-wrap items-center gap-4 text-sm text-white">
                        <label className="flex cursor-pointer items-center gap-2">
                          <input
                            type="checkbox"
                            checked={apenasCriticos}
                            onChange={(e) => setApenasCriticos(e.target.checked)}
                            className="h-4 w-4 rounded"
                          />
                          <span>Apenas Críticos</span>
                        </label>
                        <label className="flex cursor-pointer items-center gap-2">
                          <input
                            type="checkbox"
                            checked={incluirAlerta}
                            onChange={(e) => setIncluirAlerta(e.target.checked)}
                            className="h-4 w-4 rounded"
                          />
                          <span>Incluir Alertas</span>
                        </label>
                        {grupoFornecedorAtual && (
                          <label className="flex cursor-pointer items-center gap-2 rounded-full bg-white/10 px-3 py-1">
                            <input
                              type="checkbox"
                              checked={incluirGrupoFornecedor}
                              onChange={(e) => {
                                setIncluirGrupoFornecedor(e.target.checked);
                                limparEstadosSugestao();
                              }}
                              className="h-4 w-4 rounded"
                            />
                            <span>Todos os CNPJs do grupo {grupoFornecedorAtual.nome}</span>
                          </label>
                        )}
                      </div>

                      {sugestoes.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2 text-xs text-purple-100">
                          {(() => {
                            const selecionados = sugestoes.filter(s => produtosSelecionados.includes(s.produto_id));
                            const totalQtd = selecionados.reduce((sum, s) => sum + obterQuantidadeInteira(s), 0);
                            const totalPeso = selecionados.reduce((sum, s) => sum + (obterQuantidadeInteira(s) * (s.peso_bruto || 0)), 0);
                            const totalValor = selecionados.reduce((sum, s) => sum + (obterQuantidadeInteira(s) * s.preco_unitario), 0);
                            return (
                              <>
                                <span className="rounded-full bg-white/10 px-2.5 py-1">📦 <strong className="text-white">{totalQtd}</strong> unidades</span>
                                <span className="rounded-full bg-white/10 px-2.5 py-1">⚖️ <strong className="text-white">{totalPeso.toFixed(1)} kg</strong></span>
                                <span className="rounded-full bg-white/10 px-2.5 py-1">💰 <strong className="text-white">R$ {totalValor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></span>
                                {selecionados.length === 0 && (
                                  <span className="italic opacity-80">(selecione produtos para ver o total)</span>
                                )}
                              </>
                            );
                          })()}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Tabela de Sugestões */}
            <div className="flex-1 overflow-auto p-5">
              {modoAplicacaoSugestao === 'replace' && (
                <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  A sugestão selecionada vai substituir os itens atuais do rascunho quando você confirmar.
                </div>
              )}
              {loadingSugestao ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Analisando produtos e calculando sugestões...</p>
                  </div>
                </div>
              ) : sugestoes.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500 text-lg">Nenhuma sugestão encontrada com os filtros aplicados</p>
                  <p className="text-gray-400 text-sm mt-2">Tente ajustar os filtros acima</p>
                </div>
              ) : (
                <>
                  {/* Ações Rápidas */}
                  <div className="sticky top-0 z-30 -mx-5 mb-3 bg-white/95 shadow-[0_10px_20px_-18px_rgba(15,23,42,0.45)] backdrop-blur-sm">
                    <div className="border-b border-gray-200 px-5 py-3">
                      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
                      <div className="flex flex-wrap items-center gap-2.5">
                        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={mostrarSoPreenchidos}
                            onChange={(e) => setMostrarSoPreenchidos(e.target.checked)}
                            className="w-4 h-4 rounded"
                          />
                          Mostrar só preenchidos (qtd {`>`} 0)
                        </label>
                        <button
                          onClick={selecionarTodosCriticos}
                          className="rounded-lg bg-red-100 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-200"
                        >
                          🔴 Selecionar Todos Críticos
                        </button>
                        <button
                          onClick={selecionarPreenchidosVisiveis}
                          className="rounded-lg bg-green-100 px-4 py-2 text-sm font-semibold text-green-700 transition hover:bg-green-200"
                        >
                          ✅ Selecionar Preenchidos
                        </button>
                        <button
                          onClick={desmarcarVisiveis}
                          className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-200"
                        >
                          ⛔ Desmarcar Visíveis
                        </button>
                      </div>
                      <span className="text-sm text-gray-500 xl:ml-auto">
                        {`${produtosSelecionados.length} selecionados (${selecionadosComQuantidade.length} preenchidos) · ${sugestoesFiltradas.length} exibidos de ${sugestoes.length} total`}
                      </span>
                    </div>
                  </div>

                    <div className="border-b border-slate-200 bg-white/95 px-5">
                    <div
                      ref={cabecalhoTabelaSugestaoRef}
                      className="overflow-hidden"
                    >
                      <table className={classeTabelaSugestao}>
                        {renderColGroupSugestao()}
                        <thead>
                          <tr>
                            <th className={`${classeCabecalhoTabelaSugestao} text-left`}>
                              <input
                                type="checkbox"
                                onChange={(e) => {
                                  const visiveis = sugestoesFiltradas;
                                  if (e.target.checked) {
                                    setProdutosSelecionados((prev) => [
                                      ...new Set([...prev, ...visiveis.map((s) => s.produto_id)]),
                                    ]);
                                  } else {
                                    const idsVisiveis = new Set(visiveis.map((s) => s.produto_id));
                                    setProdutosSelecionados((prev) => prev.filter((id) => !idsVisiveis.has(id)));
                                  }
                                }}
                                checked={sugestoesFiltradas.length > 0 && sugestoesFiltradas.every((s) => produtosSelecionados.includes(s.produto_id))}
                                className="w-4 h-4 rounded"
                              />
                            </th>
                            <th
                              className={`${classeCabecalhoTabelaSugestao} text-left`}
                              title="CRÍTICO = menos de 7 dias. ALERTA = menos de 14 dias. ATENÇÃO = menos de 30 dias."
                            >
                              Prioridade ℹ️
                            </th>
                            <th className={`${classeCabecalhoTabelaSugestao} text-left`}>
                              Produto
                            </th>
                            <th
                              className={`${classeCabecalhoTabelaSugestao} text-right`}
                              title="Quantity atual no estoque. Negativo indica divergência de ajuste."
                            >
                              Estoque ℹ️
                            </th>
                            <th
                              className={`${classeCabecalhoTabelaSugestao} text-right`}
                              title="Média de unidades vendidas por dia no período selecionado."
                            >
                              Consumo/dia ℹ️
                            </th>
                            <th
                              className={`${classeCabecalhoTabelaSugestao} text-right`}
                              title="Quantos dias o estoque atual dura ao ritmo de consumo atual. ∞ = sem venda recente."
                            >
                              Dias Restantes ℹ️
                            </th>
                            <th
                              className={`${classeCabecalhoTabelaSugestao} text-right`}
                              title="Quantidade sugerida para cobrir o período de cobertura definido. Você pode editar."
                            >
                              Qtd Sugerida ℹ️
                            </th>
                            <th
                              className={`${classeCabecalhoTabelaSugestao} text-right`}
                              title="Último preço de custo registrado para este produto."
                            >
                              Preço Unit. ℹ️
                            </th>
                            <th
                              className={`${classeCabecalhoTabelaSugestao} text-right`}
                              title="Qtd sugerida × preço unitário."
                            >
                              Total ℹ️
                            </th>
                            <th
                              className={`${classeCabecalhoTabelaSugestao} text-left`}
                              title="Tendência de vendas: comparação entre a primeira e segunda metade do período."
                            >
                              Tendência ℹ️
                            </th>
                          </tr>
                        </thead>
                      </table>
                    </div>
                  </div>
                </div>

                  <div ref={corpoTabelaSugestaoRef} className="overflow-x-auto">
                    <table className={classeTabelaSugestao}>
                      {renderColGroupSugestao()}
                      <tbody className="divide-y divide-gray-200">
                        {sugestoesFiltradas.map((sugestao) => (
                          <tr
                            key={sugestao.produto_id}
                            className={`hover:bg-gray-50 ${
                              produtosSelecionados.includes(sugestao.produto_id) ? 'bg-purple-50' : ''
                            }`}
                          >
                            <td className="px-4 py-3">
                              <input
                                type="checkbox"
                                checked={produtosSelecionados.includes(sugestao.produto_id)}
                                onChange={() => toggleSelecionarProduto(sugestao.produto_id)}
                                className="w-4 h-4 rounded"
                              />
                            </td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                sugestao.prioridade === 'CRÍTICO' ? 'bg-red-100 text-red-700' :
                                sugestao.prioridade === 'ALERTA' ? 'bg-yellow-100 text-yellow-700' :
                                sugestao.prioridade === 'ATENÇÃO' ? 'bg-orange-100 text-orange-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {sugestao.prioridade}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <div>
                                <div className="font-medium text-gray-900">{sugestao.produto_nome}</div>
                                <div className="text-xs text-gray-500">
                                  SKU: {sugestao.produto_sku || 'N/A'} | 
                                  Barras: {sugestao.produto_codigo_barras || 'N/A'}
                                  {sugestao.marca_nome ? ` | Marca: ${sugestao.marca_nome}` : ''}
                                </div>
                                {sugestao.fornecedor_nome && incluirGrupoFornecedor && (
                                  <div className="mt-1 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                                    Origem: {sugestao.fornecedor_nome}
                                  </div>
                                )}
                                {sugestao.observacao && (
                                  <div className="text-xs text-gray-600 mt-1 italic">{sugestao.observacao}</div>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <div className="font-medium">{Number(sugestao.estoque_atual).toFixed(2).replace(/\.?0+$/, '') || '0'}</div>
                              <div className="text-xs text-gray-500">Mín: {sugestao.estoque_minimo}</div>
                            </td>
                            <td className="px-4 py-3 text-right font-medium">
                              {sugestao.consumo_diario.toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className={`font-semibold ${
                                sugestao.dias_estoque && sugestao.dias_estoque < 7 ? 'text-red-600' :
                                sugestao.dias_estoque && sugestao.dias_estoque < 14 ? 'text-yellow-600' :
                                'text-green-600'
                              }`}>
                                {sugestao.dias_estoque ? `${sugestao.dias_estoque} dias` : '∞'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <input
                                type="text"
                                inputMode="numeric"
                                pattern="[0-9]*"
                                value={obterQuantidadeInteira(sugestao)}
                                onChange={(e) => atualizarQuantidadeSugerida(sugestao.produto_id, e.target.value)}
                                onFocus={() => setProdutoEditandoQuantidade(sugestao.produto_id)}
                                onBlur={() => {
                                  setProdutoEditandoQuantidade((atual) => (atual === sugestao.produto_id ? null : atual));
                                  const valorAtual = obterQuantidadeInteira(sugestao);
                                  atualizarQuantidadeSugerida(sugestao.produto_id, valorAtual);
                                }}
                                onWheel={(e) => e.currentTarget.blur()}
                                className="w-20 px-2 py-1 text-right font-bold text-purple-600 border rounded focus:ring-2 focus:ring-purple-300"
                              />
                            </td>
                            <td className="px-4 py-3 text-right">
                              R$ {sugestao.preco_unitario.toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-right font-semibold">
                              R$ {(obterQuantidadeInteira(sugestao) * sugestao.preco_unitario).toFixed(2)}
                            </td>
                            <td className="px-4 py-3">
                              <span className={`text-xs ${
                                sugestao.tendencia === 'CRESCIMENTO' ? 'text-green-600' :
                                sugestao.tendencia === 'QUEDA' ? 'text-red-600' :
                                'text-gray-600'
                              }`}>
                                {sugestao.tendencia === 'CRESCIMENTO' ? '📈' :
                                 sugestao.tendencia === 'QUEDA' ? '📉' :
                                 sugestao.tendencia === 'ESTÁVEL' ? '➡️' : '—'}
                                {sugestao.tendencia}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>

            {/* Footer com Ações */}
            {!loadingSugestao && sugestoes.length > 0 && (
              <div className="border-t p-6 bg-gray-50">
                <div className="flex justify-between items-center">
                  <div className="text-sm text-gray-600">
                    <div className="font-semibold mb-1">Resumo da Sugestão:</div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        🔴 <strong>{sugestoes.filter(s => s.prioridade === 'CRÍTICO').length}</strong> críticos
                      </div>
                      <div>
                        ⚠️ <strong>{sugestoes.filter(s => s.prioridade === 'ALERTA').length}</strong> em alerta
                      </div>
                      <div>
                        💰 Total: <strong>R$ {sugestoes
                          .filter(s => produtosSelecionados.includes(s.produto_id))
                          .reduce((sum, s) => sum + (obterQuantidadeInteira(s) * s.preco_unitario), 0)
                          .toFixed(2)}</strong>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={fecharModalSugestao}
                      className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-100"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={adicionarSugestoesAoPedido}
                      disabled={selecionadosComQuantidade.length === 0}
                      className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {modoAplicacaoSugestao === 'replace'
                        ? `Substituir rascunho com ${selecionadosComQuantidade.length} produtos`
                        : `Adicionar ${selecionadosComQuantidade.length} produtos ao pedido`}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const ModalGruposFornecedores = ({
  grupos,
  fornecedores,
  form,
  setForm,
  salvando,
  onClose,
  onSubmit,
  onNovo,
  onEditar,
  onExcluir,
  onToggleFornecedor,
}) => {
  const [buscaFornecedor, setBuscaFornecedor] = useState('');
  const fornecedoresSelecionadosSet = useMemo(
    () => new Set((form.fornecedor_ids || []).map((id) => Number(id))),
    [form.fornecedor_ids],
  );
  const fornecedoresSelecionados = useMemo(
    () => fornecedores.filter((fornecedor) => fornecedoresSelecionadosSet.has(Number(fornecedor.id))),
    [fornecedores, fornecedoresSelecionadosSet],
  );
  const normalizar = (texto = '') => texto
    .toLowerCase()
    .normalize('NFD')
    .replaceAll(/[\u0300-\u036f]/g, '');
  const fornecedoresFiltrados = useMemo(() => {
    const termo = normalizar(buscaFornecedor.trim());
    return fornecedores
      .filter((fornecedor) => {
        if (!termo) return true;
        return normalizar([
          fornecedor.nome,
          fornecedor.cnpj,
          fornecedor.cpf,
          fornecedor.razao_social,
          fornecedor.nome_fantasia,
        ].filter(Boolean).join(' ')).includes(termo);
      })
      .slice(0, 120);
  }, [fornecedores, buscaFornecedor]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Grupos de fornecedor</h2>
              <p className="mt-1 text-sm text-slate-600">
                Una CNPJs do mesmo fornecedor comercial sem alterar o cadastro fiscal de cada empresa.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100"
            >
              Fechar
            </button>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 gap-0 overflow-y-auto lg:grid-cols-[0.95fr_1.2fr]">
          <div className="border-r border-slate-200 bg-slate-50 p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Cadastrados</div>
                <div className="text-sm text-slate-600">{grupos.length} grupo(s)</div>
              </div>
              <button
                type="button"
                onClick={onNovo}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Novo
              </button>
            </div>

            <div className="space-y-3">
              {grupos.length === 0 && (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
                  Nenhum grupo criado ainda.
                </div>
              )}

              {grupos.map((grupo) => (
                <div
                  key={grupo.id}
                  className={`rounded-xl border p-4 ${
                    Number(form.id) === Number(grupo.id)
                      ? 'border-blue-300 bg-blue-50'
                      : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{grupo.nome}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {(grupo.fornecedores || []).length} CNPJ(s) vinculado(s)
                      </div>
                      {grupo.fornecedor_principal_nome && (
                        <div className="mt-1 text-xs font-semibold text-emerald-700">
                          Principal: {grupo.fornecedor_principal_nome}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => onEditar(grupo)}
                        className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => onExcluir(grupo)}
                        className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                      >
                        Excluir
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <form onSubmit={onSubmit} className="space-y-5 p-6">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-600">
                {form.id ? 'Editar grupo' : 'Novo grupo'}
              </div>
              <h3 className="text-xl font-bold text-slate-900">Unificacao comercial de CNPJs</h3>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-semibold text-slate-700">Nome do grupo</label>
                <input
                  value={form.nome}
                  onChange={(event) => setForm((prev) => ({ ...prev, nome: event.target.value }))}
                  placeholder="Ex: Distribuidora Pet Brasil"
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-semibold text-slate-700">Fornecedor principal</label>
                <select
                  value={form.fornecedor_principal_id}
                  onChange={(event) => setForm((prev) => ({ ...prev, fornecedor_principal_id: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-400"
                >
                  <option value="">Selecione</option>
                  {fornecedoresSelecionados.map((fornecedor) => (
                    <option key={fornecedor.id} value={fornecedor.id}>
                      {fornecedor.nome}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-semibold text-slate-700">Descricao interna</label>
              <textarea
                value={form.descricao}
                onChange={(event) => setForm((prev) => ({ ...prev, descricao: event.target.value }))}
                placeholder="Observacao opcional para compras, condicoes comerciais ou contatos."
                className="h-20 w-full rounded-lg border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div className="rounded-xl border border-slate-200">
              <div className="border-b border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="font-semibold text-slate-900">CNPJs do grupo</div>
                    <div className="text-sm text-slate-500">
                      {fornecedoresSelecionados.length} fornecedor(es) selecionado(s)
                    </div>
                  </div>
                  <input
                    value={buscaFornecedor}
                    onChange={(event) => setBuscaFornecedor(event.target.value)}
                    placeholder="Buscar fornecedor, CNPJ ou razao social"
                    className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm md:w-80"
                  />
                </div>
              </div>

              <div className="max-h-72 divide-y divide-slate-100 overflow-y-auto">
                {fornecedoresFiltrados.map((fornecedor) => {
                  const selecionado = fornecedoresSelecionadosSet.has(Number(fornecedor.id));
                  return (
                    <label
                      key={fornecedor.id}
                      className={`flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-blue-50 ${
                        selecionado ? 'bg-blue-50/70' : 'bg-white'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selecionado}
                        onChange={() => onToggleFornecedor(fornecedor.id)}
                        className="mt-1 h-4 w-4 rounded"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block font-semibold text-slate-900">{fornecedor.nome}</span>
                        <span className="block text-xs text-slate-500">
                          {fornecedor.cnpj || fornecedor.cpf || 'Sem CNPJ/CPF informado'}
                          {fornecedor.razao_social ? ` | ${fornecedor.razao_social}` : ''}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-5 md:flex-row md:justify-end">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-slate-300 px-5 py-2.5 font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={salvando}
                className="rounded-lg bg-blue-600 px-5 py-2.5 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
              >
                {salvando ? 'Salvando...' : 'Salvar grupo'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

const ModalDecisaoRascunho = ({
  contexto,
  estrategiaMesclaItens,
  setEstrategiaMesclaItens,
  onClose,
  onSelecionar,
}) => {
  const pedidoRascunho = contexto?.pedidoRascunho || {};
  const pedidoNovo = contexto?.pedidoNovo || {};
  const quantidadeItensRascunho = pedidoRascunho?.itens?.length || 0;
  const quantidadeItensPedidoNovo = pedidoNovo?.itens?.length || 0;
  const totalRascunhos = Number(contexto?.totalRascunhos || 1);
  const usandoMesmoRascunho = contexto?.tipo === 'atual';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-3xl rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-gray-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Consolidar rascunho do fornecedor</h2>
              <p className="mt-2 text-sm text-gray-600">
                Já existe um pedido em rascunho para este fornecedor. Escolha como o sistema deve tratar a nova sugestão.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            >
              Fechar
            </button>
          </div>
        </div>

        <div className="grid gap-4 px-6 py-5 md:grid-cols-3">
          <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Rascunho atual</div>
            <div className="mt-2 text-lg font-bold text-indigo-900">
              {pedidoRascunho?.numero_pedido || 'Rascunho em edição'}
            </div>
            <div className="mt-2 text-sm text-indigo-900">
              {quantidadeItensRascunho} item(ns) já no rascunho.
            </div>
            {totalRascunhos > 1 && (
              <div className="mt-3 text-xs text-indigo-700">
                Há {totalRascunhos} rascunhos deste fornecedor. O sistema vai usar o mais recente.
              </div>
            )}
          </div>

          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Pedido novo</div>
            <div className="mt-2 text-lg font-bold text-emerald-900">
              {quantidadeItensPedidoNovo} item(ns) montados agora
            </div>
            <div className="mt-2 text-sm text-emerald-900">
              Esses itens podem entrar no mesmo rascunho antes de abrir a sugestão inteligente.
            </div>
          </div>

          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">Objetivo</div>
            <div className="mt-2 text-sm text-amber-900">
              Consolidar tudo em um único pedido para o envio ao fornecedor ficar centralizado.
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 px-6 py-5">
          <div className="mb-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-sm font-semibold text-slate-900">Quando o mesmo produto já existir no rascunho</div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 bg-white p-3">
                <input
                  type="radio"
                  name="estrategia-mescla-itens"
                  checked={estrategiaMesclaItens === 'somar'}
                  onChange={() => setEstrategiaMesclaItens('somar')}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-semibold text-slate-900">Somar quantidades</span>
                  <span className="mt-1 block text-sm text-slate-600">
                    Junta o item novo com o item já existente no mesmo pedido.
                  </span>
                </span>
              </label>

              <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 bg-white p-3">
                <input
                  type="radio"
                  name="estrategia-mescla-itens"
                  checked={estrategiaMesclaItens === 'maior_quantidade'}
                  onChange={() => setEstrategiaMesclaItens('maior_quantidade')}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-semibold text-slate-900">Manter a maior quantidade</span>
                  <span className="mt-1 block text-sm text-slate-600">
                    Evita duplicidade e preserva a maior quantidade entre o rascunho e a nova entrada.
                  </span>
                </span>
              </label>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <button
              type="button"
              onClick={() => onSelecionar('mesclar')}
              className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-left transition hover:bg-blue-100"
            >
              <div className="text-base font-semibold text-blue-900">Mesclar</div>
              <div className="mt-2 text-sm text-blue-800">
                Soma o pedido novo com o rascunho existente e depois aplica a sugestão no mesmo pedido.
              </div>
            </button>

            <button
              type="button"
              onClick={() => onSelecionar('substituir')}
              className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-left transition hover:bg-amber-100"
            >
              <div className="text-base font-semibold text-amber-900">Substituir</div>
              <div className="mt-2 text-sm text-amber-800">
                {usandoMesmoRascunho
                  ? 'Troca os itens atuais do rascunho pela nova sugestão selecionada.'
                  : 'Troca o conteúdo do rascunho pelo pedido novo que você está montando agora.'}
              </div>
            </button>

            <button
              type="button"
              onClick={() => onSelecionar('manter')}
              className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-left transition hover:bg-gray-100"
            >
              <div className="text-base font-semibold text-gray-900">Manter rascunho</div>
              <div className="mt-2 text-sm text-gray-700">
                Abre ou mantém o rascunho atual sem aplicar uma nova sugestão agora.
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Modal de Recebimento
const ModalRecebimento = ({ pedido, onClose, onReceber }) => {
  const [itensRecebimento, setItensRecebimento] = useState(
    pedido.itens.map(item => ({
      item_id: item.id,
      quantidade_recebida: item.quantidade_pedida - item.quantidade_recebida,
      max: item.quantidade_pedida - item.quantidade_recebida
    }))
  );

  const handleReceber = () => {
    const itens = itensRecebimento
      .filter(i => i.quantidade_recebida > 0)
      .map(i => ({
        item_id: i.item_id,
        quantidade_recebida: parseFloat(i.quantidade_recebida)
      }));

    if (itens.length === 0) {
      toast.error('Informe a quantidade recebida de pelo menos 1 item');
      return;
    }

    onReceber(itens);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">📦 Receber Pedido {pedido.numero_pedido}</h2>
        
        <div className="space-y-4">
          {pedido.itens.map((item, index) => (
            <div key={item.id} className="border rounded-lg p-4">
              <div className="font-semibold mb-2">{item.produto_nome}</div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Pedido:</span>
                  <span className="ml-2 font-semibold">{item.quantidade_pedida}</span>
                </div>
                <div>
                  <span className="text-gray-600">Já Recebido:</span>
                  <span className="ml-2 font-semibold">{item.quantidade_recebida}</span>
                </div>
                <div>
                  <span className="text-gray-600">Pendente:</span>
                  <span className="ml-2 font-semibold text-orange-600">
                    {item.quantidade_pedida - item.quantidade_recebida}
                  </span>
                </div>
              </div>
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantidade a Receber
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max={itensRecebimento[index].max}
                  value={itensRecebimento[index].quantidade_recebida}
                  onChange={(e) => {
                    const novoValor = parseFloat(e.target.value) || 0;
                    const novaLista = [...itensRecebimento];
                    novaLista[index].quantidade_recebida = Math.min(novoValor, novaLista[index].max);
                    setItensRecebimento(novaLista);
                  }}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="flex gap-4 mt-6">
          <button
            onClick={handleReceber}
            className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700"
          >
            ✅ Confirmar Recebimento
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
          >
            ❌ Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

const SeletorColunasDocumentoPedido = ({ colunasSelecionadas, onChange, titulo, descricao }) => {
  const colunasNormalizadas = normalizarColunasDocumentoPedido(colunasSelecionadas);
  const semValores = !documentoTemColunasFinanceiras(colunasNormalizadas);

  const alternarColuna = (chave) => {
    if (colunasNormalizadas.includes(chave)) {
      onChange(colunasNormalizadas.filter((coluna) => coluna !== chave));
      return;
    }

    onChange([...colunasNormalizadas, chave]);
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">{titulo}</h3>
          <p className="mt-1 text-xs text-slate-500">{descricao}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onChange(COLUNAS_DOCUMENTO_FORNECEDOR)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            Somente fornecedor
          </button>
          <button
            type="button"
            onClick={() => onChange(COLUNAS_DOCUMENTO_COMPLETO)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            Documento completo
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {COLUNAS_DOCUMENTO_PEDIDO.map((coluna) => (
          <label
            key={coluna.chave}
            className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
          >
            <input
              type="checkbox"
              checked={colunasNormalizadas.includes(coluna.chave)}
              onChange={() => alternarColuna(coluna.chave)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span>{coluna.label}</span>
          </label>
        ))}
      </div>

      <div className={`mt-3 rounded-md px-3 py-2 text-xs ${semValores ? 'bg-amber-50 text-amber-800 border border-amber-200' : 'bg-emerald-50 text-emerald-800 border border-emerald-200'}`}>
        {semValores
          ? 'Sem colunas financeiras: frete, desconto e total tambem ficam ocultos no documento e no e-mail.'
          : 'Com colunas financeiras: o documento mostra custos, descontos e total do pedido.'}
      </div>
    </div>
  );
};

const ModalExportacaoPedido = ({
  pedido,
  onClose,
  onConfirmar,
  loading,
  colunasSelecionadas,
  onChangeColunas
}) => {
  if (!pedido) return null;

  const formatoLabel = pedido.formato === 'pdf' ? 'PDF' : 'Excel';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full">
        <div className="flex justify-between items-center gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-gray-800">Exportar {formatoLabel}</h2>
            <p className="mt-1 text-sm text-gray-500">Pedido {pedido.numero_pedido}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={loading}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <SeletorColunasDocumentoPedido
          colunasSelecionadas={colunasSelecionadas}
          onChange={onChangeColunas}
          titulo="Colunas do documento"
          descricao="Escolha exatamente o que deve aparecer no arquivo antes de baixar ou encaminhar."
        />

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onConfirmar}
            disabled={loading}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? `Gerando ${formatoLabel}...` : `Gerar ${formatoLabel}`}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded-lg border border-slate-300 px-4 py-3 font-semibold text-slate-700 hover:bg-slate-50"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

// Modal de Envio de Pedido
const ModalEnvioPedido = ({
  pedidoId,
  onClose,
  onEnviar,
  onEnvioManual,
  emailEnvioDisponivel,
  dadosEnvio,
  setDadosEnvio,
  colunasSelecionadas,
  onChangeColunas
}) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-800">📤 Enviar Pedido ao Fornecedor</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Campo E-mail */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              E-mail do Fornecedor
            </label>
            <input
              type="email"
              value={dadosEnvio.email}
              onChange={(e) => setDadosEnvio({ ...dadosEnvio, email: e.target.value })}
              placeholder="fornecedor@exemplo.com"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Campo WhatsApp */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              WhatsApp (futuro)
              <span className="ml-2 text-xs text-gray-500">(Em breve)</span>
            </label>
            <input
              type="tel"
              value={dadosEnvio.whatsapp}
              onChange={(e) => setDadosEnvio({ ...dadosEnvio, whatsapp: e.target.value })}
              placeholder="(00) 00000-0000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
              disabled
            />
          </div>

          {/* Seleção de Formatos */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Formatos para Envio
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={dadosEnvio.formatos.pdf}
                  onChange={(e) => setDadosEnvio({
                    ...dadosEnvio,
                    formatos: { ...dadosEnvio.formatos, pdf: e.target.checked }
                  })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm">📄 PDF</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={dadosEnvio.formatos.excel}
                  onChange={(e) => setDadosEnvio({
                    ...dadosEnvio,
                    formatos: { ...dadosEnvio.formatos, excel: e.target.checked }
                  })}
                  className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <span className="ml-2 text-sm">📊 Excel</span>
              </label>
            </div>
          </div>

          <SeletorColunasDocumentoPedido
            colunasSelecionadas={colunasSelecionadas}
            onChange={onChangeColunas}
            titulo="Conteudo do PDF / Excel"
            descricao="Use este ajuste quando quiser ocultar custos do fornecedor e enviar apenas codigo, descricao e quantidade."
          />

          {emailEnvioDisponivel === false && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              O servidor ainda não está configurado para enviar e-mails automaticamente.
              Você pode marcar este pedido como enviado manualmente por enquanto.
            </div>
          )}

          {/* Botões de Ação */}
          <div className="flex flex-col gap-3 pt-4">
            <button
              onClick={onEnviar}
              disabled={!emailEnvioDisponivel}
              className="w-full border border-blue-200 bg-blue-50 text-blue-700 py-3 rounded-lg font-semibold hover:bg-blue-100 transition-colors disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
            >
              📧 Enviar por E-mail
            </button>
            
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">ou</span>
              </div>
            </div>

            <button
              onClick={onEnvioManual}
              className="w-full border border-slate-200 bg-slate-50 text-slate-700 py-3 rounded-lg font-semibold hover:bg-slate-100 transition-colors"
            >
              ✅ Já enviei manualmente
            </button>

            <button
              onClick={onClose}
              className="w-full border border-gray-300 text-gray-700 py-2 rounded-lg font-semibold hover:bg-gray-50"
            >
              ❌ Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PedidosCompra;
