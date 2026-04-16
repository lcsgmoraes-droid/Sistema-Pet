// âš ï¸ ARQUIVO CRÃTICO DE PRODUÃ‡ÃƒO
// Este arquivo impacta diretamente operaÃ§Ãµes reais (PDV / Financeiro / Estoque).
// NÃƒO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenÃ¡rio real
// 3. Validar impacto financeiro

/**
 * PÃ¡gina de Listagem de Produtos - Estilo Bling
 */
import React, { useMemo, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import ProdutosMainContent from "../components/produtos/ProdutosMainContent";
import ProdutosModalsLayer from "../components/produtos/ProdutosModalsLayer";
import { createProdutosColunas } from "../components/produtos/produtosColumns";
import {
  corrigirTextoQuebrado,
  isProdutoComComposicao,
  montarMensagemConflitoExclusao,
  normalizeSearchText,
  obterEstoqueVisualProduto,
} from "../components/produtos/produtosUtils";
import useProdutosCatalogos from "../hooks/useProdutosCatalogos";
import useProdutosEdicao from "../hooks/useProdutosEdicao";
import useProdutosExclusao from "../hooks/useProdutosExclusao";
import useProdutosListagem from "../hooks/useProdutosListagem";
import useProdutosPageComposition from "../hooks/useProdutosPageComposition";
import useProdutosRelatorios from "../hooks/useProdutosRelatorios";
import useProdutosTabela from "../hooks/useProdutosTabela";
import { useTour } from "../hooks/useTour";
import { tourProdutos } from "../tours/tourDefinitions";

export default function Produtos() {
  const navigate = useNavigate();
  const { iniciarTour } = useTour("produtos", tourProdutos);
  const [modalImportacao, setModalImportacao] = useState(false);
  const [paisExpandidos, setPaisExpandidos] = useState([]);
  const produtosColunas = useMemo(() => createProdutosColunas(), []);
  const {
    carregarDados,
    filtros,
    handleFiltroChange,
    handleSelecionar,
    handleSelecionarTodos,
    itensPorPagina,
    loading,
    paginaAtual,
    persistirBusca,
    produtos,
    produtosBrutos,
    produtosVisiveisRef,
    selecionados,
    setItensPorPagina,
    setPaginaAtual,
    setPersistirBusca,
    setSelecionados,
    totalItens,
    totalPaginas,
  } = useProdutosListagem({
    normalizeSearchText,
    onOcultarPaisVariacoes: () => setPaisExpandidos([]),
    paisExpandidos,
  });
  const produtosTabela = useProdutosTabela({
    colunasTabela: produtosColunas,
    paisExpandidos,
    produtosVisiveisRef,
    setPaisExpandidos,
  });
  const {
    colunasRelatorio,
    colunasRelatorioProdutos,
    menuRelatoriosAberto,
    menuRelatoriosRef,
    modalRelatorioPersonalizado,
    onCloseModalRelatorio,
    onGerarRelatorioFiltrado,
    onGerarRelatorioGeral,
    onGerarRelatorioPersonalizado,
    onOpenModalRelatorio,
    onToggleColunaRelatorio,
    onToggleMenuRelatorios,
    ordenacaoRelatorio,
    setOrdenacaoRelatorio,
  } = useProdutosRelatorios({
    filtros,
    obterEstoqueVisualProduto,
  });
  const {
    abrirModalColunas,
    colunasTemporarias,
    filtrarColunas,
    getCorEstoque,
    getValidadeMaisProxima,
    kitsExpandidos,
    linhaProdutoRefs,
    modalColunas,
    onCloseModalColunas,
    restaurarColunasPadrao,
    salvarColunas,
    toggleColuna,
    toggleKitExpandido,
    togglePaiExpandido,
  } = produtosTabela;
  const copiarTexto = (texto, tipo) => {
    navigator.clipboard.writeText(texto);
    toast.success(`${tipo} copiado!`);
  };
  const { categorias, departamentos, fornecedores, marcas } =
    useProdutosCatalogos();
  const {
    dadosEdicaoLote,
    editandoMargem,
    editandoPreco,
    handleAbrirEdicaoLote,
    handleCancelarEdicaoPreco,
    handleEditarPreco,
    handleSalvarEdicaoLote,
    handleSalvarMargem,
    handleSalvarPreco,
    modalEdicaoLote,
    novoPreco,
    setDadosEdicaoLote,
    setEditandoMargem,
    setModalEdicaoLote,
    setNovoPreco,
  } = useProdutosEdicao({
    carregarDados,
    selecionados,
    setSelecionados,
  });
  const {
    autoSelecionarConflito,
    bloqueiosExclusao,
    handleExcluir,
    handleExcluirSelecionados,
    handleResolverConflitosExclusao,
    handleSelecionarTodasVariacoesDoPai,
    handleSelecionarVariacaoConflito,
    handleToggleAtivo,
    modalConflitoExclusao,
    onCloseModalConflito,
    onToggleAutoSelecionarConflito,
    pularConfirmacaoConflito,
    resolvendoConflitoExclusao,
    setPularConfirmacaoConflito,
    variacoesSelecionadasConflito,
  } = useProdutosExclusao({
    carregarDados,
    corrigirTextoQuebrado,
    montarMensagemConflitoExclusao,
    produtosBrutos,
    setSelecionados,
  });

  const { mainContentProps, modalsLayerProps } = useProdutosPageComposition({
    catalogosState: {
      categorias,
      departamentos,
      fornecedores,
      marcas,
    },
    columnsState: {
      abrirModalColunas,
      colunasRelatorio,
      colunasTemporarias,
      colunasTabela: produtosColunas,
      filtrarColunas,
      modalColunas,
      modalRelatorioPersonalizado,
      onCloseModalColunas,
      onCloseModalRelatorio,
      onGerarRelatorioPersonalizado,
      onOpenModalRelatorio,
      onRestaurarColunasPadrao: restaurarColunasPadrao,
      onSalvarColunas: salvarColunas,
      onToggleColuna: toggleColuna,
      onToggleColunaRelatorio,
      ordenacaoRelatorio,
      setOrdenacaoRelatorio,
    },
    conflictState: {
      autoSelecionarConflito,
      bloqueiosExclusao,
      modalConflitoExclusao,
      onCancelarConflito: handleResolverConflitosExclusao,
      onCloseModalConflito,
      onSelecionarTodasVariacoesDoPai: handleSelecionarTodasVariacoesDoPai,
      onSelecionarVariacaoConflito: handleSelecionarVariacaoConflito,
      onToggleAutoSelecionarConflito,
      onTogglePularConfirmacaoConflito: setPularConfirmacaoConflito,
      pularConfirmacaoConflito,
      resolvendoConflitoExclusao,
      variacoesSelecionadasConflito,
    },
    filtersState: {
      filtros,
      handleFiltroChange,
      persistirBusca,
      setPersistirBusca,
    },
    headerState: {
      iniciarTour,
      menuRelatoriosAberto,
      menuRelatoriosRef,
      navigate,
      onExcluirSelecionados: () => handleExcluirSelecionados(selecionados),
      onGerarRelatorioFiltrado,
      onGerarRelatorioGeral,
      onOpenEdicaoLote: handleAbrirEdicaoLote,
      onOpenImportacao: () => setModalImportacao(true),
      onToggleMenuRelatorios,
      selecionadosCount: selecionados.length,
    },
    importState: {
      modalImportacao,
      onCloseImportacao: () => setModalImportacao(false),
      onImportacaoSucesso: () => {
        carregarDados();
        setModalImportacao(false);
      },
    },
    modalsState: {
      dadosEdicaoLote,
      modalEdicaoLote,
      onCloseModalEdicaoLote: () => setModalEdicaoLote(false),
      onSalvarEdicaoLote: handleSalvarEdicaoLote,
      setDadosEdicaoLote,
    },
    reportState: {
      colunasRelatorioProdutos,
    },
    tableState: {
      editandoMargem,
      editandoPreco,
      getCorEstoque,
      getValidadeMaisProxima,
      handleCancelarEdicaoPreco,
      handleEditarPreco,
      handleExcluir,
      handleSalvarMargem,
      handleSalvarPreco,
      handleSelecionar,
      handleSelecionarTodos,
      handleToggleAtivo,
      itensPorPagina,
      kitsExpandidos,
      linhaProdutoRefs,
      loading,
      novoPreco,
      onChangeItensPorPagina: (value) => {
        setItensPorPagina(Number(value));
        setPaginaAtual(1);
      },
      onIrParaPagina: setPaginaAtual,
      onIrParaPrimeiraPagina: () => setPaginaAtual(1),
      onIrParaUltimaPagina: () => setPaginaAtual(totalPaginas),
      onPaginaAnterior: () => setPaginaAtual((prev) => Math.max(prev - 1, 1)),
      onProximaPagina: () =>
        setPaginaAtual((prev) => Math.min(prev + 1, totalPaginas)),
      paginaAtual,
      paisExpandidos,
      produtos,
      selecionados,
      setEditandoMargem,
      setNovoPreco,
      toggleKitExpandido,
      togglePaiExpandido,
      totalItens,
      totalPaginas,
    },
    utilsState: {
      copiarTexto,
      corrigirTextoQuebrado,
      isProdutoComComposicao,
    },
  });

  return (
    <div className="p-6">
      <ProdutosMainContent {...mainContentProps} />
      <ProdutosModalsLayer {...modalsLayerProps} />
    </div>
  );
}

