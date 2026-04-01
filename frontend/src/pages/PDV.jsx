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

  return (
    <>
      <PDVDriveAlertBanner
        driveAlertVisible={driveAlertVisible}
        driveAguardando={driveAguardando}
        onClose={fecharDriveAlert}
        onConfirmarEntregue={confirmarDriveEntregue}
      />
      <div
        className="flex h-screen bg-gray-50"
        style={
          driveAlertVisible && driveAguardando.length > 0
            ? { paddingTop: "52px" }
            : {}
        }
      >
        <PDVMainArea
          destaqueAbrirCaixa={destaqueAbrirCaixa}
          destaqueVenda={destaqueVenda}
          caixaGuiaClasses={caixaGuiaClasses}
          vendaGuiaClasses={vendaGuiaClasses}
          iniciarTour={iniciarTour}
          searchVendaQuery={searchVendaQuery}
          onSearchVendaQueryChange={setSearchVendaQuery}
          onBuscarVenda={handleBuscarVenda}
          vendaAtual={vendaAtual}
          pendenciasCount={pendenciasCount}
          opportunitiesCount={opportunities.length}
          painelAssistenteAberto={painelAssistenteAberto}
          mensagensAssistenteLength={mensagensAssistente.length}
          onAbrirPendenciasEstoque={() => setMostrarPendenciasEstoque(true)}
          onAbrirOportunidades={() => {
            void abrirPainelOportunidades();
          }}
          onToggleAssistente={() => {
            void alternarPainelAssistente();
          }}
          caixaKey={caixaKey}
          onAbrirCaixa={() => setMostrarModalAbrirCaixa(true)}
          onNavigateMeusCaixas={() => navigate("/meus-caixas")}
          modoVisualizacao={modoVisualizacao}
          loading={loading}
          temCaixaAberto={temCaixaAberto}
          onCancelarEdicao={cancelarEdicao}
          onExcluirVenda={excluirVenda}
          onSalvarVenda={salvarVenda}
          onAbrirModalPagamento={abrirModalPagamento}
          onSairModoVisualizacao={() => {
            setModoVisualizacao(false);
            limparVenda();
          }}
          emitirNotaVendaFinalizada={emitirNotaVendaFinalizada}
          mudarStatusParaAberta={mudarStatusParaAberta}
          habilitarEdicao={habilitarEdicao}
          onAbrirCadastroCliente={() => setMostrarModalCliente(true)}
          onAbrirHistoricoCliente={() => setMostrarHistoricoCliente(true)}
          onAbrirModalAdicionarCredito={() =>
            setMostrarModalAdicionarCredito(true)
          }
          onAbrirVendasEmAberto={() => setMostrarVendasEmAberto(true)}
          buscarCliente={buscarCliente}
          buscarClientePorCodigoExato={buscarClientePorCodigoExato}
          clientesSugeridos={clientesSugeridos}
          copiadoClienteCampo={copiadoClienteCampo}
          onBuscarClienteChange={setBuscarCliente}
          onCopiarCampoCliente={copiarCampoCliente}
          onRemoverCliente={limparClienteSelecionado}
          onSelecionarCliente={selecionarCliente}
          onSelecionarPet={selecionarPet}
          saldoCampanhas={saldoCampanhas}
          vendasEmAbertoInfo={vendasEmAbertoInfo}
          buscaProduto={buscaProduto}
          buscaProdutoContainerRef={buscaProdutoContainerRef}
          copiadoCodigoItem={copiadoCodigoItem}
          inputProdutoRef={inputProdutoRef}
          itensKitExpandidos={itensKitExpandidos}
          mostrarSugestoesProduto={mostrarSugestoesProduto}
          onAbrirModalDescontoItem={abrirModalDescontoItem}
          onAdicionarNaListaEsperaRapido={adicionarNaListaEsperaRapido}
          onAlterarQuantidade={alterarQuantidade}
          onAtualizarPetItem={atualizarPetDoItem}
          onAtualizarQuantidadeItem={atualizarQuantidadeItem}
          onBuscarProdutoChange={handleBuscarProdutoChange}
          onBuscarProdutoFocus={handleBuscarProdutoFocus}
          onBuscarProdutoKeyDown={handleBuscarProdutoKeyDown}
          onCopiarCodigoProdutoCarrinho={copiarCodigoProdutoCarrinho}
          onRemoverItem={removerItem}
          onSelecionarProdutoSugerido={selecionarProdutoSugerido}
          onToggleKitExpansion={toggleKitExpansion}
          pendenciasProdutoIds={pendenciasProdutoIds}
          produtosSugeridos={produtosSugeridos}
          onObservacoesChange={(observacoes) =>
            setVendaAtual({
              ...vendaAtual,
              observacoes,
            })
          }
          entregadorSelecionado={entregadorSelecionado}
          entregadores={entregadores}
          onAbrirModalEndereco={abrirModalEndereco}
          onEnderecoEntregaChange={handleEnderecoEntregaChange}
          onObservacoesEntregaChange={handleObservacoesEntregaChange}
          onSelecionarEndereco={handleSelecionarEnderecoEntrega}
          onSelecionarEntregador={handleSelecionarEntregador}
          onTaxaEntregaTotalChange={handleTaxaEntregaTotalChange}
          onTaxaEntregadorChange={handleTaxaEntregadorChange}
          onTaxaLojaChange={handleTaxaLojaChange}
          onToggleTemEntrega={handleToggleTemEntrega}
          alertasCarrinho={alertasCarrinho}
          codigoCupom={codigoCupom}
          cupomAplicado={cupomAplicado}
          erroCupom={erroCupom}
          loadingCupom={loadingCupom}
          onAbrirModalDescontoTotal={abrirModalDescontoTotal}
          onAplicarCupom={aplicarCupom}
          onCodigoCupomChange={handleCodigoCupomChange}
          onCodigoCupomKeyDown={handleCodigoCupomKeyDown}
          onRemoverCupom={removerCupom}
          onRemoverDescontoTotal={removerDescontoTotal}
          totalImpostos={totalImpostos}
          buscaFuncionario={buscaFuncionario}
          funcionarioComissao={funcionarioComissao}
          funcionariosSugeridos={funcionariosSugeridos}
          onBuscaFuncionarioChange={handleBuscaFuncionarioChange}
          onBuscaFuncionarioFocus={handleBuscaFuncionarioFocus}
          onRemoverFuncionario={handleRemoverFuncionarioComissao}
          onSelecionarFuncionario={handleSelecionarFuncionarioComissao}
          onToggleVendaComissionada={handleToggleVendaComissionada}
          vendaComissionada={vendaComissionada}
          onNovaVenda={handleNovaVenda}
        />

        <PDVOverlays
          vendaAtual={vendaAtual}
          painelClienteAberto={painelClienteAberto}
          setPainelClienteAberto={setPainelClienteAberto}
          painelVendasAberto={painelVendasAberto}
          setPainelVendasAberto={setPainelVendasAberto}
          filtroVendas={filtroVendas}
          setFiltroVendas={setFiltroVendas}
          filtroStatus={filtroStatus}
          setFiltroStatus={setFiltroStatus}
          filtroTemEntrega={filtroTemEntrega}
          setFiltroTemEntrega={setFiltroTemEntrega}
          buscaNumeroVenda={buscaNumeroVenda}
          setBuscaNumeroVenda={setBuscaNumeroVenda}
          vendasRecentes={vendasRecentes}
          reabrirVenda={reabrirVenda}
          confirmandoRetirada={confirmandoRetirada}
          abrirConfirmacaoRetirada={abrirConfirmacaoRetirada}
          confirmarRetirada={confirmarRetirada}
          setConfirmandoRetirada={setConfirmandoRetirada}
          painelOportunidadesAberto={painelOportunidadesAberto}
          setPainelOportunidadesAberto={setPainelOportunidadesAberto}
          opportunities={opportunities}
          adicionarOportunidadeAoCarrinho={adicionarOportunidadeAoCarrinho}
          buscarAlternativaOportunidade={buscarAlternativaOportunidade}
          ignorarOportunidade={ignorarOportunidade}
          painelAssistenteAberto={painelAssistenteAberto}
          setPainelAssistenteAberto={setPainelAssistenteAberto}
          mensagensAssistente={mensagensAssistente}
          enviandoAssistente={enviandoAssistente}
          chatAssistenteEndRef={chatAssistenteEndRef}
          inputAssistente={inputAssistente}
          setInputAssistente={setInputAssistente}
          enviarMensagemAssistente={enviarMensagemAssistente}
          carregandoAnalise={carregandoAnalise}
          dadosAnalise={dadosAnalise}
          enderecoAtual={enderecoAtual}
          itemEditando={itemEditando}
          loadingCep={loadingCep}
          mostrarAnaliseVenda={mostrarAnaliseVenda}
          mostrarCalculadoraRacao={mostrarCalculadoraRacao}
          mostrarHistoricoCliente={mostrarHistoricoCliente}
          mostrarModalAbrirCaixa={mostrarModalAbrirCaixa}
          mostrarModalAdicionarCredito={mostrarModalAdicionarCredito}
          mostrarModalCliente={mostrarModalCliente}
          mostrarModalDescontoItem={mostrarModalDescontoItem}
          mostrarModalDescontoTotal={mostrarModalDescontoTotal}
          mostrarModalEndereco={mostrarModalEndereco}
          mostrarModalPagamento={mostrarModalPagamento}
          mostrarPendenciasEstoque={mostrarPendenciasEstoque}
          mostrarVendasEmAberto={mostrarVendasEmAberto}
          podeVerMargem={podeVerMargem}
          racaoIdFechada={racaoIdFechada}
          setTipoDescontoTotal={setTipoDescontoTotal}
          setValorDescontoTotal={setValorDescontoTotal}
          tipoDescontoTotal={tipoDescontoTotal}
          valorDescontoTotal={valorDescontoTotal}
          onAbrirCaixaSucesso={handleAbrirCaixaSucesso}
          onAnalisarVenda={
            podeVerMargem ? analisarVendaComFormasPagamento : null
          }
          onAplicarDescontoTotal={aplicarDescontoTotal}
          onBuscarCep={buscarCepModal}
          onChangeEnderecoAtual={setEnderecoAtual}
          onChangeItemEditando={setItemEditando}
          onClienteCriado={handleClienteCriadoRapido}
          onCloseAnalise={() => setMostrarAnaliseVenda(false)}
          onCloseCalculadoraRacao={fecharCalculadoraRacao}
          onCloseHistoricoCliente={() => setMostrarHistoricoCliente(false)}
          onCloseModalAbrirCaixa={() => setMostrarModalAbrirCaixa(false)}
          onCloseModalAdicionarCredito={() =>
            setMostrarModalAdicionarCredito(false)
          }
          onCloseModalCliente={() => setMostrarModalCliente(false)}
          onCloseModalDescontoItem={() => setMostrarModalDescontoItem(false)}
          onCloseModalDescontoTotal={() => setMostrarModalDescontoTotal(false)}
          onCloseModalEndereco={fecharModalEndereco}
          onCloseModalPagamento={() => setMostrarModalPagamento(false)}
          onClosePendenciasEstoque={() => setMostrarPendenciasEstoque(false)}
          onCloseVendasEmAberto={() => setMostrarVendasEmAberto(false)}
          onConfirmarCredito={handleConfirmarCreditoCliente}
          onConfirmarPagamento={handleConfirmarPagamento}
          onPendenciaAdicionada={carregarPendencias}
          onRemoverItemEditando={removerItemEditando}
          onSalvarDescontoItem={salvarDescontoItem}
          onSalvarEndereco={salvarEnderecoNoCliente}
          onVendaAtualizada={handleVendaAtualizadaAposPagamento}
          onVendasEmAbertoSucesso={handleVendasEmAbertoSucesso}
        />
      </div>
    </>
  );
}




