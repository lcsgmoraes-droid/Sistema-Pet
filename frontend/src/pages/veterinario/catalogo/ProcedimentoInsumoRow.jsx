import BuscaProduto from "../../../components/v2/BuscaProduto/BuscaProduto";
import useBuscaEntidadeLocal from "../../../components/v2/BuscaEntidade/useBuscaEntidadeLocal";
export default function ProcedimentoInsumoRow({
  atualizarInsumo,
  index,
  item,
  produtos,
  removerInsumo,
}) {
  const buscaProduto = useBuscaEntidadeLocal({
    itens: produtos,
    valueId: item.produto_id,
    onChangeId: (valor) => atualizarInsumo(index, "produto_id", valor),
    tipo: "produto",
  });
  return (
    <div className="grid gap-2 md:grid-cols-12">
      <BuscaProduto
        {...buscaProduto}
        className="md:col-span-7"
        placeholder="Código ou nome do insumo"
        renderSuggestionContent={(produto) => (
          <>
            <span className="block font-medium">
              {produto.codigo || "Sem código"} - {produto.nome}
            </span>
            <span className="text-xs text-slate-500">
              Estoque: {produto.estoque_atual} {produto.unidade || "UN"}
            </span>
          </>
        )}
      />
      <input
        type="number"
        min="0"
        step="0.01"
        value={item.quantidade}
        onChange={(event) => atualizarInsumo(index, "quantidade", event.target.value)}
        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm md:col-span-2"
        placeholder="Qtd."
      />
      <label className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs md:col-span-2">
        <input
          type="checkbox"
          checked={item.baixar_estoque !== false}
          onChange={(event) => atualizarInsumo(index, "baixar_estoque", event.target.checked)}
        />
        Baixar
      </label>
      <button
        type="button"
        onClick={() => removerInsumo(index)}
        className="rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50 md:col-span-1"
      >
        X
      </button>
    </div>
  );
}
