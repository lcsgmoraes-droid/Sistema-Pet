export default function useProdutosNovoPageComposition({
  adicionarProdutoKit,
  abaAtiva,
  buscaComponente,
  buscaPredecessor,
  camposEmEdicao,
  categoriasHierarquicas,
  clientes,
  departamentos,
  dropdownComponenteVisivel,
  entradaData,
  estoqueVirtualKit,
  formData,
  formatarData,
  formatarMoeda,
  fornecedores,
  fornecedorData,
  fornecedorEdit,
  handleAddFornecedor,
  handleApresentacaoPesoChange,
  handleBuscaPredecessorChange,
  handleCancelarVariacao,
  handleChange,
  handleChangeTributacao,
  handleClassificacaoRacaoChange,
  handleDeleteFornecedor,
  handleDeleteImagem,
  handleEditarLote,
  handleEditFornecedor,
  handleExcluirLote,
  handleExcluirVariacao,
  handleEntradaEstoque,
  handleFasePublicoChange,
  handleGerarCodigoBarras,
  handleGerarSKU,
  handlePersonalizarFiscal,
  handleRemoverPredecessor,
  handleSalvarEdicaoLote,
  handleSalvarVariacao,
  handleSaveFornecedor,
  handleSelecionarPredecessor,
  handleSetPrincipal,
  handleTipoRecorrenciaChange,
  handleToggleBuscaPredecessor,
  handleToggleFormVariacao,
  handleUploadImagem,
  handleVoltar,
  imagens,
  isEdicao,
  loading,
  loteEmEdicao,
  lotes,
  marcas,
  modalEdicaoLote,
  modalEntrada,
  modalFornecedor,
  mostrarBuscaPredecessor,
  mostrarFormVariacao,
  navigate,
  novaVariacao,
  opcoesApresentacoes,
  opcoesFases,
  opcoesLinhas,
  opcoesPortes,
  opcoesSabores,
  opcoesTratamentos,
  parseNumber,
  predecessorInfo,
  predecessorSelecionado,
  produtoKitSelecionado,
  produtosBusca,
  produtosDisponiveis,
  quantidadeKit,
  removerProdutoKit,
  salvando,
  setAbaAtiva,
  setCamposEmEdicao,
  setEntradaData,
  setFornecedorData,
  setFormData,
  setLoteEmEdicao,
  setModalEdicaoLote,
  setModalEntrada,
  setModalFornecedor,
  setNovaVariacao,
  setProdutoKitSelecionado,
  setQuantidadeKit,
  setBuscaComponente,
  setDropdownComponenteVisivel,
  sucessorInfo,
  uploadingImage,
  variacoes,
}) {
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
    onCancel: () => navigate('/produtos'),
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
    canShowComposicaoTab:
      abaAtiva === 9 &&
      (formData.tipo_produto === 'KIT' ||
        (formData.tipo_produto === 'VARIACAO' && formData.tipo_kit)),
    canShowVariacoesTab: abaAtiva === 8 && formData.tipo_produto === 'PAI',
    caracteristicasTabProps,
    composicaoTabProps,
    entradaModalProps,
    footerProps,
    fornecedoresTabProps,
    fornecedorModalProps,
    headerProps,
    imagensTabProps,
    loteModalProps,
    racaoTabProps,
    recorrenciaTabProps,
    statusBannersProps,
    tabsProps,
    tributacaoTabProps,
    variacoesTabProps,
  };
}
