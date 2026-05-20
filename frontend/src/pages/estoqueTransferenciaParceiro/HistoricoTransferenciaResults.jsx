import { formatarMoeda } from "../../api/produtos";
import {
  formatarData,
  formatarQuantidade,
  normalizarNumero,
} from "./transferenciaParceiroUtils";
import { StatusTransferenciaBadge } from "./transferenciaParceiroComponents";

function ResumoValorRegistro({ titulo, valor, destaque }) {
  return (
    <div className="min-w-0 rounded-2xl bg-white px-4 py-3 text-right shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {titulo}
      </p>
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
                <p className="text-sm font-medium text-gray-900">
                  {item.produto_nome}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  Codigo: {item.codigo || "-"}
                </p>
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

function CompensacaoContasPagar({
  contasPagarCompensacao,
  formBaixa,
  loadingContasPagarCompensacao,
  onAtualizarValorCompensacao,
}) {
  if (loadingContasPagarCompensacao) {
    return (
      <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
        Carregando contas a pagar para compensacao...
      </div>
    );
  }

  if (contasPagarCompensacao.length === 0) {
    return (
      <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
        Essa pessoa nao possui contas a pagar em aberto para compensar no momento.
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-3">
      {contasPagarCompensacao.map((contaPagar) => (
        <div
          key={contaPagar.conta_pagar_id}
          className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
        >
          <div className="grid gap-3 xl:grid-cols-[1.6fr_0.8fr_0.8fr_0.9fr] xl:items-center">
            <div>
              <p className="text-sm font-semibold text-slate-900">
                {contaPagar.documento || `Conta #${contaPagar.conta_pagar_id}`}
              </p>
              <p className="mt-1 text-sm text-slate-700">
                {contaPagar.descricao}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Vencimento: {formatarData(contaPagar.data_vencimento)} |{" "}
                {contaPagar.status_label}
              </p>
            </div>
            <div className="text-sm text-slate-700">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Saldo
              </p>
              <p className="mt-1 font-semibold text-slate-900">
                {formatarMoeda(contaPagar.saldo_aberto)}
              </p>
            </div>
            <div className="text-sm text-slate-700">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Ja pago
              </p>
              <p className="mt-1 font-semibold text-slate-900">
                {formatarMoeda(contaPagar.valor_pago)}
              </p>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
                Valor a compensar
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={formBaixa.compensacoes?.[contaPagar.conta_pagar_id] || ""}
                onChange={(event) =>
                  onAtualizarValorCompensacao(
                    contaPagar.conta_pagar_id,
                    event.target.value,
                  )
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function BaixaTransferenciaPanel({
  registro,
  formBaixa,
  setFormBaixa,
  loadingFormasPagamento,
  formasPagamento,
  totalCompensadoBaixa,
  loadingContasPagarCompensacao,
  contasPagarCompensacao,
  contaRecebendo,
  onPreencherCompensacaoAutomatica,
  onLimparCompensacoesBaixa,
  onAtualizarValorCompensacao,
  onFecharBaixaTransferencia,
  onRegistrarBaixaTransferencia,
}) {
  const valorBaixa = normalizarNumero(formBaixa.valor_recebido) || 0;

  return (
    <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-emerald-900">
              Tipo de baixa
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              <button
                type="button"
                onClick={() =>
                  setFormBaixa((prev) => ({
                    ...prev,
                    modo_baixa: "recebimento",
                    compensacoes: {},
                  }))
                }
                className={`rounded-2xl border px-4 py-3 text-left transition ${
                  formBaixa.modo_baixa === "recebimento"
                    ? "border-emerald-500 bg-white shadow-sm"
                    : "border-emerald-200 bg-emerald-50 hover:bg-white"
                }`}
              >
                <p className="text-sm font-semibold text-emerald-900">
                  Recebimento normal
                </p>
                <p className="mt-1 text-xs text-emerald-800">
                  Usa o contas a receber e pode vincular uma forma de pagamento.
                </p>
              </button>
              <button
                type="button"
                onClick={() =>
                  setFormBaixa((prev) => ({
                    ...prev,
                    modo_baixa: "acerto",
                    forma_pagamento_id: "",
                    compensacoes: prev.compensacoes || {},
                  }))
                }
                className={`rounded-2xl border px-4 py-3 text-left transition ${
                  formBaixa.modo_baixa === "acerto"
                    ? "border-amber-500 bg-white shadow-sm"
                    : "border-amber-200 bg-amber-50 hover:bg-white"
                }`}
              >
                <p className="text-sm font-semibold text-amber-900">
                  Acerto / compensacao
                </p>
                <p className="mt-1 text-xs text-amber-800">
                  Ideal para o mata quando a pessoa tambem tem contas com voce.
                </p>
              </button>
            </div>
          </div>

          {formBaixa.modo_baixa === "recebimento" ? (
            <div>
              <label className="mb-2 block text-sm font-medium text-emerald-900">
                Forma de pagamento
              </label>
              <select
                value={formBaixa.forma_pagamento_id}
                onChange={(event) =>
                  setFormBaixa((prev) => ({
                    ...prev,
                    forma_pagamento_id: event.target.value,
                  }))
                }
                className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
              >
                <option value="">
                  {loadingFormasPagamento
                    ? "Carregando formas..."
                    : "Sem forma especifica"}
                </option>
                {formasPagamento.map((forma) => (
                  <option key={forma.id} value={forma.id}>
                    {forma.nome}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-emerald-800">
                Opcional. Se nao informar, a baixa fica sem forma vinculada.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                O sistema vai registrar esta baixa usando a forma de pagamento{" "}
                <span className="font-semibold">Acerto</span>.
              </div>

              <div className="rounded-2xl border border-amber-200 bg-white p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-amber-900">
                      Contas a pagar em aberto da mesma pessoa
                    </p>
                    <p className="mt-1 text-xs text-amber-800">
                      Se preencher valores aqui, o sistema baixa a transferencia e
                      tambem compensa esses titulos no contas a pagar.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={onPreencherCompensacaoAutomatica}
                      className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700 transition hover:bg-amber-100"
                    >
                      Preencher automatico
                    </button>
                    <button
                      type="button"
                      onClick={onLimparCompensacoesBaixa}
                      className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                    >
                      Limpar compensacoes
                    </button>
                  </div>
                </div>

                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Total compensado
                    </p>
                    <p className="mt-1 text-lg font-bold text-slate-900">
                      {formatarMoeda(totalCompensadoBaixa)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Valor da baixa
                    </p>
                    <p className="mt-1 text-lg font-bold text-slate-900">
                      {formatarMoeda(valorBaixa)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      Diferenca
                    </p>
                    <p className="mt-1 text-lg font-bold text-amber-700">
                      {formatarMoeda(Math.max(valorBaixa - totalCompensadoBaixa, 0))}
                    </p>
                  </div>
                </div>

                <CompensacaoContasPagar
                  contasPagarCompensacao={contasPagarCompensacao}
                  formBaixa={formBaixa}
                  loadingContasPagarCompensacao={loadingContasPagarCompensacao}
                  onAtualizarValorCompensacao={onAtualizarValorCompensacao}
                />
              </div>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm text-emerald-900">
          <p className="font-semibold">Saldo atual</p>
          <p className="mt-1 text-lg font-bold">
            {formatarMoeda(registro.saldo_aberto)}
          </p>
          <p className="mt-2 text-xs text-emerald-700">
            Pode ser baixa total ou parcial, conforme o valor informado.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-2 block text-sm font-medium text-emerald-900">
            Valor recebido
          </label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={formBaixa.valor_recebido}
            onChange={(event) =>
              setFormBaixa((prev) => ({
                ...prev,
                valor_recebido: event.target.value,
              }))
            }
            className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
          />
        </div>
        <div>
          <label className="mb-2 block text-sm font-medium text-emerald-900">
            Data do recebimento
          </label>
          <input
            type="date"
            value={formBaixa.data_recebimento}
            onChange={(event) =>
              setFormBaixa((prev) => ({
                ...prev,
                data_recebimento: event.target.value,
              }))
            }
            className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
          />
        </div>
      </div>

      <div className="mt-4">
        <label className="mb-2 block text-sm font-medium text-emerald-900">
          Observacao da baixa
        </label>
        <textarea
          rows={3}
          value={formBaixa.observacao}
          onChange={(event) =>
            setFormBaixa((prev) => ({
              ...prev,
              observacao: event.target.value,
            }))
          }
          placeholder="Opcional. Ex.: pix recebido hoje, acerto parcial da remessa."
          className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
        />
      </div>

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          onClick={onFecharBaixaTransferencia}
          className="rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={() => onRegistrarBaixaTransferencia(registro)}
          disabled={contaRecebendo === registro.conta_receber_id}
          className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
        >
          {contaRecebendo === registro.conta_receber_id
            ? "Registrando baixa..."
            : "Confirmar baixa"}
        </button>
      </div>
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
            <StatusTransferenciaBadge
              status={registro.status}
              label={registro.status_label}
            />
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
              {contaGerandoPdf === registro.conta_receber_id
                ? "Gerando PDF..."
                : "Gerar PDF"}
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
                contaEnviandoEmail === registro.conta_receber_id ||
                !registro.parceiro_email
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
              {contaExcluindo === registro.conta_receber_id
                ? "Excluindo..."
                : "Excluir lancamento"}
            </button>
          </div>

          {baixaAberta ? (
            <BaixaTransferenciaPanel
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
        <p className="text-base font-semibold text-gray-900">
          Nenhuma transferencia encontrada
        </p>
        <p className="mt-2 text-sm text-gray-500">
          Ajuste os filtros acima ou registre uma nova transferencia para comecar o historico.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 px-6 py-5">
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            PDF consolidado do acerto
          </p>
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
    </div>
  );
}
