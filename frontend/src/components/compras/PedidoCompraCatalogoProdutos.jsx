import { useEffect, useState } from "react";
import { AlertTriangle, Check, Loader2, PackageSearch, Plus, Search } from "lucide-react";
import ProductIdentity from "../ui/ProductIdentity";
import CurrencyInput from "../CurrencyInput";
import { formatMoneyBRL } from "../../utils/formatters";
import { calcularQuantidadeReposicaoProduto } from "./pedidoCompraPorProdutosUtils";

function formatarQuantidade(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

function ProdutoCatalogoLinha({ itemPedido, onAdicionar, produto }) {
  const [quantidade, setQuantidade] = useState(
    String(itemPedido?.quantidade_pedida || calcularQuantidadeReposicaoProduto(produto)),
  );
  const [custoUnitario, setCustoUnitario] = useState(
    Number(itemPedido?.preco_unitario ?? produto.preco_custo ?? 0),
  );
  const estoqueAtual = Number(produto.estoque_atual || 0);
  const estoqueMinimo = Number(produto.estoque_minimo || 0);
  const semEstoque = estoqueAtual <= 0;

  useEffect(() => {
    if (!itemPedido) return;
    setQuantidade(String(itemPedido.quantidade_pedida || ""));
    setCustoUnitario(Number(itemPedido.preco_unitario ?? 0));
  }, [itemPedido]);

  return (
    <tr className={itemPedido ? "border-t border-emerald-100 bg-emerald-50/50" : "border-t"}>
      <td className="min-w-[300px] px-4 py-3">
        <ProductIdentity
          code={produto.codigo || produto.sku}
          name={produto.nome}
          nameClassName="font-semibold text-slate-900"
        />
        {itemPedido ? (
          <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800">
            <Check className="h-3 w-3" /> No pedido
          </span>
        ) : null}
      </td>
      <td className="px-4 py-3 text-right">
        <div className={`font-bold ${semEstoque ? "text-red-700" : "text-amber-700"}`}>
          {formatarQuantidade(estoqueAtual)}
        </div>
        <span
          className={`text-[11px] font-semibold ${semEstoque ? "text-red-600" : "text-amber-600"}`}
        >
          {semEstoque ? "Sem estoque" : "Estoque baixo"}
        </span>
      </td>
      <td className="px-4 py-3 text-right font-medium text-slate-600">
        {formatarQuantidade(estoqueMinimo)}
      </td>
      <td className="px-4 py-3 text-right text-sm font-semibold text-blue-700">
        {formatarQuantidade(calcularQuantidadeReposicaoProduto(produto))}
      </td>
      <td className="w-32 px-3 py-3">
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={quantidade}
          onChange={(event) => setQuantidade(event.target.value)}
          className="h-10 w-full rounded-lg border border-slate-300 px-3 text-right font-semibold focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          aria-label={`Quantidade para ${produto.nome}`}
        />
      </td>
      <td className="w-36 px-3 py-3">
        <CurrencyInput
          value={custoUnitario}
          onChange={setCustoUnitario}
          className="h-10 w-full rounded-lg border border-slate-300 px-3 text-right focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          aria-label={`Custo de ${produto.nome}`}
          title={`Custo atual: ${formatMoneyBRL(produto.preco_custo || 0)}`}
        />
      </td>
      <td className="w-32 px-4 py-3 text-right">
        <button
          type="button"
          onClick={() => onAdicionar(produto, quantidade, custoUnitario)}
          className={`inline-flex h-10 items-center justify-center gap-1.5 rounded-lg px-3 text-sm font-bold text-white transition ${
            itemPedido ? "bg-emerald-700 hover:bg-emerald-800" : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {itemPedido ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {itemPedido ? "Atualizar" : "Adicionar"}
        </button>
      </td>
    </tr>
  );
}

export default function PedidoCompraCatalogoProdutos({
  filtro,
  itensPedido,
  loading,
  onAdicionar,
  onChangeFiltro,
  onChangeTermo,
  produtos,
  termo,
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-blue-200 bg-white shadow-sm">
      <div className="border-b border-blue-100 bg-blue-50/70 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="flex items-center gap-2 font-bold text-slate-900">
              <PackageSearch className="h-5 w-5 text-blue-600" /> Produtos sugeridos
            </h3>
            <p className="mt-1 text-sm text-slate-600">
              A lista abaixo já mostra o estoque baixo. Digite uma quantidade e adicione ao pedido.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="relative block min-w-[300px]">
              <span className="sr-only">Pesquisar produtos</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={termo}
                onChange={(event) => onChangeTermo(event.target.value)}
                placeholder="Nome, SKU ou código de barras"
                className="h-11 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </label>
            <div className="flex rounded-lg border border-slate-200 bg-white p-1">
              {[
                { value: "estoque_baixo", label: "Estoque baixo" },
                { value: "todos", label: "Todos" },
              ].map((opcao) => (
                <button
                  key={opcao.value}
                  type="button"
                  onClick={() => onChangeFiltro(opcao.value)}
                  className={`whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-bold transition ${
                    filtro === opcao.value
                      ? "bg-amber-100 text-amber-900"
                      : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {opcao.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex min-h-48 items-center justify-center gap-2 text-sm font-semibold text-blue-700">
          <Loader2 className="h-5 w-5 animate-spin" /> Buscando produtos...
        </div>
      ) : produtos.length ? (
        <>
          <div className="max-h-[34rem] overflow-auto">
            <table className="w-full min-w-[1050px]">
              <thead className="sticky top-0 z-10 bg-slate-50 text-xs font-bold uppercase tracking-wide text-slate-500 shadow-sm">
                <tr>
                  <th className="px-4 py-3 text-left">Produto</th>
                  <th className="px-4 py-3 text-right">Estoque atual</th>
                  <th className="px-4 py-3 text-right">Mínimo</th>
                  <th className="px-4 py-3 text-right">Sugestão</th>
                  <th className="px-3 py-3 text-right">Qtd. a pedir</th>
                  <th className="px-3 py-3 text-right">Custo unitário</th>
                  <th className="px-4 py-3 text-right">Ação</th>
                </tr>
              </thead>
              <tbody>
                {produtos.map((produto) => (
                  <ProdutoCatalogoLinha
                    key={produto.id}
                    produto={produto}
                    itemPedido={itensPedido.find(
                      (item) => Number(item.produto_id) === Number(produto.id),
                    )}
                    onAdicionar={onAdicionar}
                  />
                ))}
              </tbody>
            </table>
          </div>
          <div className="border-t border-slate-100 bg-slate-50 px-4 py-2 text-xs text-slate-500">
            {produtos.length} produto{produtos.length === 1 ? "" : "s"} exibido
            {produtos.length === 1 ? "" : "s"}
            {termo.trim() ? " para esta pesquisa" : " nesta sugestão"}.
          </div>
        </>
      ) : (
        <div className="flex min-h-48 flex-col items-center justify-center px-6 py-10 text-center">
          <AlertTriangle className="mb-3 h-8 w-8 text-amber-500" />
          <p className="font-bold text-slate-800">
            {termo.trim()
              ? "Nenhum produto encontrado para esta pesquisa"
              : "Nenhum produto com estoque baixo encontrado"}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            {termo.trim()
              ? "Tente outro nome, SKU ou código de barras."
              : "Use a opção Todos para consultar o catálogo completo."}
          </p>
        </div>
      )}
    </section>
  );
}
