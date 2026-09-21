import { Boxes, Building2, Link2 } from "lucide-react";

export function PedidoCompraModoMontagem({
  filtroProdutosPedido,
  loadingProdutosPedido,
  modoMontagem,
  onChangeFiltro,
  onChangeModo,
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
        Como deseja montar o pedido?
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onChangeModo("fornecedor")}
          className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ${
            modoMontagem === "fornecedor"
              ? "bg-blue-600 text-white shadow-sm"
              : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-100"
          }`}
        >
          <Building2 className="h-4 w-4" />
          Por fornecedor
        </button>
        <button
          type="button"
          onClick={() => onChangeModo("produtos")}
          className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ${
            modoMontagem === "produtos"
              ? "bg-blue-600 text-white shadow-sm"
              : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-100"
          }`}
        >
          <Boxes className="h-4 w-4" />
          Por produtos
        </button>
      </div>
      {modoMontagem === "produtos" ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-600">
            Pesquise todo o catálogo. Sem pesquisa, mostramos sugestões de estoque baixo.
          </p>
          <div className="flex rounded-lg border border-slate-200 bg-white p-1">
            {[
              { value: "estoque_baixo", label: "Estoque baixo" },
              { value: "todos", label: "Todos" },
            ].map((opcao) => (
              <button
                key={opcao.value}
                type="button"
                onClick={() => onChangeFiltro(opcao.value)}
                className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
                  filtroProdutosPedido === opcao.value
                    ? "bg-amber-100 text-amber-800"
                    : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                {opcao.label}
              </button>
            ))}
          </div>
          {loadingProdutosPedido ? (
            <span className="text-xs font-medium text-blue-600">Buscando produtos...</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function PedidoCompraVinculoLote({
  fornecedorSelecionado,
  onVincular,
  selecionados,
  setVinculoComoPrincipal,
  vinculando,
  vinculoComoPrincipal,
}) {
  return (
    <div className="mt-3 flex flex-col gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="flex items-center gap-2 text-sm font-bold text-emerald-900">
          <Link2 className="h-4 w-4" /> Corrigir cadastro em lote
        </p>
        <p className="mt-1 text-xs text-emerald-800">
          {selecionados} produto{selecionados === 1 ? "" : "s"} selecionado
          {selecionados === 1 ? "" : "s"}. Escolha o fornecedor acima e vincule sem sair do pedido.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-xs font-semibold text-emerald-900">
          <input
            type="checkbox"
            checked={vinculoComoPrincipal}
            onChange={(event) => setVinculoComoPrincipal(event.target.checked)}
            className="h-4 w-4 rounded"
          />
          Definir como principal
        </label>
        <button
          type="button"
          onClick={onVincular}
          disabled={!fornecedorSelecionado || !selecionados || vinculando}
          className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {vinculando ? "Vinculando..." : "Vincular selecionados"}
        </button>
      </div>
    </div>
  );
}
