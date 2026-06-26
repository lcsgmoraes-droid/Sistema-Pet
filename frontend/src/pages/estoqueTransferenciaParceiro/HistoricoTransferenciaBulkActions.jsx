export default function HistoricoTransferenciaBulkActions({
  selecionadosHistorico,
  todosPaginaSelecionados,
  gerandoPdfConsolidado,
  onAlternarSelecaoPaginaHistorico,
  onLimparSelecaoHistorico,
  onAbrirModalDocumentoTransferencia,
}) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="text-sm font-semibold text-slate-900">PDF consolidado do acerto</p>
        <p className="mt-1 text-xs text-slate-600">
          Marque lancamentos especificos ou gere um PDF unico com todo o filtro atual.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onAlternarSelecaoPaginaHistorico}
          className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
        >
          {todosPaginaSelecionados ? "Desmarcar pagina" : "Selecionar pagina"}
        </button>
        <button
          type="button"
          onClick={onLimparSelecaoHistorico}
          disabled={selecionadosHistorico.length === 0}
          className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Limpar selecao
        </button>
        <button
          type="button"
          onClick={() => onAbrirModalDocumentoTransferencia(null, "pdf_consolidado")}
          disabled={gerandoPdfConsolidado}
          className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {gerandoPdfConsolidado
            ? "Gerando PDF consolidado..."
            : selecionadosHistorico.length > 0
              ? `Gerar PDF (${selecionadosHistorico.length} selecionado(s))`
              : "Gerar PDF do filtro atual"}
        </button>
      </div>
    </div>
  );
}
