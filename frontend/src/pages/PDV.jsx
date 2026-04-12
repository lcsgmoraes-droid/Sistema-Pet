// âš ï¸ ARQUIVO CRÃTICO DE PRODUÃ‡ÃƒO
// Este arquivo impacta diretamente operaÃ§Ãµes reais (PDV / Financeiro / Estoque).
// NÃƒO alterar sem:
// 1. Entender o fluxo completo
// 2. Testar cenÃ¡rio real
// 3. Validar impacto financeiro

import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import PDVDriveAlertBanner from "../components/pdv/PDVDriveAlertBanner";
import PDVMainArea from "../components/pdv/PDVMainArea";
import PDVOverlays from "../components/pdv/PDVOverlays";
import { useAuth } from "../contexts/AuthContext";
import { usePDVAnalisePagamento } from "../hooks/usePDVAnalisePagamento";
import { usePDVAssistente } from "../hooks/usePDVAssistente";
import { usePDVCaixaRacao } from "../hooks/usePDVCaixaRacao";
import { usePDVCliente } from "../hooks/usePDVCliente";
import { usePDVComissao } from "../hooks/usePDVComissao";
import { usePDVDescontos } from "../hooks/usePDVDescontos";
import { usePDVEndereco } from "../hooks/usePDVEndereco";
import { usePDVEntrega } from "../hooks/usePDVEntrega";
import { usePDVEstoqueFiscal } from "../hooks/usePDVEstoqueFiscal";
import { usePDVInicializacao } from "../hooks/usePDVInicializacao";
import { usePDVOportunidades } from "../hooks/usePDVOportunidades";
import { usePDVPageComposition } from "../hooks/usePDVPageComposition";
import { usePDVProdutos } from "../hooks/usePDVProdutos";
import { usePDVSalvarVenda } from "../hooks/usePDVSalvarVenda";
import { usePDVUIState } from "../hooks/usePDVUIState";
import { usePDVVendasRecentes } from "../hooks/usePDVVendasRecentes";
import { usePDVVendaAtual } from "../hooks/usePDVVendaAtual";
import { useTour } from "../hooks/useTour";
import { tourPDV } from "../tours/tourDefinitions";
import { getGuiaClassNames } from "../utils/guiaHighlight";

