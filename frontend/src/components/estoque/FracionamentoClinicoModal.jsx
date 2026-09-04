import { ArrowRight, Loader2, Search, Syringe, X } from "lucide-react";

function ProdutoDestinoOption({ item, onSelecionar, selecionado }) {
  return (
    <button
      type="button"
      onClick={() => onSelecionar(item.id)}
      className={`w-full rounded-lg border p-3 text-left transition ${
        selecionado
          ? "border-violet-400 bg-violet-50 ring-1 ring-violet-300"
          : "border-slate-200 hover:border-violet-200 hover:bg-slate-50"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-900">{item.nome}</div>
          <div className="mt-1 text-xs text-slate-500">{item.codigo || "Sem codigo"}</div>
        </div>
        <div className="text-right text-xs text-slate-600">
          <div className="font-semibold">{item.unidade || "UN"}</div>
          <div>Saldo: {Number(item.estoque_atual || 0).toLocaleString("pt-BR")}</div>
        </div>
      </div>
    </button>
  );
}

export default function FracionamentoClinicoModal({ fluxo }) {
  const {
    busca,
    custoDestinoUnitario,
    documento,
    enviar,
    fatorConversao,
    fechar,
    formatMoney,
    formatarQuantidade,
    loading,
    loteOrigemId,
    lotes,
    observacao,
    onSelecionarProduto,
    produto,
    produtoDestino,
    produtoDestinoId,
    produtosDisponiveis,
    quantidadeDestino,
    quantidadeOrigem,
    setBusca,
    setDocumento,
    setFatorConversao,
    setLoteOrigemId,
    setObservacao,
    setQuantidadeOrigem,
    setValidadeDias,
    validadeDias,
  } = fluxo;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-3xl overflow-hidden rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-violet-100 p-2 text-violet-700">
              <Syringe size={20} aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">Destinar produto a clinica</h3>
              <p className="text-xs text-slate-500">
                Baixa a embalagem da loja e cria o saldo fracionado para uso veterinario.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={fechar}
            className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fechar"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={enviar} className="max-h-[82vh] space-y-5 overflow-y-auto p-6">
          <div className="grid items-center gap-3 rounded-xl border border-violet-200 bg-violet-50 p-4 sm:grid-cols-[1fr_auto_1fr]">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wide text-violet-600">
                Estoque da loja
              </div>
              <div className="mt-1 font-semibold text-slate-900">{produto?.nome}</div>
              <div className="text-xs text-slate-600">
                Saldo: {formatarQuantidade(produto?.estoque_atual)} {produto?.unidade || "UN"}
              </div>
            </div>
            <ArrowRight className="hidden text-violet-500 sm:block" aria-hidden="true" />
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wide text-violet-600">
                Estoque clinico
              </div>
              <div className="mt-1 font-semibold text-slate-900">
                {produtoDestino?.nome || "Selecione o insumo clinico"}
              </div>
              <div className="text-xs text-slate-600">
                Entrada prevista: {formatarQuantidade(quantidadeDestino)}{" "}
                {produtoDestino?.unidade || ""}
              </div>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-semibold text-slate-700">
              Produto que recebe o saldo clinico *
            </label>
            <div className="relative">
              <Search
                size={17}
                className="absolute left-3 top-2.5 text-slate-400"
                aria-hidden="true"
              />
              <input
                value={busca}
                onChange={(event) => setBusca(event.target.value)}
                className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
                placeholder="Buscar o SKU clinico, por exemplo Dipirona uso clinico"
              />
            </div>
            <div className="mt-2 max-h-44 space-y-2 overflow-y-auto pr-1">
              {produtosDisponiveis.map((item) => (
                <ProdutoDestinoOption
                  key={item.id}
                  item={item}
                  onSelecionar={onSelecionarProduto}
                  selecionado={String(item.id) === String(produtoDestinoId)}
                />
              ))}
              {!loading && produtosDisponiveis.length === 0 ? (
                <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">
                  Nenhum produto encontrado. Cadastre primeiro um produto simples em ML ou na
                  unidade clinica desejada.
                </p>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Embalagens abertas *
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={quantidadeOrigem}
                onChange={(event) => setQuantidadeOrigem(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Conteudo por embalagem *
              </label>
              <input
                type="number"
                min="0.0001"
                step="0.0001"
                value={fatorConversao}
                onChange={(event) => setFatorConversao(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Ex.: 20"
                required
              />
              <p className="mt-1 text-xs text-slate-500">
                Em {produtoDestino?.unidade || "unidade clinica"}
              </p>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Validade apos abrir
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={validadeDias}
                onChange={(event) => setValidadeDias(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Dias"
              />
            </div>
          </div>

          {lotes.length ? (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Lote da embalagem
              </label>
              <select
                value={loteOrigemId}
                onChange={(event) => setLoteOrigemId(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Automatico por validade/FIFO</option>
                {lotes.map((lote) => (
                  <option key={lote.id} value={lote.id}>
                    {lote.nome_lote} - saldo {formatarQuantidade(lote.quantidade_disponivel)}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Documento/referencia
              </label>
              <input
                value={documento}
                onChange={(event) => setDocumento(event.target.value)}
                maxLength={50}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Ex.: uso clinico / consulta"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Observacao</label>
              <input
                value={observacao}
                onChange={(event) => setObservacao(event.target.value)}
                maxLength={1000}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Opcional"
              />
            </div>
          </div>

          <div className="rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
            Serão criadas duas movimentações vinculadas: saída da loja e entrada na clínica. O
            vínculo e o fator ficam salvos para as próximas aberturas. Custo estimado por unidade
            clínica: <strong>{formatMoney(custoDestinoUnitario)}</strong>.
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={fechar}
              disabled={loading}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !produtoDestinoId || quantidadeDestino <= 0}
              className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : null}
              Confirmar e movimentar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
