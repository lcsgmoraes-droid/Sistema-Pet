import React from 'react';
import ModalConfronto from './ModalConfronto';
import ModalDecisaoRascunho from './ModalDecisaoRascunho';
import ModalEnvioPedido from './ModalEnvioPedido';
import ModalExportacaoPedido from './ModalExportacaoPedido';
import ModalGruposFornecedores from './ModalGruposFornecedores';
import ModalRecebimento from './ModalRecebimento';
import PedidosCompraSugestaoModal from './PedidosCompraSugestaoModal';

export default function PedidosCompraModalsLayer({
  mostrarRecebimento,
  pedidoSelecionado,
  setMostrarRecebimento,
  setPedidoSelecionado,
  receberPedido,
  mostrarConfronto,
  pedidoConfronto,
  setMostrarConfronto,
  setPedidoConfronto,
  carregarDados,
  mostrarModalEnvio,
  pedidoParaEnviar,
  setMostrarModalEnvio,
  confirmarEnvioPedido,
  marcarComoEnviadoManualmente,
  emailEnvioDisponivel,
  dadosEnvio,
  setDadosEnvio,
  colunasDocumentoPedido,
  atualizarColunasDocumento,
  mostrarModalExportacao,
  pedidoParaExportar,
  fecharModalExportacao,
  confirmarExportacaoPedido,
  exportandoArquivo,
  mostrarModalRascunhoSugestao,
  contextoRascunhoSugestao,
  estrategiaMesclaItens,
  setEstrategiaMesclaItens,
  fecharModalRascunho,
  decidirAcaoRascunhoSugestao,
  mostrarModalGruposFornecedores,
  gruposFornecedores,
  fornecedores,
  grupoFornecedorForm,
  setGrupoFornecedorForm,
  salvandoGrupoFornecedor,
  fecharModalGruposFornecedores,
  salvarGrupoFornecedor,
  iniciarNovoGrupoFornecedor,
  editarGrupoFornecedor,
  excluirGrupoFornecedor,
  alternarFornecedorNoGrupoForm,
  mostrarSugestao,
  fecharModalSugestao,
  filtroSugestao,
  setFiltroSugestao,
  filtroMarcasRef,
  setMostrarFiltroMarcas,
  resumoMarcasSelecionadas,
  mostrarFiltroMarcas,
  setMarcasSelecionadas,
  marcasSelecionadas,
  marcasFornecedor,
  alternarMarcaSelecionada,
  periodoSugestao,
  setPeriodoSugestao,
  diasCobertura,
  setDiasCobertura,
  buscarSugestoes,
  loadingSugestao,
  apenasCriticos,
  setApenasCriticos,
  incluirAlerta,
  setIncluirAlerta,
  grupoFornecedorAtual,
  incluirGrupoFornecedor,
  setIncluirGrupoFornecedor,
  apenasFornecedorPrincipal,
  setApenasFornecedorPrincipal,
  limparEstadosSugestao,
  sugestoes,
  produtosSelecionados,
  obterQuantidadeInteira,
  modoAplicacaoSugestao,
  mostrarSoPreenchidos,
  setMostrarSoPreenchidos,
  selecionarTodosCriticos,
  selecionarPreenchidosVisiveis,
  desmarcarVisiveis,
  selecionadosComQuantidade,
  sugestoesFiltradas,
  setProdutosSelecionados,
  classeTabelaSugestao,
  renderColGroupSugestao,
  classeCabecalhoTabelaSugestao,
  cabecalhoTabelaSugestaoRef,
  corpoTabelaSugestaoRef,
  toggleSelecionarProduto,
  copiarSkuSugestao,
  montarTooltipGiroSugestao,
  formatarQuantidadeCurta,
  obterVendaJanelaSugestao,
  consumoFoiAjustado,
  atualizarQuantidadeSugerida,
  setProdutoEditandoQuantidade,
  adicionarSugestoesAoPedido,
}) {
  return (
    <>
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

      {mostrarConfronto && pedidoConfronto && (
        <ModalConfronto
          pedido={pedidoConfronto}
          onClose={() => {
            setMostrarConfronto(false);
            setPedidoConfronto(null);
          }}
          onPedidoComplementarCriado={() => {
            carregarDados();
          }}
        />
      )}

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

      {mostrarModalGruposFornecedores && (
        <ModalGruposFornecedores
          grupos={gruposFornecedores}
          fornecedores={fornecedores}
          form={grupoFornecedorForm}
          setForm={setGrupoFornecedorForm}
          salvando={salvandoGrupoFornecedor}
          onClose={fecharModalGruposFornecedores}
          onSubmit={salvarGrupoFornecedor}
          onNovo={iniciarNovoGrupoFornecedor}
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
        apenasFornecedorPrincipal={apenasFornecedorPrincipal}
        setApenasFornecedorPrincipal={setApenasFornecedorPrincipal}
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
    </>
  );
}
