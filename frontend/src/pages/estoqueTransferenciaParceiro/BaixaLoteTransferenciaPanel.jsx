import { formatarMoeda } from "../../api/produtos";
import BaixaLoteAcertoDireto from "./BaixaLoteAcertoDireto";
import BaixaLoteTransferenciaLista from "./BaixaLoteTransferenciaLista";

function ResumoBaixaLoteCard({ titulo, valor, destaque = "text-slate-900" }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{titulo}</p>
      <p className={`mt-1 text-base font-bold ${destaque}`}>{formatarMoeda(valor)}</p>
    </div>
  );
}

function ContasPagarCompensacaoLote({
  contas,
  compensacoes,
  loading,
  onAtualizarValorCompensacao,
}) {
  if (loading) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-800">
        Carregando contas a pagar para compensacao...
      </div>
    );
  }

  if (!contas?.length) {
    return (
      <div className="rounded-xl border border-amber-200 bg-white px-4 py-4 text-sm text-amber-800">
        Essa pessoa nao possui contas a pagar em aberto para compensar.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {contas.map((conta) => {
        const origemEntrada = conta.origem_acerto === "entrada_parceiro";
        const classeOrigem = origemEntrada
          ? "border-blue-200 bg-blue-50 text-blue-700"
          : "border-slate-200 bg-slate-50 text-slate-600";
        return (
          <div
            key={conta.conta_pagar_id}
            className="grid gap-3 rounded-xl border border-amber-100 bg-white p-3 md:grid-cols-[1fr_140px_150px] md:items-center"
          >
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-slate-900">
                  {conta.documento || `Conta #${conta.conta_pagar_id}`}
                </p>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${classeOrigem}`}
                >
                  {conta.origem_label || "Financeiro"}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">{conta.descricao}</p>
            </div>
            <p className="text-sm font-semibold text-amber-700 md:text-right">
              {formatarMoeda(conta.saldo_aberto)}
            </p>
            <input
              type="number"
              min="0"
              step="0.01"
              value={compensacoes?.[conta.conta_pagar_id] || ""}
              onChange={(event) =>
                onAtualizarValorCompensacao(conta.conta_pagar_id, event.target.value)
              }
              className="rounded-lg border border-slate-300 px-3 py-2 text-right text-sm text-slate-900 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
            />
          </div>
        );
      })}
    </div>
  );
}

export default function BaixaLoteTransferenciaPanel({
  pessoaNome,
  form,
  setForm,
  preview,
  loadingPreview,
  salvando,
  formasPagamento,
  loadingFormasPagamento,
  aplicacoes,
  totalAplicado,
  totalCompensado,
  diferencaAplicacao,
  contasPagarCompensacao,
  loadingContasPagarCompensacao,
  onRecalcularPreview,
  onToggleAplicacao,
  onAtualizarValorAplicacao,
  onAtualizarValorCompensacao,
  onPreencherCompensacaoAutomatica,
  onLimparCompensacoesBaixa,
  onFechar,
  onConfirmar,
}) {
  return (
    <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-base font-semibold text-emerald-950">
            Registrar acerto / baixa por valor
          </h3>
          <p className="mt-1 text-sm text-emerald-800">
            {pessoaNome ? `Pessoa: ${pessoaNome}` : "Selecione uma pessoa nos filtros."}
          </p>
        </div>
        <button
          type="button"
          onClick={onFechar}
          className="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm font-medium text-emerald-800 transition hover:bg-emerald-100"
        >
          Fechar
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-emerald-900">
            Valor total
          </label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={form.valor_total}
            onChange={(event) => setForm((prev) => ({ ...prev, valor_total: event.target.value }))}
            className="w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-emerald-900">
            Data
          </label>
          <input
            type="date"
            value={form.data_recebimento}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, data_recebimento: event.target.value }))
            }
            className="w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-emerald-900">
            Ordem
          </label>
          <select
            value={form.ordem}
            onChange={(event) => setForm((prev) => ({ ...prev, ordem: event.target.value }))}
            className="w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
          >
            <option value="antiga">Mais antiga primeiro</option>
            <option value="nova">Mais nova primeiro</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-emerald-900">
            Tipo
          </label>
          <select
            value={form.modo_baixa}
            onChange={(event) => setForm((prev) => ({ ...prev, modo_baixa: event.target.value }))}
            className="w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
          >
            <option value="recebimento">Recebimento financeiro</option>
            <option value="acerto">Acerto / compensacao</option>
            <option value="produto_devolvido">Produto devolvido</option>
          </select>
        </div>
        <div className="flex items-end">
          <button
            type="button"
            onClick={onRecalcularPreview}
            disabled={loadingPreview}
            className="w-full rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-emerald-300"
          >
            {loadingPreview ? "Calculando..." : "Sugerir baixa"}
          </button>
        </div>
      </div>

      {form.modo_baixa === "recebimento" ? (
        <div className="mt-3">
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-emerald-900">
            Forma de pagamento
          </label>
          <select
            value={form.forma_pagamento_id}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, forma_pagamento_id: event.target.value }))
            }
            className="w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
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
        </div>
      ) : null}

      {form.modo_baixa === "produto_devolvido" ? (
        <label className="mt-3 flex items-center gap-2 text-sm font-medium text-emerald-900">
          <input
            type="checkbox"
            checked={Boolean(form.devolver_estoque)}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, devolver_estoque: event.target.checked }))
            }
            className="h-4 w-4 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500"
          />
          Voltar os produtos integrais selecionados para o estoque
        </label>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <ResumoBaixaLoteCard titulo="Aberto" valor={preview.total_aberto || 0} />
        <ResumoBaixaLoteCard titulo="Sugerido" valor={preview.total_sugerido || 0} />
        <ResumoBaixaLoteCard titulo="Aplicado" valor={totalAplicado} destaque="text-emerald-700" />
        <ResumoBaixaLoteCard
          titulo="Diferenca"
          valor={diferencaAplicacao}
          destaque="text-amber-700"
        />
      </div>

      <div className="mt-4">
        <BaixaLoteTransferenciaLista
          items={preview.items || []}
          aplicacoes={aplicacoes}
          onToggleAplicacao={onToggleAplicacao}
          onAtualizarValorAplicacao={onAtualizarValorAplicacao}
        />
      </div>

      {form.modo_baixa === "acerto" ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold text-amber-950">Contas a pagar para compensar</p>
              <p className="text-xs text-amber-800">
                Total compensado: {formatarMoeda(totalCompensado)}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={onPreencherCompensacaoAutomatica}
                className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs font-medium text-amber-800 transition hover:bg-amber-100"
              >
                Preencher automatico
              </button>
              <button
                type="button"
                onClick={onLimparCompensacoesBaixa}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
              >
                Limpar
              </button>
            </div>
          </div>
          <ContasPagarCompensacaoLote
            contas={contasPagarCompensacao}
            compensacoes={form.compensacoes}
            loading={loadingContasPagarCompensacao}
            onAtualizarValorCompensacao={onAtualizarValorCompensacao}
          />
          <BaixaLoteAcertoDireto
            form={form}
            setForm={setForm}
            totalAplicado={totalAplicado}
            totalCompensado={totalCompensado}
          />
        </div>
      ) : null}

      <div className="mt-4">
        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-emerald-900">
          Observacao
        </label>
        <textarea
          rows={3}
          value={form.observacao}
          onChange={(event) => setForm((prev) => ({ ...prev, observacao: event.target.value }))}
          className="w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
        />
      </div>

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          onClick={onFechar}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={onConfirmar}
          disabled={salvando}
          className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-emerald-300"
        >
          {salvando ? "Registrando..." : "Confirmar baixa por valor"}
        </button>
      </div>
    </section>
  );
}
