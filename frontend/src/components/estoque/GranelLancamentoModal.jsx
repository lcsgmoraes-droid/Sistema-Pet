import { X } from "lucide-react";
import ActionButton from "../ui/ActionButton";

const formatarQuantidadePadrao = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor || 0));

const formatMoneyPadrao = (valor) =>
  Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

export default function GranelLancamentoModal({
  atualizarPrecoGranel,
  baseMargemGranel,
  baseMargemTexto,
  buscaGranel,
  custoKgGranel,
  diferencaPrecoGranel,
  formatMoney = formatMoneyPadrao,
  formatPercentual = formatarQuantidadePadrao,
  formatarQuantidade = formatarQuantidadePadrao,
  granelDentroMargemEsperada,
  granelProdutos = [],
  granelSelecionadoId,
  granelVinculos = [],
  handleAlterarModoPrecoGranel,
  handleDesvincularGranel,
  handleSelecionarGranel,
  kgGranelPrevisto,
  loadingGranel,
  margemBaseGranel,
  margemCalculadaGranel,
  margemGranel,
  modoPrecoGranel,
  nomeGranelSelecionado,
  observacaoGranel,
  onClose,
  onSubmit,
  precoMinimoEsperadoGranel,
  precoVendaAtualGranel,
  precoVendaGranel,
  precoVendaKgOrigem,
  precoVendaSugeridoGranel,
  produto,
  quantidadeGranel,
  quantidadeGranelNumero,
  setAtualizarPrecoGranel,
  setBuscaGranel,
  setMargemBaseGranel,
  setMargemGranel,
  setObservacaoGranel,
  setPrecoVendaGranel,
  setQuantidadeGranel,
  pesoPacoteOrigem,
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-xl overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Lancar granel</h3>
            <p className="mt-1 text-xs text-slate-500">
              {produto?.nome} | {formatarQuantidade(pesoPacoteOrigem)} kg por pacote
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fechar"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={onSubmit} className="max-h-[82vh] space-y-4 overflow-y-auto p-6">
          {granelVinculos.length > 0 && (
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Granel vinculado
              </label>
              <div className="space-y-2">
                {granelVinculos.map((vinculo) => (
                  <label
                    key={vinculo.id}
                    className={`flex cursor-pointer items-center justify-between gap-3 rounded-lg border p-3 text-sm ${
                      String(granelSelecionadoId) === String(vinculo.produto_granel_id)
                        ? "border-orange-300 bg-orange-50"
                        : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <input
                        type="radio"
                        name="granel_vinculado"
                        checked={String(granelSelecionadoId) === String(vinculo.produto_granel_id)}
                        onChange={() =>
                          handleSelecionarGranel(
                            vinculo.produto_granel_id,
                            vinculo.produto_granel_preco_venda,
                          )
                        }
                        className="text-orange-600 focus:ring-orange-500"
                      />
                      <span className="min-w-0">
                        <span className="block truncate font-semibold text-slate-900">
                          {vinculo.produto_granel_nome}
                        </span>
                        <span className="block text-xs text-slate-500">
                          Estoque granel: {formatarQuantidade(vinculo.produto_granel_estoque)} kg
                        </span>
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.preventDefault();
                        handleDesvincularGranel(vinculo.id);
                      }}
                      className="shrink-0 rounded border border-slate-200 px-2 py-1 text-xs text-slate-500 hover:border-red-200 hover:text-red-600"
                    >
                      Desvincular
                    </button>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Buscar outro produto granel
            </label>
            <input
              type="text"
              value={buscaGranel}
              onChange={(event) => setBuscaGranel(event.target.value)}
              placeholder="Ex: Special Dog Carne Granel"
              className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-orange-500"
            />
            <div className="mt-2 max-h-36 overflow-y-auto rounded-lg border border-slate-200">
              {granelProdutos.length === 0 ? (
                <div className="px-3 py-2 text-sm text-slate-500">
                  {loadingGranel ? "Buscando..." : "Nenhum granel encontrado"}
                </div>
              ) : (
                granelProdutos.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelecionarGranel(item.id, item.preco_venda)}
                    className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-orange-50 ${
                      String(granelSelecionadoId) === String(item.id)
                        ? "bg-orange-50 text-orange-800"
                        : "text-slate-700"
                    }`}
                  >
                    <span className="min-w-0 truncate">
                      <span className="font-semibold">{item.codigo}</span> - {item.nome}
                    </span>
                    <span className="ml-3 shrink-0 text-xs text-slate-500">
                      {formatarQuantidade(item.estoque_atual)} kg
                    </span>
                  </button>
                ))
              )}
            </div>
            {nomeGranelSelecionado && (
              <p className="mt-1 text-xs text-orange-700">
                Selecionado: {nomeGranelSelecionado}
              </p>
            )}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Pacotes abertos *
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={quantidadeGranel}
              onChange={(event) => setQuantidadeGranel(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-orange-500"
              required
            />
            <p className="mt-1 text-xs text-slate-500">
              Estoque atual da origem: {formatarQuantidade(produto?.estoque_atual)} pacote(s)
            </p>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded-md bg-white p-2">
                <div className="text-[11px] font-medium uppercase text-slate-500">Custo/kg origem</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">{formatMoney(custoKgGranel)}</div>
              </div>
              <div className="rounded-md bg-white p-2">
                <div className="text-[11px] font-medium uppercase text-slate-500">Venda/kg origem</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">{formatMoney(precoVendaKgOrigem)}</div>
              </div>
              <div className="rounded-md bg-white p-2">
                <div className="text-[11px] font-medium uppercase text-slate-500">Preco atual granel</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">{formatMoney(precoVendaAtualGranel)}</div>
              </div>
            </div>

            <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-slate-900">Preco de venda do granel</div>
                  <div className="text-xs text-slate-500">
                    Base: {baseMargemTexto} ({formatMoney(baseMargemGranel)})
                  </div>
                </div>
                <label className="flex items-center gap-2 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={atualizarPrecoGranel}
                    onChange={(event) => setAtualizarPrecoGranel(event.target.checked)}
                    className="rounded border-slate-300 text-orange-600 focus:ring-orange-500"
                  />
                  Atualizar ao lancar
                </label>
              </div>

              <label className="mt-3 flex items-start gap-2 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={margemBaseGranel === "preco_venda_kg"}
                  onChange={(event) =>
                    setMargemBaseGranel(event.target.checked ? "preco_venda_kg" : "custo_kg")
                  }
                  className="mt-0.5 rounded border-slate-300 text-orange-600 focus:ring-orange-500"
                />
                <span>
                  Calcular margem sobre venda/kg do pacote pai. Desmarcado usa o custo/kg.
                </span>
              </label>

              <div className="mt-3 grid grid-cols-2 rounded-lg border border-slate-200 bg-slate-100 p-1 text-xs">
                <button
                  type="button"
                  onClick={() => handleAlterarModoPrecoGranel("margem")}
                  className={`rounded-md px-2 py-1.5 font-medium transition-colors ${
                    modoPrecoGranel === "margem"
                      ? "bg-white text-orange-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Margem -&gt; preco
                </button>
                <button
                  type="button"
                  onClick={() => handleAlterarModoPrecoGranel("preco")}
                  className={`rounded-md px-2 py-1.5 font-medium transition-colors ${
                    modoPrecoGranel === "preco"
                      ? "bg-white text-orange-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Preco -&gt; margem
                </button>
              </div>

              {modoPrecoGranel === "margem" ? (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600">
                      Margem desejada (%)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={margemGranel}
                      onChange={(event) => setMargemGranel(event.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-orange-500"
                    />
                  </div>
                  <div className="rounded-lg bg-orange-50 p-3">
                    <div className="text-xs font-medium text-orange-700">Preco sugerido</div>
                    <div className="mt-1 text-lg font-semibold text-orange-900">
                      {formatMoney(precoVendaSugeridoGranel)}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600">
                      Preco de venda por kg
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={precoVendaGranel}
                      onChange={(event) => setPrecoVendaGranel(event.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-orange-500"
                    />
                  </div>
                  <div className="rounded-lg bg-blue-50 p-3">
                    <div className="text-xs font-medium text-blue-700">Margem calculada</div>
                    <div className="mt-1 text-lg font-semibold text-blue-900">
                      {formatPercentual(margemCalculadaGranel)}%
                    </div>
                  </div>
                </div>
              )}

              <div
                className={`mt-3 rounded-md border px-3 py-2 text-xs ${
                  granelDentroMargemEsperada
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                    : "border-amber-200 bg-amber-50 text-amber-700"
                }`}
              >
                {granelDentroMargemEsperada ? "Dentro da meta inicial" : "Abaixo da meta inicial"}:
                {" "}minimo {formatMoney(precoMinimoEsperadoGranel)} por kg (20% acima da venda/kg do pai).
                {precoVendaAtualGranel > 0 && precoVendaSugeridoGranel > 0 && (
                  <span className="ml-1 text-slate-600">
                    Diferenca vs atual: {diferencaPrecoGranel >= 0 ? "+" : "-"}
                    {formatMoney(Math.abs(diferencaPrecoGranel))}.
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900">
            <div className="font-semibold">Previsao do lancamento</div>
            <div className="mt-1 text-xs leading-5">
              Baixa {formatarQuantidade(quantidadeGranelNumero)} pacote(s) da origem e entra{" "}
              {formatarQuantidade(kgGranelPrevisto)} kg no granel. Custo estimado:{" "}
              {formatMoney(custoKgGranel)} por kg.
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Observacao
            </label>
            <textarea
              value={observacaoGranel}
              onChange={(event) => setObservacaoGranel(event.target.value)}
              rows={2}
              className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-orange-500"
              placeholder="Opcional"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <ActionButton
              className="flex-1 justify-center"
              intent="neutral"
              onClick={onClose}
              tone="soft"
              type="button"
            >
              Cancelar
            </ActionButton>
            <ActionButton
              className="flex-1 justify-center"
              disabled={loadingGranel}
              intent="warning"
              loading={loadingGranel}
              type="submit"
            >
              {loadingGranel ? "Lancando..." : "Lancar granel"}
            </ActionButton>
          </div>
        </form>
      </div>
    </div>
  );
}
