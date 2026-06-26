import HistoricoTransferenciaBulkActions from "./HistoricoTransferenciaBulkActions";
import HistoricoTransferenciaLista from "./HistoricoTransferenciaLista";

export default function HistoricoTransferenciaResults({
  loadingHistorico,
  historico,
  selecionadosHistorico,
  todosPaginaSelecionados,
  gerandoPdfConsolidado,
  historicoExpandidoIds,
  baixaAbertaId,
  formBaixa,
  setFormBaixa,
  loadingFormasPagamento,
  formasPagamento,
  totalCompensadoBaixa,
  loadingContasPagarCompensacao,
  contasPagarCompensacao,
  contaRecebendo,
  contaGerandoPdf,
  contaEnviandoEmail,
  contaExcluindo,
  totalPaginasHistorico,
  paginaHistorico,
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
  onSetPaginaHistorico,
}) {
  if (loadingHistorico) {
    return (
      <div className="px-6 py-12 text-center text-sm text-gray-500">
        Carregando historico de transferencias...
      </div>
    );
  }

  if (historico.items.length === 0) {
    return (
      <div className="px-6 py-12 text-center">
        <p className="text-base font-semibold text-gray-900">Nenhuma transferencia encontrada</p>
        <p className="mt-2 text-sm text-gray-500">
          Ajuste os filtros acima ou registre uma nova transferencia para comecar o historico.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 px-6 py-5">
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
