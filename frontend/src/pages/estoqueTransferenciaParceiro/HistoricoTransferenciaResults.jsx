import BaixaLoteTransferenciaPanel from "./BaixaLoteTransferenciaPanel";
import HistoricoEntradaParceiroPanel from "./HistoricoEntradaParceiroPanel";
import HistoricoTransferenciaBulkActions from "./HistoricoTransferenciaBulkActions";
import HistoricoTransferenciaLista from "./HistoricoTransferenciaLista";

export default function HistoricoTransferenciaResults({
  loadingHistorico,
  loadingEntradasParceiro,
  historico,
  entradasParceiro,
  pessoaBaixaLoteNome,
  selecionadosHistorico,
  todosPaginaSelecionados,
  gerandoPdfConsolidado,
  historicoExpandidoIds,
  baixaAbertaId,
  baixaLoteAberta,
  formBaixa,
  setFormBaixa,
  formBaixaLote,
  setFormBaixaLote,
  previewBaixaLote,
  aplicacoesBaixaLote,
  loadingFormasPagamento,
  formasPagamento,
  totalCompensadoBaixa,
  totalAplicadoBaixaLote,
  totalCompensadoBaixaLote,
  diferencaAplicacaoBaixaLote,
  loadingPreviewBaixaLote,
  loadingContasPagarCompensacao,
  contasPagarCompensacao,
  contaRecebendo,
  salvandoBaixaLote,
  contaGerandoPdf,
  contaEnviandoEmail,
  contaExcluindo,
  totalPaginasHistorico,
  paginaHistorico,
  paginaEntradasParceiro,
  onAlternarSelecaoPaginaHistorico,
  onLimparSelecaoHistorico,
  onAbrirModalDocumentoTransferencia,
  onAlternarSelecaoHistorico,
  onAlternarExpansaoHistorico,
  onAbrirBaixaTransferencia,
  onIniciarEdicaoTransferencia,
  onExcluirTransferencia,
  onPreencherCompensacaoAutomatica,
  onLimparCompensacoesBaixa,
  onAtualizarValorCompensacao,
  onFecharBaixaTransferencia,
  onRegistrarBaixaTransferencia,
  onRecalcularPreviewBaixaLote,
  onToggleAplicacaoBaixaLote,
  onAtualizarValorAplicacaoBaixaLote,
  onAtualizarValorCompensacaoBaixaLote,
  onAjustarBaixaAoSaldoAcerto,
  onPreencherCompensacaoAutomaticaBaixaLote,
  onLimparCompensacoesBaixaLote,
  onFecharBaixaLoteTransferencia,
  onRegistrarBaixaLoteTransferencia,
  onSetPaginaHistorico,
  onSetPaginaEntradasParceiro,
}) {
  if (loadingHistorico) {
    return (
      <div className="px-6 py-12 text-center text-sm text-gray-500">
        Carregando historico de transferencias...
      </div>
    );
  }

  const baixaLotePanel = baixaLoteAberta ? (
    <BaixaLoteTransferenciaPanel
      pessoaNome={pessoaBaixaLoteNome}
      form={formBaixaLote}
      setForm={setFormBaixaLote}
      preview={previewBaixaLote}
      loadingPreview={loadingPreviewBaixaLote}
      salvando={salvandoBaixaLote}
      formasPagamento={formasPagamento}
      loadingFormasPagamento={loadingFormasPagamento}
      aplicacoes={aplicacoesBaixaLote}
      totalAplicado={totalAplicadoBaixaLote}
      totalCompensado={totalCompensadoBaixaLote}
      diferencaAplicacao={diferencaAplicacaoBaixaLote}
      contasPagarCompensacao={contasPagarCompensacao}
      loadingContasPagarCompensacao={loadingContasPagarCompensacao}
      onRecalcularPreview={onRecalcularPreviewBaixaLote}
      onToggleAplicacao={onToggleAplicacaoBaixaLote}
      onAtualizarValorAplicacao={onAtualizarValorAplicacaoBaixaLote}
      onAtualizarValorCompensacao={onAtualizarValorCompensacaoBaixaLote}
      onAjustarBaixaAoSaldoAcerto={onAjustarBaixaAoSaldoAcerto}
      onPreencherCompensacaoAutomatica={onPreencherCompensacaoAutomaticaBaixaLote}
      onLimparCompensacoesBaixa={onLimparCompensacoesBaixaLote}
      onFechar={onFecharBaixaLoteTransferencia}
      onConfirmar={onRegistrarBaixaLoteTransferencia}
    />
  ) : null;

  if (historico.items.length === 0) {
    return (
      <div className="space-y-4 px-6 py-5">
        {baixaLotePanel}
        <HistoricoEntradaParceiroPanel
          entradasParceiro={entradasParceiro}
          loading={loadingEntradasParceiro}
          pagina={paginaEntradasParceiro}
          onSetPagina={onSetPaginaEntradasParceiro}
        />
        <div className="py-8 text-center">
          <p className="text-base font-semibold text-gray-900">Nenhuma transferencia encontrada</p>
          <p className="mt-2 text-sm text-gray-500">
            Ajuste os filtros acima ou registre uma nova transferencia para comecar o historico.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 px-6 py-5">
      {baixaLotePanel}
      <HistoricoEntradaParceiroPanel
        entradasParceiro={entradasParceiro}
        loading={loadingEntradasParceiro}
        pagina={paginaEntradasParceiro}
        onSetPagina={onSetPaginaEntradasParceiro}
      />
      <HistoricoTransferenciaBulkActions
        selecionadosHistorico={selecionadosHistorico}
        todosPaginaSelecionados={todosPaginaSelecionados}
        gerandoPdfConsolidado={gerandoPdfConsolidado}
        onAlternarSelecaoPaginaHistorico={onAlternarSelecaoPaginaHistorico}
        onLimparSelecaoHistorico={onLimparSelecaoHistorico}
        onAbrirModalDocumentoTransferencia={onAbrirModalDocumentoTransferencia}
      />
      <HistoricoTransferenciaLista
        historico={historico}
        selecionadosHistorico={selecionadosHistorico}
        historicoExpandidoIds={historicoExpandidoIds}
        baixaAbertaId={baixaAbertaId}
        formBaixa={formBaixa}
        setFormBaixa={setFormBaixa}
        loadingFormasPagamento={loadingFormasPagamento}
        formasPagamento={formasPagamento}
        totalCompensadoBaixa={totalCompensadoBaixa}
        loadingContasPagarCompensacao={loadingContasPagarCompensacao}
        contasPagarCompensacao={contasPagarCompensacao}
        contaRecebendo={contaRecebendo}
        contaGerandoPdf={contaGerandoPdf}
        contaEnviandoEmail={contaEnviandoEmail}
        contaExcluindo={contaExcluindo}
        totalPaginasHistorico={totalPaginasHistorico}
        paginaHistorico={paginaHistorico}
        loadingHistorico={loadingHistorico}
        onAlternarSelecaoHistorico={onAlternarSelecaoHistorico}
        onAlternarExpansaoHistorico={onAlternarExpansaoHistorico}
        onAbrirBaixaTransferencia={onAbrirBaixaTransferencia}
        onIniciarEdicaoTransferencia={onIniciarEdicaoTransferencia}
        onAbrirModalDocumentoTransferencia={onAbrirModalDocumentoTransferencia}
        onExcluirTransferencia={onExcluirTransferencia}
        onPreencherCompensacaoAutomatica={onPreencherCompensacaoAutomatica}
        onLimparCompensacoesBaixa={onLimparCompensacoesBaixa}
        onAtualizarValorCompensacao={onAtualizarValorCompensacao}
        onFecharBaixaTransferencia={onFecharBaixaTransferencia}
        onRegistrarBaixaTransferencia={onRegistrarBaixaTransferencia}
        onSetPaginaHistorico={onSetPaginaHistorico}
      />
    </div>
  );
}
