import { formatarMoeda } from "../../api/produtos";
import { formatarData, normalizarNumero } from "./transferenciaParceiroUtils";

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
              <p className="mt-1 text-sm text-slate-700">{contaPagar.descricao}</p>
              <p className="mt-1 text-xs text-slate-500">
                Vencimento: {formatarData(contaPagar.data_vencimento)} | {contaPagar.status_label}
              </p>
            </div>
            <div className="text-sm text-slate-700">
              <p className="text-xs uppercase tracking-wide text-slate-500">Saldo</p>
              <p className="mt-1 font-semibold text-slate-900">
                {formatarMoeda(contaPagar.saldo_aberto)}
              </p>
            </div>
            <div className="text-sm text-slate-700">
              <p className="text-xs uppercase tracking-wide text-slate-500">Ja pago</p>
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
                  onAtualizarValorCompensacao(contaPagar.conta_pagar_id, event.target.value)
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

export default function HistoricoTransferenciaBaixaPanel({
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
            <label className="mb-2 block text-sm font-medium text-emerald-900">Tipo de baixa</label>
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
                <p className="text-sm font-semibold text-emerald-900">Recebimento normal</p>
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
                <p className="text-sm font-semibold text-amber-900">Acerto / compensacao</p>
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
                  setFormBaixa((prev) => ({ ...prev, forma_pagamento_id: event.target.value }))
                }
                className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
              >
                <option value="">
                  {loadingFormasPagamento ? "Carregando formas..." : "Sem forma especifica"}
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
                      Se preencher valores aqui, o sistema baixa a transferencia e tambem compensa
                      esses titulos no contas a pagar.
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
          <p className="mt-1 text-lg font-bold">{formatarMoeda(registro.saldo_aberto)}</p>
          <p className="mt-2 text-xs text-emerald-700">
            Pode ser baixa total ou parcial, conforme o valor informado.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-2 block text-sm font-medium text-emerald-900">Valor recebido</label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={formBaixa.valor_recebido}
            onChange={(event) =>
              setFormBaixa((prev) => ({ ...prev, valor_recebido: event.target.value }))
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
              setFormBaixa((prev) => ({ ...prev, data_recebimento: event.target.value }))
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
            setFormBaixa((prev) => ({ ...prev, observacao: event.target.value }))
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
