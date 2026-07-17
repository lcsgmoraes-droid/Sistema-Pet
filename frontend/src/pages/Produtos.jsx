// ARQUIVO CRITICO DE PRODUCAO
// Este arquivo impacta diretamente operaÃ§Ãµes reais (PDV / Financeiro / Estoque).
// NÃƒO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenÃ¡rio real
// 3. Validar impacto financeiro

/**
 * PÃ¡gina de Listagem de Produtos - Estilo Bling
 */
import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import {
  exportarProdutoBling,
  exportarProdutosBlingLote,
  validarVinculoProdutoBling,
} from "../api/produtos";
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
  const [modalFusao, setModalFusao] = useState(false);
  const [blingActionKey, setBlingActionKey] = useState(null);
  const [blingBatchLoading, setBlingBatchLoading] = useState(false);
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

  const getProdutoBlingId = (produto) => String(produto?.bling_produto_id || "").trim();
  const getProdutoBlingActionKey = (produtoId) => `produto-bling-${produtoId}`;
  const getMensagemErroBling = (error, fallback) => {
    const detail = error?.response?.data?.detail ?? error?.response?.data?.message;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg || item?.message || String(item)).join("; ");
    }
    if (detail && typeof detail === "object") {
      return detail.message || JSON.stringify(detail);
    }
    return detail || error?.message || fallback;
  };

  const handleExportarProdutoBling = async (produto) => {
    if (!produto?.id) return;
    if (produto.tipo_produto === "PAI") {
      toast.error("Produto agrupador nao deve ser cadastrado diretamente no Bling.");
      return;
    }
    if (getProdutoBlingId(produto)) {
      toast.success("Produto ja esta vinculado ao Bling.");
      return;
    }

    setBlingActionKey(getProdutoBlingActionKey(produto.id));
    try {
      const response = await exportarProdutoBling(produto.id, true);
      const data = response.data || {};
      const status = data.status;
      const mensagem =
        status === "criado"
          ? "Produto cadastrado no Bling."
          : status === "vinculado_existente"
            ? "Produto ja existia no Bling e foi vinculado."
            : "Produto vinculado ao Bling.";
      const enriquecimentos = [
        data.imagens_enviadas ? `${data.imagens_enviadas} foto(s)` : "",
        data.fornecedores_enviados ? `${data.fornecedores_enviados} fornecedor(es)` : "",
      ].filter(Boolean);
      toast.success(
        enriquecimentos.length
          ? `${mensagem} Enviado tambem: ${enriquecimentos.join(" e ")}.`
          : mensagem,
      );
      if (data.fornecedores_detail) {
        toast(data.fornecedores_detail, { icon: "⚠️" });
      }
      await carregarDados();
    } catch (error) {
      console.error("Erro ao cadastrar produto no Bling:", error);
      toast.error(getMensagemErroBling(error, "Nao foi possivel cadastrar no Bling."));
    } finally {
      setBlingActionKey(null);
    }
  };

  const handleValidarVinculoProdutoBling = async (produto) => {
    if (!produto?.id || !getProdutoBlingId(produto)) return;

    setBlingActionKey(getProdutoBlingActionKey(produto.id));
    try {
      const response = await validarVinculoProdutoBling(produto.id);
      const data = response.data || {};
      if (data.existe) {
        toast.success(data.message || "Cadastro confirmado no Bling.");
      } else {
        toast(data.message || "O vinculo antigo foi removido. Agora voce pode criar novamente.", {
          icon: "🔄",
        });
        await carregarDados();
      }
    } catch (error) {
      console.error("Erro ao conferir produto no Bling:", error);
      toast.error(getMensagemErroBling(error, "Nao foi possivel conferir o cadastro no Bling."));
    } finally {
      setBlingActionKey(null);
    }
  };

  const handleEnviarSelecionadosBling = async () => {
    const selecionadosSet = new Set(selecionados.map(Number));
    const produtosSelecionados = produtosBrutos.filter((produto) =>
      selecionadosSet.has(Number(produto.id)),
    );
    const candidatos = produtosSelecionados.filter(
      (produto) => produto.tipo_produto !== "PAI" && !getProdutoBlingId(produto),
    );
    const ignorados = Math.max(selecionados.length - candidatos.length, 0);

    if (candidatos.length === 0) {
      toast.error("Selecione produtos sem cadastro no Bling.");
      return;
    }

    const avisoIgnorados =
      ignorados > 0
        ? `\n\n${ignorados} selecionado(s) ja tem Bling ou sao agrupadores e serao ignorados.`
        : "";
    const confirmado = window.confirm(
      `Cadastrar ${candidatos.length} produto(s) no Bling?${avisoIgnorados}`,
    );
    if (!confirmado) return;

    const produtoIds = candidatos.map((produto) => Number(produto.id));
    setBlingBatchLoading(true);
    try {
      const response = await exportarProdutosBlingLote(produtoIds, true);
      const data = response.data || {};
      const partes = [
        data.criados ? `${data.criados} criado(s)` : "",
        data.vinculados_existentes ? `${data.vinculados_existentes} vinculado(s)` : "",
        data.ja_vinculados ? `${data.ja_vinculados} ja vinculado(s)` : "",
      ].filter(Boolean);
      const resumo = partes.length ? ` ${partes.join(", ")}.` : "";

      if (data.erros) {
        toast.error(`Lote concluido com ${data.erros} erro(s).${resumo}`);
      } else {
        toast.success(`Lote enviado ao Bling.${resumo}`);
      }

      setSelecionados((prev) => prev.filter((id) => !produtoIds.includes(Number(id))));
      await carregarDados();
    } catch (error) {
      console.error("Erro ao cadastrar produtos no Bling:", error);
      toast.error(getMensagemErroBling(error, "Nao foi possivel enviar o lote ao Bling."));
    } finally {
      setBlingBatchLoading(false);
    }
  };

  const produtosFusao = useMemo(
    () => produtosBrutos.filter((produto) => selecionados.includes(produto.id)).slice(0, 2),
    [produtosBrutos, selecionados],
  );
  const { categorias, departamentos, fornecedores, marcas } = useProdutosCatalogos();
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
      blingBatchLoading,
      iniciarTour,
      menuRelatoriosAberto,
      menuRelatoriosRef,
      navigate,
      onEnviarSelecionadosBling: handleEnviarSelecionadosBling,
      onExcluirSelecionados: () => handleExcluirSelecionados(selecionados),
      onGerarRelatorioFiltrado,
      onGerarRelatorioGeral,
      onOpenEdicaoLote: handleAbrirEdicaoLote,
      onOpenFusao: () => setModalFusao(true),
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
      modalFusao,
      onCloseModalFusao: () => setModalFusao(false),
      onFusaoSucesso: () => {
        carregarDados();
        setSelecionados([]);
        setModalFusao(false);
      },
      onCloseModalEdicaoLote: () => setModalEdicaoLote(false),
      onSalvarEdicaoLote: handleSalvarEdicaoLote,
      produtosFusao,
      setDadosEdicaoLote,
    },
    reportState: {
      colunasRelatorioProdutos,
    },
    tableState: {
      blingActionKey,
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
      onExportarProdutoBling: handleExportarProdutoBling,
      onValidarVinculoProdutoBling: handleValidarVinculoProdutoBling,
      onChangeItensPorPagina: (value) => {
        setItensPorPagina(Number(value));
        setPaginaAtual(1);
      },
      onIrParaPagina: setPaginaAtual,
      onIrParaPrimeiraPagina: () => setPaginaAtual(1),
      onIrParaUltimaPagina: () => setPaginaAtual(totalPaginas),
      onPaginaAnterior: () => setPaginaAtual((prev) => Math.max(prev - 1, 1)),
      onProximaPagina: () => setPaginaAtual((prev) => Math.min(prev + 1, totalPaginas)),
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
    <div className="p-4 md:p-6">
      <ProdutosMainContent {...mainContentProps} />
      <ProdutosModalsLayer {...modalsLayerProps} />
    </div>
  );
}
