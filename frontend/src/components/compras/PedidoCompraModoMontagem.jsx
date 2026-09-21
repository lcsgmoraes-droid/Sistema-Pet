import { Link2 } from "lucide-react";

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
