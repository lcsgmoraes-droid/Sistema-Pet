import { Boxes, Building2, ClipboardList } from "lucide-react";

const ABAS = [
  {
    value: "fornecedor",
    label: "Por fornecedor",
    descricao: "Pedido tradicional e sugestão inteligente",
    icon: Building2,
  },
  {
    value: "produtos",
    label: "Por produtos",
    descricao: "Estoque baixo e pesquisa do catálogo",
    icon: Boxes,
  },
  {
    value: "pedidos",
    label: "Pedidos realizados",
    descricao: "Consulte, envie e acompanhe pedidos",
    icon: ClipboardList,
  },
];

export default function PedidosCompraTabs({ abaAtiva, itensNoPedido, onChange, totalPedidos }) {
  return (
    <div
      className="mb-6 grid gap-2 rounded-2xl border border-slate-200 bg-slate-100 p-2 shadow-sm md:grid-cols-3"
      role="tablist"
      aria-label="Áreas de pedidos de compra"
    >
      {ABAS.map((aba) => {
        const Icon = aba.icon;
        const ativa = abaAtiva === aba.value;
        const contador =
          aba.value === "produtos" && itensNoPedido > 0
            ? itensNoPedido
            : aba.value === "pedidos" && totalPedidos > 0
              ? totalPedidos
              : null;

        return (
          <button
            key={aba.value}
            type="button"
            role="tab"
            aria-selected={ativa}
            onClick={() => onChange(aba.value)}
            className={`flex min-h-20 items-center gap-3 rounded-xl border px-4 py-3 text-left transition ${
              ativa
                ? "border-blue-200 bg-white text-blue-800 shadow-sm"
                : "border-transparent text-slate-600 hover:bg-white/70 hover:text-slate-900"
            }`}
          >
            <span
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                ativa ? "bg-blue-100 text-blue-700" : "bg-slate-200 text-slate-600"
              }`}
            >
              <Icon className="h-5 w-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-2 font-bold">
                {aba.label}
                {contador ? (
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                    {contador}
                  </span>
                ) : null}
              </span>
              <span className="mt-0.5 block text-xs font-medium text-slate-500">
                {aba.descricao}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
