import PDVAcoesFooterCard from "./PDVAcoesFooterCard";
import PDVClienteCard from "./PDVClienteCard";
import PDVComissaoCard from "./PDVComissaoCard";
import PDVEntregaCard from "./PDVEntregaCard";
import PDVHeaderBar from "./PDVHeaderBar";
import PDVInfoBanners from "./PDVInfoBanners";
import PDVModoVisualizacaoBanner from "./PDVModoVisualizacaoBanner";
import PDVObservacoesCard from "./PDVObservacoesCard";
import PDVProdutosCard from "./PDVProdutosCard";
import PDVResumoFinanceiroCard from "./PDVResumoFinanceiroCard";

export default function PDVMainArea(props) {
  const {
    destaqueAbrirCaixa,
    destaqueVenda,
    caixaGuiaClasses,
    vendaGuiaClasses,
    iniciarTour,
    searchVendaQuery,
    onSearchVendaQueryChange,
    onBuscarVenda,
    vendaAtual,
    pendenciasCount,
    opportunitiesCount,
    painelAssistenteAberto,
    mensagensAssistenteLength,
    onAbrirPendenciasEstoque,
    onAbrirOportunidades,
    onToggleAssistente,
    caixaKey,
    onAbrirCaixa,
    onNavigateMeusCaixas,
    modoVisualizacao,
    loading,
    temCaixaAberto,
    onCancelarEdicao,
    onExcluirVenda,
    onSalvarVenda,
    onAbrirModalPagamento,
    onSairModoVisualizacao,
    emitirNotaVendaFinalizada,
    mudarStatusParaAberta,
    habilitarEdicao,
    onAbrirCadastroCliente,
    onAbrirHistoricoCliente,
    onAbrirModalAdicionarCredito,
    onAbrirVendasEmAberto,
    buscarCliente,
    buscarClientePorCodigoExato,
    clientesSugeridos,
    copiadoClienteCampo,
    onBuscarClienteChange,
    onCopiarCampoCliente,
    onRemoverCliente,
    onSelecionarCliente,
    onSelecionarPet,
    saldoCampanhas,
    vendasEmAbertoInfo,
    buscaProduto,
    buscaProdutoContainerRef,
    copiadoCodigoItem,
    inputProdutoRef,
    itensKitExpandidos,
    mostrarSugestoesProduto,
    onAbrirModalDescontoItem,
    onAdicionarNaListaEsperaRapido,
    onAlterarQuantidade,
    onAtualizarPetItem,
    onAtualizarQuantidadeItem,
    onBuscarProdutoChange,
    onBuscarProdutoFocus,
    onBuscarProdutoKeyDown,
    onCopiarCodigoProdutoCarrinho,
    onRemoverItem,
    onSelecionarProdutoSugerido,
    onToggleKitExpansion,
    pendenciasProdutoIds,
    produtosSugeridos,
    onObservacoesChange,
    entregadorSelecionado,
    entregadores,
    onAbrirModalEndereco,
    onEnderecoEntregaChange,
    onObservacoesEntregaChange,
    onSelecionarEndereco,
    onSelecionarEntregador,
    onTaxaEntregaTotalChange,
    onTaxaEntregadorChange,
    onTaxaLojaChange,
    onToggleTemEntrega,
    alertasCarrinho,
    codigoCupom,
    cupomAplicado,
    erroCupom,
    loadingCupom,
    onAbrirModalDescontoTotal,
    onAplicarCupom,
    onCodigoCupomChange,
    onCodigoCupomKeyDown,
    onRemoverCupom,
    onRemoverDescontoTotal,
    totalImpostos,
    buscaFuncionario,
    funcionarioComissao,
    funcionariosSugeridos,
    onBuscaFuncionarioChange,
    onBuscaFuncionarioFocus,
    onRemoverFuncionario,
    onSelecionarFuncionario,
    onToggleVendaComissionada,
    vendaComissionada,
    onNovaVenda,
  } = props;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <PDVHeaderBar
        destaqueAbrirCaixa={destaqueAbrirCaixa}
        destaqueVenda={destaqueVenda}
        caixaGuiaClasses={caixaGuiaClasses}
        iniciarTour={iniciarTour}
        searchVendaQuery={searchVendaQuery}
        onSearchVendaQueryChange={onSearchVendaQueryChange}
        onBuscarVenda={onBuscarVenda}
        vendaAtual={vendaAtual}
        pendenciasCount={pendenciasCount}
        opportunitiesCount={opportunitiesCount}
        painelAssistenteAberto={painelAssistenteAberto}
        mensagensAssistenteLength={mensagensAssistenteLength}
        onAbrirPendenciasEstoque={onAbrirPendenciasEstoque}
        onAbrirOportunidades={onAbrirOportunidades}
        onToggleAssistente={onToggleAssistente}
        menuCaixaKey={caixaKey}
        onAbrirCaixa={onAbrirCaixa}
        onNavigateMeusCaixas={onNavigateMeusCaixas}
        modoVisualizacao={modoVisualizacao}
        loading={loading}
        temCaixaAberto={temCaixaAberto}
        onCancelarEdicao={onCancelarEdicao}
        onExcluirVenda={onExcluirVenda}
        onSalvarVenda={onSalvarVenda}
        onAbrirModalPagamento={onAbrirModalPagamento}
      />

      <PDVInfoBanners
        temCaixaAberto={temCaixaAberto}
        modoVisualizacao={modoVisualizacao}
        vendaAtual={vendaAtual}
      />

      <PDVModoVisualizacaoBanner
        ativo={modoVisualizacao}
        vendaAtual={vendaAtual}
        onVoltar={onSairModoVisualizacao}
        emitirNotaVendaFinalizada={emitirNotaVendaFinalizada}
        mudarStatusParaAberta={mudarStatusParaAberta}
        habilitarEdicao={habilitarEdicao}
      />

      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-5xl mx-auto space-y-4">
          <PDVClienteCard
            buscarCliente={buscarCliente}
            buscarClientePorCodigoExato={buscarClientePorCodigoExato}
            clientesSugeridos={clientesSugeridos}
            copiadoClienteCampo={copiadoClienteCampo}
            destaqueVenda={destaqueVenda}
            modoVisualizacao={modoVisualizacao}
            onAbrirCadastroCliente={onAbrirCadastroCliente}
            onAbrirHistoricoCliente={onAbrirHistoricoCliente}
            onAbrirModalAdicionarCredito={onAbrirModalAdicionarCredito}
            onAbrirVendasEmAberto={onAbrirVendasEmAberto}
            onBuscarClienteChange={onBuscarClienteChange}
            onCopiarCampoCliente={onCopiarCampoCliente}
            onRemoverCliente={onRemoverCliente}
            onSelecionarCliente={onSelecionarCliente}
            onSelecionarPet={onSelecionarPet}
            onTrocarCliente={onRemoverCliente}
            saldoCampanhas={saldoCampanhas}
            vendaAtual={vendaAtual}
            vendaGuiaClasses={vendaGuiaClasses}
            vendasEmAbertoInfo={vendasEmAbertoInfo}
          />

          <PDVProdutosCard
            buscaProduto={buscaProduto}
            buscaProdutoContainerRef={buscaProdutoContainerRef}
            copiadoCodigoItem={copiadoCodigoItem}
            inputProdutoRef={inputProdutoRef}
            itensKitExpandidos={itensKitExpandidos}
            modoVisualizacao={modoVisualizacao}
            mostrarSugestoesProduto={mostrarSugestoesProduto}
            onAbrirModalDescontoItem={onAbrirModalDescontoItem}
            onAdicionarNaListaEsperaRapido={onAdicionarNaListaEsperaRapido}
            onAlterarQuantidade={onAlterarQuantidade}
            onAtualizarPetItem={onAtualizarPetItem}
            onAtualizarQuantidadeItem={onAtualizarQuantidadeItem}
            onBuscarProdutoChange={onBuscarProdutoChange}
            onBuscarProdutoFocus={onBuscarProdutoFocus}
            onBuscarProdutoKeyDown={onBuscarProdutoKeyDown}
            onCopiarCodigoProdutoCarrinho={onCopiarCodigoProdutoCarrinho}
            onRemoverItem={onRemoverItem}
            onSelecionarProdutoSugerido={onSelecionarProdutoSugerido}
            onToggleKitExpansion={onToggleKitExpansion}
            pendenciasProdutoIds={pendenciasProdutoIds}
            produtosSugeridos={produtosSugeridos}
            vendaAtual={vendaAtual}
          />

          <PDVObservacoesCard
            modoVisualizacao={modoVisualizacao}
            observacoes={vendaAtual.observacoes}
            onObservacoesChange={onObservacoesChange}
          />

          <PDVEntregaCard
            cliente={vendaAtual.cliente}
            entregadorSelecionado={entregadorSelecionado}
            entregadores={entregadores}
            modoVisualizacao={modoVisualizacao}
            onAbrirModalEndereco={onAbrirModalEndereco}
            onEnderecoEntregaChange={onEnderecoEntregaChange}
            onObservacoesEntregaChange={onObservacoesEntregaChange}
            onSelecionarEndereco={onSelecionarEndereco}
            onSelecionarEntregador={onSelecionarEntregador}
            onTaxaEntregaTotalChange={onTaxaEntregaTotalChange}
            onTaxaEntregadorChange={onTaxaEntregadorChange}
            onTaxaLojaChange={onTaxaLojaChange}
            onToggleTemEntrega={onToggleTemEntrega}
            vendaAtual={vendaAtual}
          />

          <PDVResumoFinanceiroCard
            alertasCarrinho={alertasCarrinho}
            codigoCupom={codigoCupom}
            cupomAplicado={cupomAplicado}
            erroCupom={erroCupom}
            loadingCupom={loadingCupom}
            modoVisualizacao={modoVisualizacao}
            onAbrirModalDescontoTotal={onAbrirModalDescontoTotal}
            onAplicarCupom={onAplicarCupom}
            onCodigoCupomChange={onCodigoCupomChange}
            onCodigoCupomKeyDown={onCodigoCupomKeyDown}
            onRemoverCupom={onRemoverCupom}
            onRemoverDescontoTotal={onRemoverDescontoTotal}
            totalImpostos={totalImpostos}
            vendaAtual={vendaAtual}
          />

          <PDVComissaoCard
            buscaFuncionario={buscaFuncionario}
            funcionarioComissao={funcionarioComissao}
            funcionariosSugeridos={funcionariosSugeridos}
            modoVisualizacao={modoVisualizacao}
            onBuscaFuncionarioChange={onBuscaFuncionarioChange}
            onBuscaFuncionarioFocus={onBuscaFuncionarioFocus}
            onRemoverFuncionario={onRemoverFuncionario}
            onSelecionarFuncionario={onSelecionarFuncionario}
            onToggleVendaComissionada={onToggleVendaComissionada}
            vendaComissionada={vendaComissionada}
          />
        </div>

        <PDVAcoesFooterCard
          itensCount={vendaAtual.itens.length}
          loading={loading}
          modoVisualizacao={modoVisualizacao}
          onAbrirModalPagamento={onAbrirModalPagamento}
          onNovaVenda={onNovaVenda}
          onSalvarVenda={onSalvarVenda}
          statusVenda={vendaAtual.status}
          temCaixaAberto={temCaixaAberto}
          vendaId={vendaAtual.id}
        />
      </div>
    </div>
  );
}
