export default function useProdutosNovoPageComposition({
  catalogos,
  fornecedoresState,
  imagensState,
  kitState,
  lotesState,
  navigationState,
  pageState,
  predecessorState,
  racaoState,
  recorrenciaState,
  tributacaoState,
  utilsState,
  variacoesState,
}) {
  const { categoriasHierarquicas, clientes, departamentos, marcas } = catalogos;
  const {
    fornecedores,
    fornecedorData,
    fornecedorEdit,
    handleAddFornecedor,
    handleDeleteFornecedor,
    handleEditFornecedor,
    handleSaveFornecedor,
    modalFornecedor,
    setFornecedorData,
    setModalFornecedor,
  } = fornecedoresState;
  const {
    handleDeleteImagem,
    handleSetPrincipal,
    handleUploadImagem,
    imagens,
    uploadingImage,
  } = imagensState;
  const {
    adicionarProdutoKit,
    buscaComponente,
    dropdownComponenteVisivel,
    estoqueVirtualKit,
    produtoKitSelecionado,
    produtosDisponiveis,
    quantidadeKit,
    removerProdutoKit,
    setBuscaComponente,
    setDropdownComponenteVisivel,
    setProdutoKitSelecionado,
    setQuantidadeKit,
  } = kitState;
  const {
    entradaData,
    handleEditarLote,
    handleEntradaEstoque,
    handleExcluirLote,
    handleSalvarEdicaoLote,
    loteEmEdicao,
    lotes,
    modalEdicaoLote,
    modalEntrada,
    setEntradaData,
    setLoteEmEdicao,
    setModalEdicaoLote,
    setModalEntrada,
  } = lotesState;
  const { handleVoltar, navigate, setAbaAtiva } = navigationState;
  const { abaAtiva, camposEmEdicao, formData, isEdicao, salvando, setCamposEmEdicao, setFormData } =
    pageState;
  const {
    buscaPredecessor,
    handleBuscaPredecessorChange,
    handleRemoverPredecessor,
    handleSelecionarPredecessor,
    handleToggleBuscaPredecessor,
    mostrarBuscaPredecessor,
    predecessorInfo,
    predecessorSelecionado,
    produtosBusca,
    sucessorInfo,
  } = predecessorState;
  const {
    handleApresentacaoPesoChange,
    handleClassificacaoRacaoChange,
    handleFasePublicoChange,
    opcoesApresentacoes,
    opcoesFases,
    opcoesLinhas,
    opcoesPortes,
    opcoesSabores,
    opcoesTratamentos,
  } = racaoState;
  const { handleTipoRecorrenciaChange } = recorrenciaState;
  const { handleChangeTributacao, handlePersonalizarFiscal } = tributacaoState;
  const { formatarData, formatarMoeda, handleChange, handleGerarCodigoBarras, handleGerarSKU, parseNumber } =
    utilsState;
  const {
    handleCancelarVariacao,
    handleExcluirVariacao,
    handleSalvarVariacao,
    handleToggleFormVariacao,
    mostrarFormVariacao,
    novaVariacao,
    setNovaVariacao,
    variacoes,
  } = variacoesState;

  const headerProps = {
    formData,
    isEdicao,
    onVoltar: handleVoltar,
  };

  const tabsProps = {
    abaAtiva,
    onChangeAba: setAbaAtiva,
    tipoProduto: formData.tipo_produto,
    tipoKit: formData.tipo_kit,
  };

  const statusBannersProps = {
    isEdicao,
    onAbrirPredecessor: () => navigate(`/produtos/${predecessorInfo.id}/editar`),
    onAbrirSucessor: () => navigate(`/produtos/${sucessorInfo.id}/editar`),
    predecessorInfo,
    sucessorInfo,
  };

  const caracteristicasTabProps = {
    buscaPredecessor,
    camposEmEdicao,
    categoriasHierarquicas,
    departamentos,
    formData,
    handleBuscaPredecessorChange,
    handleChange,
    handleGerarCodigoBarras,
    handleGerarSKU,
    handleRemoverPredecessor,
    handleSelecionarPredecessor,
    handleToggleBuscaPredecessor,
    isEdicao,
    marcas,
    mostrarBuscaPredecessor,
    parseNumber,
    predecessorSelecionado,
    produtosBusca,
    setAbaAtiva,
    setCamposEmEdicao,
    setFormData,
  };

  const imagensTabProps = {
    handleDeleteImagem,
    handleSetPrincipal,
    handleUploadImagem,
    imagens,
    isEdicao,
    uploadingImage,
  };

  const estoqueTabProps = {
    formData,
    formatarData,
    formatarMoeda,
    handleChange,
    handleEditarLote,
    handleExcluirLote,
    isEdicao,
    lotes,
    setModalEntrada,
  };

  const fornecedoresTabProps = {
    fornecedores,
    formatarMoeda,
    handleAddFornecedor,
    handleDeleteFornecedor,
    handleEditFornecedor,
    isEdicao,
  };

  const tributacaoTabProps = {
    formData,
    handleChangeTributacao,
    handlePersonalizarFiscal,
  };

  const recorrenciaTabProps = {
    formData,
    handleChange,
    handleTipoRecorrenciaChange,
  };

  const racaoTabProps = {
    formData,
    handleChange,
    handleApresentacaoPesoChange,
    handleClassificacaoRacaoChange,
    handleFasePublicoChange,
    opcoesApresentacoes,
    opcoesFases,
    opcoesLinhas,
    opcoesPortes,
    opcoesSabores,
    opcoesTratamentos,
  };

  const variacoesTabProps = {
    formData,
    isEdicao,
    mostrarFormVariacao,
    novaVariacao,
    setNovaVariacao,
    variacoes,
    handleToggleFormVariacao,
    handleCancelarVariacao,
    handleSalvarVariacao,
    handleExcluirVariacao,
    onEditarVariacao: (variacao) => navigate(`/produtos/${variacao.id}/editar`),
  };

  const composicaoTabProps = {
    formData,
    handleChange,
    estoqueVirtualKit,
    produtosDisponiveis,
    produtoKitSelecionado,
    setProdutoKitSelecionado,
    quantidadeKit,
    setQuantidadeKit,
    buscaComponente,
    setBuscaComponente,
    dropdownComponenteVisivel,
    setDropdownComponenteVisivel,
    adicionarProdutoKit,
    removerProdutoKit,
  };

  const footerProps = {
    isEdicao,
    onCancel: () => navigate("/produtos"),
    salvando,
  };

  const entradaModalProps = modalEntrada
    ? {
        entradaData,
        setEntradaData,
        onClose: () => setModalEntrada(false),
        onSubmit: handleEntradaEstoque,
      }
    : null;

  const loteModalProps =
    modalEdicaoLote && loteEmEdicao
      ? {
          loteEmEdicao,
          setLoteEmEdicao,
          onClose: () => {
            setModalEdicaoLote(false);
            setLoteEmEdicao(null);
          },
          onSubmit: handleSalvarEdicaoLote,
        }
      : null;

  const fornecedorModalProps = modalFornecedor
    ? {
        clientes,
        fornecedorData,
        fornecedorEdit,
        setFornecedorData,
        onClose: () => setModalFornecedor(false),
        onSubmit: handleSaveFornecedor,
      }
    : null;

  return {
    mainContentProps: {
      canShowComposicaoTab:
        abaAtiva === 9 &&
        (formData.tipo_produto === "KIT" ||
          (formData.tipo_produto === "VARIACAO" && formData.tipo_kit)),
      canShowVariacoesTab: abaAtiva === 8 && formData.tipo_produto === "PAI",
      caracteristicasTabProps,
      composicaoTabProps,
      estoqueTabProps,
      footerProps,
      fornecedoresTabProps,
      headerProps,
      imagensTabProps,
      racaoTabProps,
      recorrenciaTabProps,
      statusBannersProps,
      tabsProps,
      tributacaoTabProps,
      variacoesTabProps,
    },
    modalsLayerProps: {
      entradaModalProps,
      fornecedorModalProps,
      loteModalProps,
    },
  };
}
