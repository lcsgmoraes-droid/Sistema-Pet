import { formatarMoeda } from "../../api/produtos";
import { formatarData, formatarQuantidade } from "./transferenciaParceiroUtils";
import HistoricoTransferenciaBaixaPanel from "./HistoricoTransferenciaBaixaPanel";
import { StatusTransferenciaBadge } from "./transferenciaParceiroComponents";

function ResumoValorRegistro({ titulo, valor, destaque }) {
  return (
    <div className="min-w-0 rounded-2xl bg-white px-4 py-3 text-right shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{titulo}</p>
      <p
        className={`mt-1 break-words text-sm font-semibold md:text-base ${
          destaque || "text-gray-900"
        }`}
      >
        {formatarMoeda(valor)}
      </p>
    </div>
  );
}

function ItensTransferenciaTable({ registro }) {
  return (
    <div className="mt-4 overflow-x-auto rounded-2xl bg-white">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-slate-100">
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
            <th className="px-4 py-3">Item</th>
            <th className="px-4 py-3 text-right">Qtd</th>
            <th className="px-4 py-3 text-right">Custo</th>
            <th className="px-4 py-3 text-right">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {(registro.itens || []).map((item, index) => (
            <tr key={`${registro.conta_receber_id}-${item.produto_id}-${index}`}>
              <td className="px-4 py-3">
                <p className="text-sm font-medium text-gray-900">{item.produto_nome}</p>
                <p className="mt-1 text-xs text-gray-500">Codigo: {item.codigo || "-"}</p>
              </td>
              <td className="px-4 py-3 text-right text-sm text-gray-700">
                {formatarQuantidade(item.quantidade)}
              </td>
              <td className="px-4 py-3 text-right text-sm text-gray-700">
                {formatarMoeda(item.custo_unitario)}
              </td>
              <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">
                {formatarMoeda(item.valor_total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistoricoTransferenciaCard({
  registro,
  expandido,
  selecionado,
  baixaAberta,
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
  onAlternarSelecao,
  onAlternarExpansao,
  onAbrirBaixaTransferencia,
  onIniciarEdicaoTransferencia,
  onAbrirModalDocumentoTransferencia,
  onExcluirTransferencia,
  onPreencherCompensacaoAutomatica,
  onLimparCompensacoesBaixa,
  onAtualizarValorCompensacao,
  onFecharBaixaTransferencia,
  onRegistrarBaixaTransferencia,
}) {
  const totalItensRegistro = registro.itens?.length || 0;
  const bloqueiaAlteracao =
    Number(registro.valor_recebido || 0) > 0 ||
    registro.status === "recebido" ||
    registro.status === "cancelado";

  return (
    <article className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
              <input
                type="checkbox"
                checked={selecionado}
                onChange={() => onAlternarSelecao(registro.conta_receber_id)}
                className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
              />
              Selecionar
            </label>
            <h3 className="text-base font-semibold text-gray-900">
              {registro.documento || `Transferencia #${registro.conta_receber_id}`}
            </h3>
            <StatusTransferenciaBadge status={registro.status} label={registro.status_label} />
          </div>
          <p className="text-sm text-gray-700">
            {registro.parceiro_nome}
            {registro.parceiro_codigo ? ` | Codigo ${registro.parceiro_codigo}` : ""}
          </p>
          {registro.parceiro_email ? (
            <p className="text-xs text-gray-500">{registro.parceiro_email}</p>
          ) : null}
          <p className="text-xs text-gray-500">
            Emissao: {formatarData(registro.data_emissao)} | Vencimento:{" "}
            {formatarData(registro.data_vencimento)} | Recebimento:{" "}
            {formatarData(registro.data_recebimento)}
          </p>
          {registro.modo_baixa_label || registro.forma_pagamento_nome ? (
            <div className="flex flex-wrap gap-2">
              {registro.modo_baixa_label ? (
                <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                  {registro.modo_baixa_label}
                </span>
              ) : null}
              {registro.forma_pagamento_nome ? (
                <span className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                  Forma: {registro.forma_pagamento_nome}
                </span>
              ) : null}
            </div>
          ) : null}
          {expandido && registro.observacoes ? (
            <p className="text-xs text-gray-500">{registro.observacoes}</p>
          ) : null}
        </div>

        <div className="min-w-0 space-y-3 xl:min-w-[460px]">
          <div className="grid min-w-0 gap-3 sm:grid-cols-3">
            <ResumoValorRegistro titulo="Valor" valor={registro.valor_original} />
            <ResumoValorRegistro
              titulo="Recebido"
              valor={registro.valor_recebido}
              destaque="text-emerald-700"
            />
            <ResumoValorRegistro
              titulo="Saldo"
              valor={registro.saldo_aberto}
              destaque="text-amber-700"
            />
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => onAlternarExpansao(registro.conta_receber_id)}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
            >
              {expandido ? "Fechar detalhes" : `Ver detalhes (${totalItensRegistro} item(ns))`}
            </button>
          </div>
        </div>
      </div>

      {expandido ? (
        <>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            {registro.status !== "recebido" && registro.status !== "cancelado" ? (
              <button
                type="button"
                onClick={() => void onAbrirBaixaTransferencia(registro)}
                className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100"
              >
                Dar baixa
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => onIniciarEdicaoTransferencia(registro)}
              disabled={bloqueiaAlteracao}
              className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700 transition-colors hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Editar lancamento
            </button>
            <button
              type="button"
              onClick={() => onAbrirModalDocumentoTransferencia(registro, "pdf")}
              disabled={contaGerandoPdf === registro.conta_receber_id}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {contaGerandoPdf === registro.conta_receber_id ? "Gerando PDF..." : "Gerar PDF"}
            </button>
            <button
              type="button"
              onClick={() => onAbrirModalDocumentoTransferencia(registro, "cupom")}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              Imprimir cupom
            </button>
            <button
              type="button"
              onClick={() => onAbrirModalDocumentoTransferencia(registro, "email")}
              disabled={
                contaEnviandoEmail === registro.conta_receber_id || !registro.parceiro_email
              }
              className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {contaEnviandoEmail === registro.conta_receber_id
                ? "Enviando e-mail..."
                : registro.parceiro_email
                  ? "Enviar por e-mail"
                  : "Sem e-mail cadastrado"}
            </button>
            <button
              type="button"
              onClick={() => void onExcluirTransferencia(registro)}
              disabled={
                contaExcluindo === registro.conta_receber_id ||
                Number(registro.valor_recebido || 0) > 0
              }
              className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {contaExcluindo === registro.conta_receber_id ? "Excluindo..." : "Excluir lancamento"}
            </button>
          </div>

          {baixaAberta ? (
            <HistoricoTransferenciaBaixaPanel
              registro={registro}
              formBaixa={formBaixa}
              setFormBaixa={setFormBaixa}
              loadingFormasPagamento={loadingFormasPagamento}
              formasPagamento={formasPagamento}
              totalCompensadoBaixa={totalCompensadoBaixa}
              loadingContasPagarCompensacao={loadingContasPagarCompensacao}
              contasPagarCompensacao={contasPagarCompensacao}
              contaRecebendo={contaRecebendo}
              onPreencherCompensacaoAutomatica={onPreencherCompensacaoAutomatica}
              onLimparCompensacoesBaixa={onLimparCompensacoesBaixa}
              onAtualizarValorCompensacao={onAtualizarValorCompensacao}
              onFecharBaixaTransferencia={onFecharBaixaTransferencia}
              onRegistrarBaixaTransferencia={onRegistrarBaixaTransferencia}
            />
          ) : null}

          <ItensTransferenciaTable registro={registro} />
        </>
      ) : null}
    </article>
  );
}

export default function HistoricoTransferenciaLista({
  historico,
  selecionadosHistorico,
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
  loadingHistorico,
  onAlternarSelecaoHistorico,
  onAlternarExpansaoHistorico,
  onAbrirBaixaTransferencia,
  onIniciarEdicaoTransferencia,
  onAbrirModalDocumentoTransferencia,
  onExcluirTransferencia,
  onPreencherCompensacaoAutomatica,
  onLimparCompensacoesBaixa,
  onAtualizarValorCompensacao,
  onFecharBaixaTransferencia,
  onRegistrarBaixaTransferencia,
  onSetPaginaHistorico,
}) {
  return (
    <>
      {historico.items.map((registro) => (
        <HistoricoTransferenciaCard
          key={registro.conta_receber_id}
          registro={registro}
          expandido={historicoExpandidoIds.includes(registro.conta_receber_id)}
          selecionado={selecionadosHistorico.includes(registro.conta_receber_id)}
          baixaAberta={baixaAbertaId === registro.conta_receber_id}
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
          onAlternarSelecao={onAlternarSelecaoHistorico}
          onAlternarExpansao={onAlternarExpansaoHistorico}
          onAbrirBaixaTransferencia={onAbrirBaixaTransferencia}
          onIniciarEdicaoTransferencia={onIniciarEdicaoTransferencia}
          onAbrirModalDocumentoTransferencia={onAbrirModalDocumentoTransferencia}
          onExcluirTransferencia={onExcluirTransferencia}
          onPreencherCompensacaoAutomatica={onPreencherCompensacaoAutomatica}
          onLimparCompensacoesBaixa={onLimparCompensacoesBaixa}
          onAtualizarValorCompensacao={onAtualizarValorCompensacao}
          onFecharBaixaTransferencia={onFecharBaixaTransferencia}
          onRegistrarBaixaTransferencia={onRegistrarBaixaTransferencia}
        />
      ))}

      {totalPaginasHistorico > 1 ? (
        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onSetPaginaHistorico((prev) => Math.max(prev - 1, 1))}
            disabled={paginaHistorico <= 1 || loadingHistorico}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-600">
            Pagina {historico.page || 1} de {totalPaginasHistorico}
          </span>
          <button
            type="button"
            onClick={() =>
              onSetPaginaHistorico((prev) => Math.min(prev + 1, totalPaginasHistorico))
            }
            disabled={paginaHistorico >= totalPaginasHistorico || loadingHistorico}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Proxima
          </button>
        </div>
      ) : null}
    </>
  );
}
