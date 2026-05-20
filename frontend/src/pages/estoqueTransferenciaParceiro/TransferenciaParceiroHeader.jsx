export default function TransferenciaParceiroHeader({
  modoEdicao,
  transferenciaEditando,
  onCancelarEdicao,
  abaAtiva,
  onChangeAba,
  totalRegistrosHistorico,
}) {
  return (
    <>
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Transferencia com Ressarcimento
          </h1>
          <p className="mt-2 max-w-4xl text-sm text-gray-600">
            Use esta tela para baixar estoque pelo custo quando qualquer pessoa
            ou parceiro levar produtos. O sistema nao cria venda no PDV e gera
            um contas a receber separado para o ressarcimento, com baixa por
            recebimento normal ou acerto.
          </p>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Nao entra em faturamento de vendas. Sai do estoque e fica pendente no
          financeiro da pessoa responsavel pelo ressarcimento ate voce baixar.
        </div>
      </div>

      {modoEdicao ? (
        <div className="flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-semibold">
              Editando{" "}
              {transferenciaEditando.documento ||
                `transferencia #${transferenciaEditando.conta_receber_id}`}
            </p>
            <p className="mt-1">
              Ao salvar, o sistema recalcula estoque e financeiro deste lancamento.
            </p>
          </div>
          <button
            type="button"
            onClick={onCancelarEdicao}
            className="rounded-xl border border-amber-300 bg-white px-4 py-2 text-sm font-semibold text-amber-800 transition hover:bg-amber-100"
          >
            Cancelar edicao
          </button>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2 border-b border-gray-200">
        <button
          type="button"
          onClick={() => onChangeAba("lancamento")}
          className={`border-b-2 px-4 py-3 text-sm font-semibold transition ${
            abaAtiva === "lancamento"
              ? "border-blue-600 text-blue-700"
              : "border-transparent text-gray-600 hover:text-gray-900"
          }`}
        >
          Novo lancamento
        </button>
        <button
          type="button"
          onClick={() => onChangeAba("historico")}
          className={`border-b-2 px-4 py-3 text-sm font-semibold transition ${
            abaAtiva === "historico"
              ? "border-blue-600 text-blue-700"
              : "border-transparent text-gray-600 hover:text-gray-900"
          }`}
        >
          Consultar historico
          {totalRegistrosHistorico ? (
            <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
              {totalRegistrosHistorico}
            </span>
          ) : null}
        </button>
      </div>
    </>
  );
}
