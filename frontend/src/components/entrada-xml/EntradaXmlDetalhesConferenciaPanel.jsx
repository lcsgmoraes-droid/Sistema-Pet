import ActionButton from "../ui/ActionButton";

function EntradaXmlDetalhesConferenciaPanel({
  conferenciaObservacaoGeral,
  criandoPendenciaFornecedor,
  desfazendoConferencia,
  desfazerConferenciaAtual,
  formatarValorFiscal,
  gerarPendenciaFornecedor,
  gerarRascunhoDevolucao,
  gerandoRascunhoDevolucao,
  metaConferenciaAtual,
  mostrarCamposConferencia,
  notaSelecionada,
  resumoConferenciaAtual,
  salvandoConferencia,
  salvarConferenciaAtual,
  setConferenciaObservacaoGeral,
  setMostrarCamposConferencia,
}) {
  if (!resumoConferenciaAtual) {
    return null;
  }

  const estaPendente = notaSelecionada.status === "pendente";
  const temDivergencia = resumoConferenciaAtual.itens_com_divergencia > 0;
  const salvandoOuDesfazendo = salvandoConferencia || desfazendoConferencia;

  return (
    <div className="border-b border-slate-200 bg-white px-4 py-3 md:px-5">
      <div className="flex flex-wrap items-center gap-3">
        <div
          className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${metaConferenciaAtual?.cls || "border-gray-200 bg-gray-100 text-gray-700"}`}
        >
          {metaConferenciaAtual?.label || "Nao conferida"}
        </div>

        <p className="min-w-[240px] flex-1 text-xs text-slate-600">
          {estaPendente
            ? "Tudo comeca como conferido. Ajuste somente itens com falta ou avaria."
            : "Conferencia salva. Divergencias podem ser tratadas sem reverter a entrada."}
        </p>

        <div className="grid shrink-0 grid-cols-4 divide-x divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-slate-50 text-center">
          <div className="min-w-[70px] px-2.5 py-1.5">
            <div className="text-[10px] uppercase tracking-wide text-slate-400">Itens OK</div>
            <div className="text-sm font-bold text-emerald-700">
              {resumoConferenciaAtual.itens_ok}
            </div>
          </div>
          <div className="min-w-[76px] px-2.5 py-1.5">
            <div className="text-[10px] uppercase tracking-wide text-slate-400">Divergencias</div>
            <div className="text-sm font-bold text-orange-700">
              {resumoConferenciaAtual.itens_com_divergencia}
            </div>
          </div>
          <div className="min-w-[84px] px-2.5 py-1.5">
            <div className="text-[10px] uppercase tracking-wide text-slate-400">Recebida</div>
            <div className="text-sm font-bold text-slate-800">
              {formatarValorFiscal(resumoConferenciaAtual.quantidade_total_conferida, 2)}
            </div>
          </div>
          <div className="min-w-[84px] px-2.5 py-1.5">
            <div className="text-[10px] uppercase tracking-wide text-slate-400">Falta + avaria</div>
            <div className="text-sm font-bold text-rose-700">
              {formatarValorFiscal(
                resumoConferenciaAtual.quantidade_total_faltante +
                  resumoConferenciaAtual.quantidade_total_avariada,
                2,
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-2.5 flex flex-wrap gap-2">
        {estaPendente && (
          <>
            <ActionButton
              intent="neutral"
              onClick={() => setMostrarCamposConferencia((prev) => !prev)}
              size="sm"
              tone="soft"
            >
              {mostrarCamposConferencia ? "Ocultar ajuste manual" : "Editar quantidades e avarias"}
            </ActionButton>
            <ActionButton
              disabled={salvandoOuDesfazendo}
              intent="create"
              onClick={() => salvarConferenciaAtual()}
              size="sm"
            >
              {salvandoConferencia
                ? "Salvando..."
                : resumoConferenciaAtual.status === "nao_iniciada"
                  ? "Conferido"
                  : "Atualizar conferencia"}
            </ActionButton>
          </>
        )}

        {estaPendente && resumoConferenciaAtual.status !== "nao_iniciada" && (
          <ActionButton
            disabled={salvandoOuDesfazendo || Boolean(notaSelecionada?.entrada_estoque_realizada)}
            intent="warning"
            onClick={desfazerConferenciaAtual}
            size="sm"
            tone="soft"
          >
            {desfazendoConferencia ? "Desfazendo..." : "Desfazer conferencia"}
          </ActionButton>
        )}

        {!estaPendente && temDivergencia && (
          <>
            <ActionButton
              intent="neutral"
              onClick={() => setMostrarCamposConferencia((prev) => !prev)}
              size="sm"
              tone="soft"
            >
              {mostrarCamposConferencia ? "Ocultar tratativas" : "Abrir tratativas"}
            </ActionButton>
            <ActionButton
              disabled={salvandoOuDesfazendo}
              intent="edit"
              onClick={() => salvarConferenciaAtual()}
              size="sm"
            >
              {salvandoConferencia ? "Salvando..." : "Salvar tratativas"}
            </ActionButton>
          </>
        )}

        {temDivergencia && (
          <>
            <ActionButton
              disabled={criandoPendenciaFornecedor || salvandoOuDesfazendo}
              intent="info"
              onClick={gerarPendenciaFornecedor}
              size="sm"
              tone="soft"
            >
              {criandoPendenciaFornecedor ? "Gerando..." : "Gerar pendencia fornecedor"}
            </ActionButton>
            <ActionButton
              disabled={gerandoRascunhoDevolucao || salvandoOuDesfazendo}
              intent="warning"
              onClick={gerarRascunhoDevolucao}
              size="sm"
            >
              {gerandoRascunhoDevolucao ? "Gerando..." : "NF Devolucao das Divergencias"}
            </ActionButton>
          </>
        )}
      </div>

      {mostrarCamposConferencia && (
        <div className="mt-2.5">
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Observacao geral da conferencia
          </label>
          <textarea
            value={conferenciaObservacaoGeral}
            onChange={(event) => setConferenciaObservacaoGeral(event.target.value)}
            rows="1"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500"
            placeholder="Ex.: faltou 1 unidade do item X e 2 vieram avariadas."
          />
        </div>
      )}
    </div>
  );
}

export default EntradaXmlDetalhesConferenciaPanel;
