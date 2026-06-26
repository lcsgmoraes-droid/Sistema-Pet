import { X } from "lucide-react";
import ProductIdentity from "../../components/ui/ProductIdentity";
import { PERIODOS } from "./produtosRelatorioConstants";
import { formatarQuantidade } from "./produtosRelatorioFormatters";

export default function ProdutosRelatorioFiltros({
  periodoSelecionado,
  filtrosForm,
  produtoSelecionado,
  buscaProduto,
  sugestoesProdutos,
  dropdownAberto,
  loadingBuscaProduto,
  buscaRef,
  onSubmit,
  onPeriodoChange,
  onDataInicioChange,
  onDataFimChange,
  onFiltroChange,
  onBuscaProdutoChange,
  onBuscaProdutoFocus,
  onLimparBuscaProduto,
  onSelecionarProduto,
  onLimparProduto,
  onLimparFiltros,
}) {
  return (
    <form onSubmit={onSubmit} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap gap-2">
        {PERIODOS.map((periodo) => (
          <button
            key={periodo.value}
            type="button"
            onClick={() => onPeriodoChange(periodo)}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
              periodoSelecionado === periodo.value
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {periodo.label}
          </button>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Data inicio</label>
          <input
            type="date"
            value={filtrosForm.data_inicio}
            onChange={(event) => onDataInicioChange(event.target.value)}
            className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Data fim</label>
          <input
            type="date"
            value={filtrosForm.data_fim}
            onChange={(event) => onDataFimChange(event.target.value)}
            className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div className="relative md:col-span-2" ref={buscaRef}>
          <label className="mb-1 block text-sm font-medium text-gray-700">Produto</label>
          {produtoSelecionado ? (
            <div className="flex min-h-[46px] items-center gap-3 rounded-xl border border-blue-300 bg-blue-50 px-3 py-2">
              <div className="min-w-0 flex-1">
                <ProductIdentity
                  product={produtoSelecionado}
                  className="max-w-full"
                  nameClassName="text-sm font-semibold text-gray-900"
                  codeClassName="text-xs text-gray-600"
                />
              </div>
              <button
                type="button"
                onClick={onLimparProduto}
                className="rounded-lg px-2 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-50"
              >
                Limpar
              </button>
            </div>
          ) : (
            <div className="relative">
              <input
                type="text"
                value={buscaProduto}
                onChange={(event) => onBuscaProdutoChange(event.target.value)}
                onFocus={onBuscaProdutoFocus}
                placeholder="Buscar por nome, codigo, SKU ou codigo de barras"
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 pr-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
              {buscaProduto && (
                <button
                  type="button"
                  onClick={onLimparBuscaProduto}
                  aria-label="Limpar busca de produto"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 transition-colors hover:text-red-500"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
              {dropdownAberto && (buscaProduto.trim().length >= 2 || loadingBuscaProduto) && (
                <div className="absolute left-0 right-0 top-full z-20 mt-2 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-xl">
                  {loadingBuscaProduto ? (
                    <div className="px-4 py-3 text-sm text-gray-500">Buscando produtos...</div>
                  ) : sugestoesProdutos.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-gray-500">
                      Nenhum produto encontrado para esse termo.
                    </div>
                  ) : (
                    sugestoesProdutos.map((produto) => (
                      <button
                        key={produto.id}
                        type="button"
                        onMouseDown={() => onSelecionarProduto(produto)}
                        className="flex w-full items-start justify-between gap-3 border-b border-gray-100 px-4 py-3 text-left transition-colors hover:bg-blue-50 last:border-b-0"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-gray-900">
                            {produto.nome}
                          </p>
                          <p className="truncate text-xs text-gray-500">
                            {[produto.codigo, produto.sku, produto.codigo_barras]
                              .filter(Boolean)
                              .join(" | ")}
                          </p>
                        </div>
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-700">
                          Estoque {formatarQuantidade(produto.estoque_atual)}
                        </span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Tipo da movimentacao
          </label>
          <select
            value={filtrosForm.tipo_movimentacao}
            onChange={(event) => onFiltroChange("tipo_movimentacao", event.target.value)}
            className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            <option value="">Todos os tipos</option>
            <option value="entrada">Entrada</option>
            <option value="saida">Saida</option>
            <option value="transferencia">Transferencia</option>
          </select>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-gray-700">Itens por pagina</label>
          <select
            value={filtrosForm.page_size}
            onChange={(event) => onFiltroChange("page_size", Number(event.target.value))}
            className="rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          >
            {[20, 50, 100].map((opcao) => (
              <option key={opcao} value={opcao}>
                {opcao}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onLimparFiltros}
            className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            Limpar filtros
          </button>
          <button
            type="submit"
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Atualizar painel
          </button>
        </div>
      </div>
    </form>
  );
}