export default function PDV() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const guiaAtiva = searchParams.get("guia");
  const destaqueAbrirCaixa = guiaAtiva === "abrir-caixa";
  const destaqueVenda =
    guiaAtiva === "venda-sem-entrega" ||
    guiaAtiva === "venda-com-entrega" ||
    guiaAtiva === "venda-com-comissao";
  const caixaGuiaClasses = getGuiaClassNames(destaqueAbrirCaixa);
  const vendaGuiaClasses = getGuiaClassNames(destaqueVenda);
  const { user } = useAuth();
  const { iniciarTour } = useTour("pdv", tourPDV, { delay: 1200 });

  // ðŸ”’ Controle de visibilidade de dados gerenciais (lucro, margem, custos)
  const podeVerMargem = user?.is_admin === true;

  // Estado da venda atual
  const [vendaAtual, setVendaAtual] = useState({
    cliente: null,
    pet: null,
    itens: [],
    subtotal: 0,
    desconto_valor: 0,
    desconto_percentual: 0,
    total: 0,
    observacoes: "",
    funcionario_id: null, // âœ… FuncionÃ¡rio para comissÃ£o
    entregador_id: null, // ðŸšš Entregador para entrega
    tem_entrega: false,
    entrega: {
      endereco_completo: "",
      taxa_entrega_total: 0,
      taxa_loja: 0,
      taxa_entregador: 0,
      observacoes_entrega: "",
    },
  });

  const {
    mostrarModalPagamento,
    setMostrarModalPagamento,
    mostrarModalCliente,
    setMostrarModalCliente,
    mostrarVendasEmAberto,
    setMostrarVendasEmAberto,
    mostrarHistoricoCliente,
    setMostrarHistoricoCliente,
    mostrarModalAdicionarCredito,
    setMostrarModalAdicionarCredito,
    mostrarPendenciasEstoque,
    setMostrarPendenciasEstoque,
    loading,
    setLoading,
    modoVisualizacao,
    setModoVisualizacao,
    searchVendaQuery,
    setSearchVendaQuery,
    painelVendasAberto,
    setPainelVendasAberto,
    painelClienteAberto,
    setPainelClienteAberto,
  } = usePDVUIState();

  const {
    buscarCliente,
    setBuscarCliente,
    clientesSugeridos,
    copiadoClienteCampo,
    vendasEmAbertoInfo,
    saldoCampanhas,
    buscarClientePorCodigoExato,
    selecionarCliente,
    selecionarPet,
    copiarCampoCliente,
    limparClienteSelecionado,
    handleClienteCriadoRapido: handleClienteCriadoRapidoHook,
    recarregarVendasEmAbertoClienteAtual,
    recarregarContextoClientePorId,
    recarregarContextoClienteAtual,
  } = usePDVCliente({
    vendaAtual,
    setVendaAtual,
  });

  const {
    vendasRecentes,
    filtroVendas,
    setFiltroVendas,
    filtroStatus,
    setFiltroStatus,
    confirmandoRetirada,
    setConfirmandoRetirada,
    filtroTemEntrega,
    setFiltroTemEntrega,
    buscaNumeroVenda,
    setBuscaNumeroVenda,
    driveAguardando,
    driveAlertVisible,
    carregarVendasRecentes,
    confirmarDriveEntregue,
    abrirConfirmacaoRetirada,
    confirmarRetirada,
    fecharDriveAlert,
  } = usePDVVendasRecentes();

  const {
    mostrarModalAbrirCaixa,
    setMostrarModalAbrirCaixa,
    caixaKey,
    temCaixaAberto,
    mostrarCalculadoraRacao,
    racaoIdFechada,
    fecharCalculadoraRacao,
    handleAbrirCaixaSucesso,
  } = usePDVCaixaRacao({
    vendaAtual,
    destaqueAbrirCaixa,
  });

  const {
    mostrarModalEndereco,
    enderecoAtual,
    setEnderecoAtual,
    loadingCep,
    abrirModalEndereco,
    fecharModalEndereco,
    buscarCepModal,
    salvarEnderecoNoCliente,
  } = usePDVEndereco({
    vendaAtual,
    setVendaAtual,
  });

  const {
    painelAssistenteAberto,
    setPainelAssistenteAberto,
    mensagensAssistente,
    inputAssistente,
    setInputAssistente,
    enviandoAssistente,
    chatAssistenteEndRef,
    alertasCarrinho,
    enviarMensagemAssistente,
    alternarPainelAssistente,
  } = usePDVAssistente(vendaAtual);
  const {
    painelOportunidadesAberto,
    setPainelOportunidadesAberto,
    opportunities,
    abrirPainelOportunidades,
    adicionarOportunidadeAoCarrinho,
    buscarAlternativaOportunidade,
    ignorarOportunidade,
  } = usePDVOportunidades(vendaAtual, user?.id);
  const {
    entregadores,
    entregadorSelecionado,
    sincronizarEntregadorDaVenda,
    handleToggleTemEntrega,
    handleSelecionarEnderecoEntrega,
    handleEnderecoEntregaChange,
    handleSelecionarEntregador,
    handleTaxaEntregaTotalChange,
    handleTaxaLojaChange,
    handleTaxaEntregadorChange,
    handleObservacoesEntregaChange,
  } = usePDVEntrega(vendaAtual, setVendaAtual);
  const {
    vendaComissionada,
    funcionarioComissao,
    funcionariosSugeridos,
    buscaFuncionario,
    sincronizarComissaoDaVenda,
    handleToggleVendaComissionada,
    handleBuscaFuncionarioFocus,
    handleBuscaFuncionarioChange,
    handleSelecionarFuncionarioComissao,
    handleRemoverFuncionarioComissao,
    limparComissao,
  } = usePDVComissao(setVendaAtual, modoVisualizacao);
  const {
    carregarVendaEspecifica,
    handleBuscarVenda,
    abrirModalPagamento,
    limparVenda,
    reabrirVenda,
  } = usePDVVendaAtual({
    vendaAtual,
    setVendaAtual,
    searchVendaQuery,
    setSearchVendaQuery,
    setLoading,
    setModoVisualizacao,
    setMostrarModalPagamento,
    entregadorSelecionado,
    limparComissao,
    sincronizarComissaoDaVenda,
    sincronizarEntregadorDaVenda,
    recarregarContextoClientePorId,
  });
  const { salvarVenda } = usePDVSalvarVenda({
    vendaAtual,
    loading,
    setLoading,
    temCaixaAberto,
    entregadorSelecionado,
    vendaComissionada,
    funcionarioComissao,
    limparVenda,
    carregarVendasRecentes: () => carregarVendasRecentes(),
  });
  const {
    mostrarModalDescontoItem,
    setMostrarModalDescontoItem,
    itemEditando,
    setItemEditando,
    mostrarModalDescontoTotal,
    setMostrarModalDescontoTotal,
    tipoDescontoTotal,
    setTipoDescontoTotal,
    valorDescontoTotal,
    setValorDescontoTotal,
    codigoCupom,
    cupomAplicado,
    loadingCupom,
    erroCupom,
    recalcularTotais,
    abrirModalDescontoItem,
    salvarDescontoItem,
    removerItemEditando,
    abrirModalDescontoTotal,
    aplicarDescontoTotal,
    removerDescontoTotal,
    aplicarCupom,
    removerCupom,
    handleCodigoCupomChange,
    handleCodigoCupomKeyDown,
  } = usePDVDescontos({
    vendaAtual,
    setVendaAtual,
  });
  const {
    buscaProduto,
    buscaProdutoContainerRef,
    copiadoCodigoItem,
    inputProdutoRef,
    itensKitExpandidos,
    mostrarSugestoesProduto,
    produtosSugeridos,
    alterarQuantidade,
    atualizarPetDoItem,
    atualizarQuantidadeItem,
    copiarCodigoProdutoCarrinho,
    handleBuscarProdutoChange,
    handleBuscarProdutoFocus,
    handleBuscarProdutoKeyDown,
    limparBuscaProduto,
    removerItem,
    selecionarProdutoSugerido,
    toggleKitExpansion,
  } = usePDVProdutos({
    vendaAtual,
    setVendaAtual,
    modoVisualizacao,
    temCaixaAberto,
    recalcularTotais,
  });
  const {
    pendenciasCount,
    pendenciasProdutoIds,
    totalImpostos,
    carregarPendencias,
    adicionarNaListaEsperaRapido,
  } = usePDVEstoqueFiscal({
    vendaAtual,
    limparBuscaProduto,
  });
  const {
    mostrarAnaliseVenda,
    setMostrarAnaliseVenda,
    dadosAnalise,
    carregandoAnalise,
    analisarVendaComFormasPagamento,
    habilitarEdicao,
    cancelarEdicao,
    excluirVenda,
    mudarStatusParaAberta,
    emitirNotaVendaFinalizada,
    handleConfirmarPagamento,
    handleVendaAtualizadaAposPagamento,
  } = usePDVAnalisePagamento({
    vendaAtual,
    setVendaAtual,
    setLoading,
    modoVisualizacao,
    setModoVisualizacao,
    setMostrarModalPagamento,
    limparVenda,
    carregarVendaEspecifica,
    carregarVendasRecentes: () => carregarVendasRecentes(),
    recarregarContextoClienteAtual,
  });
  const {
    handleNovaVenda,
    handleClienteCriadoRapido,
    handleVendasEmAbertoSucesso,
    handleConfirmarCreditoCliente,
  } = usePDVInicializacao({
    searchParams,
    carregarVendaEspecifica,
    handleClienteCriadoRapidoHook,
    setMostrarModalCliente,
    recarregarVendasEmAbertoClienteAtual,
    setVendaAtual,
    setMostrarModalAdicionarCredito,
    limparVenda,
  });

  const { driveAlertProps, containerStyle, mainAreaProps, overlayProps } =
    usePDVPageComposition({
      navigate,
      destaqueAbrirCaixa,
      destaqueVenda,
      caixaGuiaClasses,
      vendaGuiaClasses,
      iniciarTour,
      searchVendaQuery,
      setSearchVendaQuery,
      handleBuscarVenda,
      vendaAtual,
      pendenciasCount,
      opportunities,
      painelAssistenteAberto,
      mensagensAssistente,
      setMostrarPendenciasEstoque,
      abrirPainelOportunidades,
      alternarPainelAssistente,
      caixaKey,
      setMostrarModalAbrirCaixa,
      modoVisualizacao,
      loading,
      temCaixaAberto,
      cancelarEdicao,
      excluirVenda,
      salvarVenda,
      abrirModalPagamento,
      setModoVisualizacao,
      limparVenda,
      emitirNotaVendaFinalizada,
      mudarStatusParaAberta,
      habilitarEdicao,
      setMostrarModalCliente,
      setMostrarHistoricoCliente,
      setMostrarModalAdicionarCredito,
      setMostrarVendasEmAberto,
      buscarCliente,
      buscarClientePorCodigoExato,
      clientesSugeridos,
      copiadoClienteCampo,
      setBuscarCliente,
      copiarCampoCliente,
      limparClienteSelecionado,
      selecionarCliente,
      selecionarPet,
      saldoCampanhas,
      vendasEmAbertoInfo,
      buscaProduto,
      buscaProdutoContainerRef,
      copiadoCodigoItem,
      inputProdutoRef,
      itensKitExpandidos,
      mostrarSugestoesProduto,
      abrirModalDescontoItem,
      adicionarNaListaEsperaRapido,
      alterarQuantidade,
      atualizarPetDoItem,
      atualizarQuantidadeItem,
      handleBuscarProdutoChange,
      handleBuscarProdutoFocus,
      handleBuscarProdutoKeyDown,
      copiarCodigoProdutoCarrinho,
      removerItem,
      selecionarProdutoSugerido,
      toggleKitExpansion,
      pendenciasProdutoIds,
      produtosSugeridos,
      setVendaAtual,
      entregadorSelecionado,
      entregadores,
      abrirModalEndereco,
      handleEnderecoEntregaChange,
      handleObservacoesEntregaChange,
      handleSelecionarEnderecoEntrega,
      handleSelecionarEntregador,
      handleTaxaEntregaTotalChange,
      handleTaxaEntregadorChange,
      handleTaxaLojaChange,
      handleToggleTemEntrega,
      alertasCarrinho,
      codigoCupom,
      cupomAplicado,
      erroCupom,
      loadingCupom,
      abrirModalDescontoTotal,
      aplicarCupom,
      handleCodigoCupomChange,
      handleCodigoCupomKeyDown,
      removerCupom,
      removerDescontoTotal,
      totalImpostos,
      buscaFuncionario,
      funcionarioComissao,
      funcionariosSugeridos,
      handleBuscaFuncionarioChange,
      handleBuscaFuncionarioFocus,
      handleRemoverFuncionarioComissao,
      handleSelecionarFuncionarioComissao,
      handleToggleVendaComissionada,
      vendaComissionada,
      handleNovaVenda,
      painelClienteAberto,
      setPainelClienteAberto,
      painelVendasAberto,
      setPainelVendasAberto,
      filtroVendas,
      setFiltroVendas,
      filtroStatus,
      setFiltroStatus,
      filtroTemEntrega,
      setFiltroTemEntrega,
      buscaNumeroVenda,
      setBuscaNumeroVenda,
      vendasRecentes,
      reabrirVenda,
      confirmandoRetirada,
      abrirConfirmacaoRetirada,
      confirmarRetirada,
      setConfirmandoRetirada,
      painelOportunidadesAberto,
      setPainelOportunidadesAberto,
      adicionarOportunidadeAoCarrinho,
      buscarAlternativaOportunidade,
      ignorarOportunidade,
      setPainelAssistenteAberto,
      enviandoAssistente,
      chatAssistenteEndRef,
      inputAssistente,
      setInputAssistente,
      enviarMensagemAssistente,
      carregandoAnalise,
      dadosAnalise,
      enderecoAtual,
      itemEditando,
      loadingCep,
      mostrarAnaliseVenda,
      mostrarCalculadoraRacao,
      mostrarHistoricoCliente,
      mostrarModalAbrirCaixa,
      mostrarModalAdicionarCredito,
      mostrarModalCliente,
      mostrarModalDescontoItem,
      setMostrarModalDescontoItem,
      mostrarModalDescontoTotal,
      setMostrarModalDescontoTotal,
      mostrarModalEndereco,
      fecharModalEndereco,
      mostrarModalPagamento,
      setMostrarModalPagamento,
      mostrarPendenciasEstoque,
      mostrarVendasEmAberto,
      podeVerMargem,
      racaoIdFechada,
      setTipoDescontoTotal,
      setValorDescontoTotal,
      tipoDescontoTotal,
      valorDescontoTotal,
      handleAbrirCaixaSucesso,
      analisarVendaComFormasPagamento,
      aplicarDescontoTotal,
      buscarCepModal,
      setEnderecoAtual,
      setItemEditando,
      handleClienteCriado: handleClienteCriadoRapido,
      fecharCalculadoraRacao,
      handleConfirmarCreditoCliente,
      handleConfirmarPagamento,
      carregarPendencias,
      removerItemEditando,
      salvarDescontoItem,
      salvarEnderecoNoCliente,
      handleVendaAtualizadaAposPagamento,
      handleVendasEmAbertoSucesso,
      driveAlertVisible,
      driveAguardando,
      fecharDriveAlert,
      confirmarDriveEntregue,
    });

  return (
    <>
      <PDVDriveAlertBanner {...driveAlertProps} />
      <div className="flex h-screen bg-gray-50" style={containerStyle}>
        <PDVMainArea {...mainAreaProps} />
        <PDVOverlays {...overlayProps} />
      </div>
    </>
  );
}




