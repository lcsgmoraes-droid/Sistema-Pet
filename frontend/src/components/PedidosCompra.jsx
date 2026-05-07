import React, { useState, useEffect, useMemo, useRef } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';
import ModalConfronto from './compras/ModalConfronto';
import ModalGruposFornecedores from './compras/ModalGruposFornecedores';
import PedidosCompraFiltros from './compras/PedidosCompraFiltros';
import PedidosCompraSugestaoModal from './compras/PedidosCompraSugestaoModal';
import PedidosCompraTabela from './compras/PedidosCompraTabela';
import ModalDecisaoRascunho from './compras/ModalDecisaoRascunho';
import ModalEnvioPedido from './compras/ModalEnvioPedido';
import ModalExportacaoPedido from './compras/ModalExportacaoPedido';
import ModalRecebimento from './compras/ModalRecebimento';
import {
  COLUNAS_DOCUMENTO_COMPLETO,
  normalizarColunasDocumentoPedido,
} from './compras/pedidoDocumentoColunas';

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

const FILTROS_PEDIDOS_INICIAL = {
  status: '',
  fornecedor_id: '',
  busca: '',
  data_inicio: '',
  data_fim: ''
};

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
  const [filtrosPedidos, setFiltrosPedidos] = useState(FILTROS_PEDIDOS_INICIAL);
  const [loadingListaPedidos, setLoadingListaPedidos] = useState(false);
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

  const fornecedoresOrdenados = useMemo(
    () => [...fornecedores].sort((a, b) => String(a.nome || '').localeCompare(String(b.nome || ''), 'pt-BR')),
    [fornecedores],
  );

  const filtrosPedidosAtivos = useMemo(
    () => Object.values(filtrosPedidos).filter((valor) => String(valor || '').trim()).length,
    [filtrosPedidos],
  );

  const montarParametrosPedidos = (filtros = FILTROS_PEDIDOS_INICIAL) => {
    const params = { limit: 100 };
    Object.entries(filtros).forEach(([chave, valor]) => {
      const texto = String(valor || '').trim();
      if (texto) {
        params[chave] = texto;
      }
    });
    return params;
  };

  const extrairListaResposta = (data, chaves = []) => {
    if (Array.isArray(data)) return data;
    for (const chave of chaves) {
      if (Array.isArray(data?.[chave])) {
        return data[chave];
      }
    }
    return data?.items || [];
  };

  const atualizarFiltroPedidos = (campo, valor) => {
    setFiltrosPedidos((prev) => ({ ...prev, [campo]: valor }));
  };

  const aplicarFiltrosPedidos = (event) => {
    event?.preventDefault();
    carregarDados(filtrosPedidos, { apenasPedidos: true });
  };

  const limparFiltrosPedidos = () => {
    setFiltrosPedidos(FILTROS_PEDIDOS_INICIAL);
    carregarDados(FILTROS_PEDIDOS_INICIAL, { apenasPedidos: true });
  };

  const selecionarFiltroStatus = (statusPedido) => {
    const proximosFiltros = { ...filtrosPedidos, status: statusPedido };
    setFiltrosPedidos(proximosFiltros);
    carregarDados(proximosFiltros, { apenasPedidos: true });
  };

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
    carregarDados(FILTROS_PEDIDOS_INICIAL);
  }, []);

  const carregarDados = async (filtrosParaAplicar = filtrosPedidos, opcoes = {}) => {
    const params = montarParametrosPedidos(filtrosParaAplicar);
    setLoadingListaPedidos(true);
    try {
      if (opcoes.apenasPedidos) {
        const pedidosRes = await api.get('/pedidos-compra/', { params });
        setPedidos(extrairListaResposta(pedidosRes.data, ['pedidos']));
        return;
      }

      const [pedidosRes, fornecedoresRes, gruposRes, envioStatusRes] = await Promise.all([
        api.get('/pedidos-compra/', { params }),
        api.get('/clientes/?tipo_cadastro=fornecedor&apenas_ativos=true'),
        api.get('/fornecedor-grupos/'),
        api.get('/pedidos-compra/envio/status').catch(() => ({ data: { email_configurado: false } }))
      ]);

      // Tratar resposta dos pedidos (pode ser array direto ou objeto paginado)
      const pedidosData = extrairListaResposta(pedidosRes.data, ['pedidos']);
      
      // Tratar resposta dos fornecedores
      const fornecedoresData = extrairListaResposta(fornecedoresRes.data, ['clientes']);
      const gruposData = extrairListaResposta(gruposRes.data, ['grupos']);

      setPedidos(pedidosData);
      setFornecedores(fornecedoresData);
      setGruposFornecedores(gruposData);
      setEmailEnvioDisponivel(Boolean(envioStatusRes?.data?.email_configurado));
      // NÃO carregar produtos aqui - apenas quando fornecedor for selecionado
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar dados');
    } finally {
      setLoadingListaPedidos(false);
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

  const copiarSkuSugestao = async (sugestao) => {
    const sku = sugestao?.produto_sku || sugestao?.sku || sugestao?.codigo || '';

    if (!sku) {
      toast.error('SKU não disponível para este produto');
      return;
    }

    try {
      await navigator.clipboard.writeText(String(sku));
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

  const formatarQuantidadeCurta = (valor, casas = 2) => {
    const numero = Number(valor || 0);
    return numero.toLocaleString('pt-BR', {
      minimumFractionDigits: numero % 1 === 0 ? 0 : Math.min(casas, 1),
      maximumFractionDigits: casas,
    });
  };

  const obterVendaJanelaSugestao = (sugestao, dias) => {
    const janelas = sugestao?.vendas_janelas || {};
    return Number(
      janelas[String(dias)]
      ?? janelas[dias]
      ?? sugestao?.[`vendas_${dias}d`]
      ?? 0
    );
  };

  const montarTooltipGiroSugestao = (sugestao) => {
    const vendas = [7, 15, 30, 60, 90]
      .map((dias) => `${dias}d: ${formatarQuantidadeCurta(obterVendaJanelaSugestao(sugestao, dias))}`)
      .join(' | ');
    const granel = sugestao?.granel_consumo || {};
    const granelKg = Number(granel?.kg_periodo || 0);
    const granelPacotes = Number(granel?.pacotes_equivalentes_periodo || 0);
    const granelItens = Array.isArray(granel?.itens)
      ? granel.itens
        .filter((item) => Number(item?.kg || 0) > 0)
        .map((item) => `${item.produto_nome || 'Granel'}: ${formatarQuantidadeCurta(item.kg)} kg (${formatarQuantidadeCurta(item.pacotes_equivalentes, 3)} pacote eq.)`)
        .join(' | ')
      : '';
    const origens = Array.isArray(sugestao?.origens_venda)
      ? sugestao.origens_venda
        .filter((origem) => Number(origem?.quantidade || 0) > 0)
        .map((origem) => `${origem.canal}: ${formatarQuantidadeCurta(origem.quantidade)}`)
        .join(' | ')
      : '';
    const consumoObservado = Number(sugestao?.consumo_diario_observado ?? sugestao?.consumo_diario ?? 0);
    const consumoAjustado = Number(sugestao?.consumo_diario_ajustado ?? sugestao?.consumo_diario ?? 0);
    const coberturaAlvo = Number(sugestao?.dias_total_cobertura || 0);
    const reposicao = Number(sugestao?.dias_reposicao || 0);
    const leadIncluido = Boolean(sugestao?.lead_time_incluido_no_alvo);
    const linhas = [
      `Vendas por janela: ${vendas}`,
      `Consumo observado: ${formatarQuantidadeCurta(consumoObservado, 3)}/dia`,
      consumoAjustado > consumoObservado * 1.05
        ? `Consumo ajustado: ${formatarQuantidadeCurta(consumoAjustado, 3)}/dia`
        : '',
      coberturaAlvo
        ? leadIncluido
          ? `Cobertura alvo: ${formatarQuantidadeCurta(coberturaAlvo, 1)} dias (cobertura ${diasCobertura} + reposicao ${formatarQuantidadeCurta(reposicao, 1)})`
          : `Cobertura alvo: ${formatarQuantidadeCurta(coberturaAlvo, 1)} dias (estoque ja cobre a reposicao; alvo = cobertura ${diasCobertura})`
        : '',
      granelKg > 0
        ? `Consumo granel: ${formatarQuantidadeCurta(granelKg)} kg (${formatarQuantidadeCurta(granelPacotes, 3)} pacote(s) equivalentes)`
        : '',
      granelItens ? `Itens granel: ${granelItens}` : '',
      sugestao?.teve_ruptura
        ? `Ruptura no periodo: ${formatarQuantidadeCurta(sugestao.dias_sem_estoque || 0, 1)} dia(s) sem estoque`
        : '',
      sugestao?.ruptura_ajuste_motivo || '',
      sugestao?.estoque_derivado
        ? 'Estoque derivado por KIT/variacao virtual'
        : '',
      origens ? `Origens consideradas: ${origens}` : '',
    ];

    return linhas.filter(Boolean).join('\n');
  };

  const consumoFoiAjustado = (sugestao) => {
    if (sugestao?.ruptura_ajuste_aplicado !== undefined) {
      return Boolean(sugestao.ruptura_ajuste_aplicado);
    }
    return Number(sugestao?.consumo_diario_ajustado || 0)
      > Number(sugestao?.consumo_diario_observado || sugestao?.consumo_diario || 0) * 1.05;
  };

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

      <PedidosCompraFiltros
        filtrosPedidos={filtrosPedidos}
        filtrosPedidosAtivos={filtrosPedidosAtivos}
        fornecedoresOrdenados={fornecedoresOrdenados}
        loadingListaPedidos={loadingListaPedidos}
        onAplicar={aplicarFiltrosPedidos}
        onAtualizarFiltro={atualizarFiltroPedidos}
        onLimpar={limparFiltrosPedidos}
        onSelecionarStatus={selecionarFiltroStatus}
        pedidosCount={pedidos.length}
      />

      {/* Lista de Pedidos */}
      <PedidosCompraTabela
        abrirConfronto={abrirConfronto}
        abrirEdicao={abrirEdicao}
        abrirRecebimento={abrirRecebimento}
        cancelarPedido={cancelarPedido}
        confirmarPedido={confirmarPedido}
        enviarPedido={enviarPedido}
        exportarExcel={exportarExcel}
        exportarPDF={exportarPDF}
        obterFornecedorPorId={obterFornecedorPorId}
        pedidos={pedidos}
        reverterStatus={reverterStatus}
        verDetalhes={verDetalhes}
      />
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

      <PedidosCompraSugestaoModal
        mostrarSugestao={mostrarSugestao}
        fecharModalSugestao={fecharModalSugestao}
        filtroSugestao={filtroSugestao}
        setFiltroSugestao={setFiltroSugestao}
        filtroMarcasRef={filtroMarcasRef}
        setMostrarFiltroMarcas={setMostrarFiltroMarcas}
        resumoMarcasSelecionadas={resumoMarcasSelecionadas}
        mostrarFiltroMarcas={mostrarFiltroMarcas}
        setMarcasSelecionadas={setMarcasSelecionadas}
        marcasSelecionadas={marcasSelecionadas}
        marcasFornecedor={marcasFornecedor}
        alternarMarcaSelecionada={alternarMarcaSelecionada}
        periodoSugestao={periodoSugestao}
        setPeriodoSugestao={setPeriodoSugestao}
        diasCobertura={diasCobertura}
        setDiasCobertura={setDiasCobertura}
        buscarSugestoes={buscarSugestoes}
        loadingSugestao={loadingSugestao}
        apenasCriticos={apenasCriticos}
        setApenasCriticos={setApenasCriticos}
        incluirAlerta={incluirAlerta}
        setIncluirAlerta={setIncluirAlerta}
        grupoFornecedorAtual={grupoFornecedorAtual}
        incluirGrupoFornecedor={incluirGrupoFornecedor}
        setIncluirGrupoFornecedor={setIncluirGrupoFornecedor}
        limparEstadosSugestao={limparEstadosSugestao}
        sugestoes={sugestoes}
        produtosSelecionados={produtosSelecionados}
        obterQuantidadeInteira={obterQuantidadeInteira}
        modoAplicacaoSugestao={modoAplicacaoSugestao}
        mostrarSoPreenchidos={mostrarSoPreenchidos}
        setMostrarSoPreenchidos={setMostrarSoPreenchidos}
        selecionarTodosCriticos={selecionarTodosCriticos}
        selecionarPreenchidosVisiveis={selecionarPreenchidosVisiveis}
        desmarcarVisiveis={desmarcarVisiveis}
        selecionadosComQuantidade={selecionadosComQuantidade}
        sugestoesFiltradas={sugestoesFiltradas}
        setProdutosSelecionados={setProdutosSelecionados}
        classeTabelaSugestao={classeTabelaSugestao}
        renderColGroupSugestao={renderColGroupSugestao}
        classeCabecalhoTabelaSugestao={classeCabecalhoTabelaSugestao}
        cabecalhoTabelaSugestaoRef={cabecalhoTabelaSugestaoRef}
        corpoTabelaSugestaoRef={corpoTabelaSugestaoRef}
        toggleSelecionarProduto={toggleSelecionarProduto}
        copiarSkuSugestao={copiarSkuSugestao}
        montarTooltipGiroSugestao={montarTooltipGiroSugestao}
        formatarQuantidadeCurta={formatarQuantidadeCurta}
        obterVendaJanelaSugestao={obterVendaJanelaSugestao}
        consumoFoiAjustado={consumoFoiAjustado}
        atualizarQuantidadeSugerida={atualizarQuantidadeSugerida}
        setProdutoEditandoQuantidade={setProdutoEditandoQuantidade}
        adicionarSugestoesAoPedido={adicionarSugestoesAoPedido}
      />
    </div>
  );
};

export default PedidosCompra;
