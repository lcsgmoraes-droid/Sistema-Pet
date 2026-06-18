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
    <div className="border-b bg-emerald-50/40 px-6 py-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-3">
          <div
            className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${metaConferenciaAtual?.cls || "border-gray-200 bg-gray-100 text-gray-700"}`}
          >
            {metaConferenciaAtual?.label || "Nao conferida"}
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div className="rounded-lg border border-white/70 bg-white/80 p-3">
              <div className="text-xs uppercase tracking-wide text-gray-500">Itens OK</div>
              <div className="text-lg font-bold text-emerald-700">
                {resumoConferenciaAtual.itens_ok}
              </div>
            </div>
            <div className="rounded-lg border border-white/70 bg-white/80 p-3">
              <div className="text-xs uppercase tracking-wide text-gray-500">Divergencias</div>
              <div className="text-lg font-bold text-orange-700">
                {resumoConferenciaAtual.itens_com_divergencia}
              </div>
            </div>
            <div className="rounded-lg border border-white/70 bg-white/80 p-3">
              <div className="text-xs uppercase tracking-wide text-gray-500">Qtd recebida</div>
              <div className="mt-1 text-[11px] text-gray-500">Entra no estoque</div>
              <div className="text-lg font-bold text-slate-800">
                {formatarValorFiscal(resumoConferenciaAtual.quantidade_total_conferida, 2)}
              </div>
            </div>
            <div className="rounded-lg border border-white/70 bg-white/80 p-3">
              <div className="text-xs uppercase tracking-wide text-gray-500">Falta + Avaria</div>
              <div className="text-lg font-bold text-rose-700">
                {formatarValorFiscal(
                  resumoConferenciaAtual.quantidade_total_faltante +
                    resumoConferenciaAtual.quantidade_total_avariada,
                  2,
                )}
              </div>
            </div>
          </div>

          <p className="max-w-3xl text-sm text-gray-700">
            {estaPendente
              ? "A conferencia nasce assumindo tudo certo. Se a carga estiver perfeita, basta clicar em Conferido. So mexa nos itens com falta ou avaria."
              : "Conferencia ja salva. Use as acoes de divergencia para gerar a tratativa sem precisar reverter a entrada."}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {estaPendente && (
            <>
              <ActionButton
                intent="neutral"
                onClick={() => setMostrarCamposConferencia((prev) => !prev)}
                size="md"
                tone="soft"
              >
                {mostrarCamposConferencia
                  ? "Ocultar ajuste manual"
                  : "Editar quantidades e avarias"}
              </ActionButton>
              <ActionButton
                disabled={salvandoOuDesfazendo}
                intent="create"
                onClick={() => salvarConferenciaAtual()}
                size="md"
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
              size="md"
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
                size="md"
                tone="soft"
              >
                {mostrarCamposConferencia ? "Ocultar tratativas" : "Abrir tratativas"}
              </ActionButton>
              <ActionButton
                disabled={salvandoOuDesfazendo}
                intent="edit"
                onClick={() => salvarConferenciaAtual()}
                size="md"
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
                size="md"
                tone="soft"
              >
                {criandoPendenciaFornecedor ? "Gerando..." : "Gerar pendencia fornecedor"}
              </ActionButton>
              <ActionButton
                disabled={gerandoRascunhoDevolucao || salvandoOuDesfazendo}
                intent="warning"
                onClick={gerarRascunhoDevolucao}
                size="md"
              >
                {gerandoRascunhoDevolucao ? "Gerando..." : "NF Devolucao das Divergencias"}
              </ActionButton>
            </>
          )}
        </div>
      </div>

      {mostrarCamposConferencia && (
        <div className="mt-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Observacao geral da conferencia
          </label>
          <textarea
            value={conferenciaObservacaoGeral}
            onChange={(event) => setConferenciaObservacaoGeral(event.target.value)}
            rows="2"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500"
            placeholder="Ex.: faltou 1 unidade do item X e 2 vieram avariadas."
          />
        </div>
      )}
    </div>
  );
}

export default EntradaXmlDetalhesConferenciaPanel;
