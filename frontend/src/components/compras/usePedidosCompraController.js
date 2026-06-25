import { useState, useEffect, useMemo } from "react";
import { toast } from "react-hot-toast";
import usePedidosCompraGruposFornecedores from "./usePedidosCompraGruposFornecedores";
import usePedidosCompraSugestao from "./usePedidosCompraSugestao";
import { createPedidosCompraDataController } from "./pedidosCompraDataController";
import { createPedidosCompraFormularioController } from "./pedidosCompraFormularioController";
import { createPedidosCompraItemController } from "./pedidosCompraItemController";
import { createPedidosCompraOperacoesController } from "./pedidosCompraOperacoesController";
import { COLUNAS_DOCUMENTO_COMPLETO } from "./pedidoDocumentoColunas";
import { numeroSeguro, textoContemTokens } from "./pedidoCompraUtils";

const FORM_DATA_INICIAL = {
  fornecedor_id: "",
  data_prevista_entrega: "",
  valor_frete: "0",
  valor_desconto: "0",
  observacoes: "",
  itens: [],
};

const ITEM_FORM_INICIAL = {
  produto_id: "",
  quantidade_pedida: "",
  preco_unitario: "",
};

const FILTROS_PEDIDOS_INICIAL = {
  status: "",
  fornecedor_id: "",
  busca: "",
  data_inicio: "",
  data_fim: "",
};

