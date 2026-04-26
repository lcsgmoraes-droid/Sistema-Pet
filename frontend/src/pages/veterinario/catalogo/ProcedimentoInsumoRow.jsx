export default function ProcedimentoInsumoRow({ atualizarInsumo, index, item, produtos, removerInsumo }) {
  return (
    <div className="grid gap-2 md:grid-cols-12">
      <select
        value={item.produto_id}
        onChange={(event) => atualizarInsumo(index, "produto_id", event.target.value)}
        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm md:col-span-7"
      >
        <option value="">Selecione um produto</option>
        {produtos.map((produto) => (
          <option key={produto.id} value={produto.id}>
            {produto.nome} - estoque {produto.estoque_atual} {produto.unidade || "UN"}
          </option>
        ))}
      </select>
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