export default function usePedidosCompraController() {
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
    email: "",
    whatsapp: "",
    formatos: {
      pdf: true,
      excel: false,
    },
  });

  const [formData, setFormData] = useState(FORM_DATA_INICIAL);

  const [itemForm, setItemForm] = useState(ITEM_FORM_INICIAL);

  // Estados para inputs digitáveis
  const [fornecedorTexto, setFornecedorTexto] = useState("");
  const [produtoTexto, setProdutoTexto] = useState("");
  const [mostrarSugestoesProduto, setMostrarSugestoesProduto] = useState(false);
  const [incluirGrupoFornecedor, setIncluirGrupoFornecedor] = useState(false);

  const produtosFiltrados = useMemo(() => {
    const termo = produtoTexto.trim();
    if (!termo) return produtos.slice(0, 15);

    return produtos
      .filter((p) =>
        textoContemTokens(
          [p.nome, p.codigo, p.sku, p.codigo_barras, p.marca_nome, p.marca?.nome]
            .filter(Boolean)
            .join(" "),
          termo,
        ),
      )
      .slice(0, 15);
  }, [produtos, produtoTexto]);

  const fornecedoresOrdenados = useMemo(
    () =>
      [...fornecedores].sort((a, b) =>
        String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"),
      ),
    [fornecedores],
  );

  const registrarFornecedorCriado = (fornecedor) => {
    if (!fornecedor?.id) return;

    setFornecedores((prev) => {
      const existe = prev.some((item) => Number(item.id) === Number(fornecedor.id));
      const proximaLista = existe
        ? prev.map((item) => (Number(item.id) === Number(fornecedor.id) ? fornecedor : item))
        : [...prev, fornecedor];

      return proximaLista.sort((a, b) =>
        String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"),
      );
    });
  };

  const filtrosPedidosAtivos = useMemo(
    () => Object.values(filtrosPedidos).filter((valor) => String(valor || "").trim()).length,
    [filtrosPedidos],
  );

  const {
    atualizarFiltroPedidos,
    aplicarFiltrosPedidos,
    limparFiltrosPedidos,
    selecionarFiltroStatus,
    carregarDados,
  } = createPedidosCompraDataController({
    filtrosPedidos,
    filtrosPedidosInicial: FILTROS_PEDIDOS_INICIAL,
    setEmailEnvioDisponivel,
    setFiltrosPedidos,
    setFornecedores,
    setGruposFornecedores,
    setLoadingListaPedidos,
    setPedidos,
  });

  const selecionarFornecedor = (fornecedor) => {
    const grupo = obterGrupoDoFornecedor(fornecedor.id);
    setFornecedorTexto(fornecedor.nome || "");
    setFormData((prev) => ({ ...prev, fornecedor_id: fornecedor.id.toString(), itens: [] }));
    setIncluirGrupoFornecedor(Boolean(grupo));
    setItemForm(ITEM_FORM_INICIAL);
    setProdutoTexto("");
    // Limpar sugestões do fornecedor anterior
    limparEstadosSugestao();
    carregarProdutosFornecedor(fornecedor.id, { fornecedorGrupoId: grupo?.id });
  };

  const obterFornecedorPorId = (fornecedorId) =>
    fornecedores.find((f) => Number(f.id) === Number(fornecedorId));

  const obterFornecedorPreferencialDoGrupo = (grupo) => {
    const fornecedoresGrupo = Array.isArray(grupo?.fornecedores) ? grupo.fornecedores : [];
    const fornecedorId =
      Number(grupo?.fornecedor_principal_id) ||
      Number(grupo?.fornecedor_ids?.[0]) ||
      Number(fornecedoresGrupo[0]?.id);

    if (!Number.isFinite(fornecedorId) || fornecedorId <= 0) {
      return null;
    }

    return (
      obterFornecedorPorId(fornecedorId) ||
      fornecedoresGrupo.find((fornecedor) => Number(fornecedor.id) === fornecedorId) ||
      null
    );
  };

  const selecionarGrupoFornecedor = (grupo) => {
    const fornecedorBase = obterFornecedorPreferencialDoGrupo(grupo);

    if (!fornecedorBase?.id) {
      toast.error("Grupo de fornecedor sem fornecedor vinculado");
      return;
    }

    if (!obterFornecedorPorId(fornecedorBase.id)) {
      registrarFornecedorCriado(fornecedorBase);
    }
    setFornecedorTexto(grupo.nome || fornecedorBase.nome || "");
    setFormData((prev) => ({
      ...prev,
      fornecedor_id: fornecedorBase.id.toString(),
      itens: [],
    }));
    setIncluirGrupoFornecedor(true);
    setItemForm(ITEM_FORM_INICIAL);
    setProdutoTexto("");
    limparEstadosSugestao();
    carregarProdutosFornecedor(fornecedorBase.id, { fornecedorGrupoId: grupo.id });
  };

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

    return (
      gruposFornecedores.find(
        (grupo) =>
          Array.isArray(grupo.fornecedor_ids) &&
          grupo.fornecedor_ids.some((grupoFornecedorId) => Number(grupoFornecedorId) === id),
      ) || null
    );
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

  const {
    mostrarSugestao,
    sugestoes,
    loadingSugestao,
    loadingPrepararSugestao,
    periodoSugestao,
    setPeriodoSugestao,
    diasCobertura,
    setDiasCobertura,
    apenasCriticos,
    setApenasCriticos,
    incluirAlerta,
    setIncluirAlerta,
    produtosSelecionados,
    setProdutosSelecionados,
    filtroSugestao,
    setFiltroSugestao,
    mostrarSoPreenchidos,
    setMostrarSoPreenchidos,
    marcasSelecionadas,
    setMarcasSelecionadas,
    mostrarFiltroMarcas,
    setMostrarFiltroMarcas,
    mostrarModalRascunhoSugestao,
    setMostrarModalRascunhoSugestao,
    contextoRascunhoSugestao,
    setContextoRascunhoSugestao,
    modoAplicacaoSugestao,
    estrategiaMesclaItens,
    setEstrategiaMesclaItens,
    apenasFornecedorPrincipal,
    setApenasFornecedorPrincipal,
    cabecalhoTabelaSugestaoRef,
    corpoTabelaSugestaoRef,
    filtroMarcasRef,
    limparEstadosSugestao,
    buscarSugestoes,
    abrirModalSugestao,
    toggleSelecionarProduto,
    atualizarQuantidadeSugerida,
    obterQuantidadeInteira,
    formatarQuantidadeCurta,
    obterVendaJanelaSugestao,
    montarTooltipGiroSugestao,
    consumoFoiAjustado,
    sugestoesFiltradas,
    marcasFornecedor,
    selecionadosComQuantidade,
    resumoMarcasSelecionadas,
    fecharModalSugestao,
    selecionarTodosCriticos,
    selecionarPreenchidosVisiveis,
    desmarcarVisiveis,
    alternarMarcaSelecionada,
    classeCabecalhoTabelaSugestao,
    classeTabelaSugestao,
    renderColGroupSugestao,
    adicionarSugestoesAoPedido,
    setLoadingPrepararSugestao,
    setProdutoEditandoQuantidade,
  } = usePedidosCompraSugestao({
    formData,
    setFormData,
    produtos,
    obterParametrosGrupoFornecedor,
  });

  useEffect(() => {
    carregarDados(FILTROS_PEDIDOS_INICIAL);
  }, []);

  const {
    mostrarModalGruposFornecedores,
    grupoFornecedorForm,
    setGrupoFornecedorForm,
    salvandoGrupoFornecedor,
    abrirNovoGrupoFornecedor,
    editarGrupoFornecedor,
    alternarFornecedorNoGrupoForm,
    salvarGrupoFornecedor,
    excluirGrupoFornecedor,
    fecharModalGruposFornecedores,
    iniciarNovoGrupoFornecedor,
  } = usePedidosCompraGruposFornecedores({
    fornecedorIdAtual: formData.fornecedor_id,
    carregarDados,
  });

  const {
    carregarProdutosFornecedor,
    selecionarProduto,
    adicionarItem,
    removerItem,
    atualizarItemPedido,
    obterSkuItemPedido,
    copiarSkuSugestao,
    calcularTotal,
  } = createPedidosCompraItemController({
    formData,
    itemForm,
    itemFormInicial: ITEM_FORM_INICIAL,
    produtos,
    setFormData,
    setItemForm,
    setMostrarSugestoesProduto,
    setProdutos,
    setProdutoTexto,
  });

  const {
    fecharFormularioPedido,
    abrirNovoFormulario,
    aplicarPedidoNoFormulario,
    abrirFluxoSugestaoInteligente,
    fecharModalRascunho,
    decidirAcaoRascunhoSugestao,
  } = createPedidosCompraFormularioController({
    abrirModalSugestao,
    carregarProdutosFornecedor,
    contextoRascunhoSugestao,
    formData,
    formDataInicial: FORM_DATA_INICIAL,
    itemFormInicial: ITEM_FORM_INICIAL,
    limparEstadosSugestao,
    modoEdicao,
    obterFornecedorPorId,
    obterGrupoDoFornecedor,
    obterParametrosGrupoFornecedor,
    pedidoEditando,
    setContextoRascunhoSugestao,
    setEstrategiaMesclaItens,
    setFornecedorTexto,
    setFormData,
    setIncluirGrupoFornecedor,
    setItemForm,
    setLoadingPrepararSugestao,
    setModoEdicao,
    setMostrarForm,
    setMostrarModalRascunhoSugestao,
    setMostrarSugestoesProduto,
    setPedidoEditando,
    setProdutos,
    setProdutoTexto,
  });

  const {
    handleSubmit,
    enviarPedido,
    atualizarColunasDocumento,
    fecharModalExportacao,
    confirmarEnvioPedido,
    marcarComoEnviadoManualmente,
    confirmarPedido,
    exportarPDF,
    exportarExcel,
    confirmarExportacaoPedido,
    verDetalhes,
    reverterStatus,
    cancelarPedido,
    abrirEdicao,
    editarPedido,
    abrirRecebimento,
    abrirConfronto,
    receberPedido,
  } = createPedidosCompraOperacoesController({
    aplicarPedidoNoFormulario,
    carregarDados,
    colunasDocumentoPedido,
    dadosEnvio,
    emailEnvioDisponivel,
    exportandoArquivo,
    fecharFormularioPedido,
    formData,
    obterFornecedorPorId,
    pedidoEditando,
    pedidoParaEnviar,
    pedidoParaExportar,
    pedidoSelecionado,
    pedidos,
    setColunasDocumentoPedido,
    setDadosEnvio,
    setExportandoArquivo,
    setLoading,
    setMostrarConfronto,
    setMostrarModalEnvio,
    setMostrarModalExportacao,
    setMostrarRecebimento,
    setPedidoConfronto,
    setPedidoParaEnviar,
    setPedidoParaExportar,
    setPedidoSelecionado,
  });

  return {
    ITEM_FORM_INICIAL,
    adicionarItem,
    adicionarSugestoesAoPedido,
    alternarFornecedorNoGrupoForm,
    alternarMarcaSelecionada,
    apenasCriticos,
    apenasFornecedorPrincipal,
    aplicarFiltrosPedidos,
    abrirConfronto,
    abrirEdicao,
    abrirFluxoSugestaoInteligente,
    abrirNovoFormulario,
    abrirNovoGrupoFornecedor,
    abrirRecebimento,
    atualizarColunasDocumento,
    atualizarFiltroPedidos,
    atualizarItemPedido,
    atualizarQuantidadeSugerida,
    buscarSugestoes,
    cabecalhoTabelaSugestaoRef,
    calcularTotal,
    cancelarPedido,
    carregarDados,
    classeCabecalhoTabelaSugestao,
    classeTabelaSugestao,
    colunasDocumentoPedido,
    confirmarEnvioPedido,
    confirmarExportacaoPedido,
    confirmarPedido,
    consumoFoiAjustado,
    contextoRascunhoSugestao,
    copiarSkuSugestao,
    corpoTabelaSugestaoRef,
    dadosEnvio,
    decidirAcaoRascunhoSugestao,
    desmarcarVisiveis,
    diasCobertura,
    editarGrupoFornecedor,
    editarPedido,
    emailEnvioDisponivel,
    enviarPedido,
    estrategiaMesclaItens,
    excluirGrupoFornecedor,
    exportandoArquivo,
    exportarExcel,
    exportarPDF,
    fecharFormularioPedido,
    fecharModalExportacao,
    fecharModalGruposFornecedores,
    fecharModalRascunho,
    fecharModalSugestao,
    filtroMarcasRef,
    filtroSugestao,
    filtrosPedidos,
    filtrosPedidosAtivos,
    formData,
    fornecedorTexto,
    fornecedores,
    fornecedoresOrdenados,
    formatarQuantidadeCurta,
    grupoFornecedorAtual,
    grupoFornecedorForm,
    gruposFornecedores,
    handleSubmit,
    incluirAlerta,
    incluirGrupoFornecedor,
    iniciarNovoGrupoFornecedor,
    itemForm,
    limparEstadosSugestao,
    limparFiltrosPedidos,
    loading,
    loadingListaPedidos,
    loadingPrepararSugestao,
    loadingSugestao,
    marcasFornecedor,
    marcasSelecionadas,
    marcarComoEnviadoManualmente,
    modoAplicacaoSugestao,
    modoEdicao,
    montarTooltipGiroSugestao,
    mostrarConfronto,
    mostrarFiltroMarcas,
    mostrarForm,
    mostrarModalEnvio,
    mostrarModalExportacao,
    mostrarModalGruposFornecedores,
    mostrarModalRascunhoSugestao,
    mostrarRecebimento,
    mostrarSoPreenchidos,
    mostrarSugestao,
    mostrarSugestoesProduto,
    numeroSeguro,
    obterFornecedorPorId,
    obterGrupoDoFornecedor,
    obterQuantidadeInteira,
    obterSkuItemPedido,
    obterVendaJanelaSugestao,
    pedidoConfronto,
    pedidoParaEnviar,
    pedidoParaExportar,
    pedidoSelecionado,
    pedidos,
    periodoSugestao,
    produtoTexto,
    produtos,
    produtosFiltrados,
    produtosSelecionados,
    receberPedido,
    registrarFornecedorCriado,
    removerItem,
    renderColGroupSugestao,
    resumoMarcasSelecionadas,
    reverterStatus,
    salvarGrupoFornecedor,
    salvandoGrupoFornecedor,
    selecionarFiltroStatus,
    selecionarFornecedor,
    selecionarGrupoFornecedor,
    selecionarPreenchidosVisiveis,
    selecionarProduto,
    selecionarTodosCriticos,
    selecionadosComQuantidade,
    setApenasCriticos,
    setApenasFornecedorPrincipal,
    setDadosEnvio,
    setDiasCobertura,
    setEstrategiaMesclaItens,
    setFiltroSugestao,
    setFormData,
    setFornecedorTexto,
    setGrupoFornecedorForm,
    setIncluirAlerta,
    setIncluirGrupoFornecedor,
    setItemForm,
    setMarcasSelecionadas,
    setMostrarConfronto,
    setMostrarFiltroMarcas,
    setMostrarModalEnvio,
    setMostrarRecebimento,
    setMostrarSoPreenchidos,
    setMostrarSugestoesProduto,
    setPeriodoSugestao,
    setPedidoConfronto,
    setPedidoSelecionado,
    setProdutoEditandoQuantidade,
    setProdutoTexto,
    setProdutos,
    setProdutosSelecionados,
    sugestoes,
    sugestoesFiltradas,
    toggleSelecionarProduto,
    verDetalhes,
  };
}
