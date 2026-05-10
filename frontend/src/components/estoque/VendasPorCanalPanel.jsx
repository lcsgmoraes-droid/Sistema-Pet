import { ShoppingCart } from "lucide-react";

export default function VendasPorCanalPanel({
  estilosCanais = {},
  formatMoney,
  formatQuantidade,
  labelsCanais = {},
  vendasPorCanal = [],
}) {
  if (vendasPorCanal.length === 0) {
    return null;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-slate-100 px-6 py-4">
        <ShoppingCart className="h-5 w-5 text-indigo-500" aria-hidden="true" />
        <h2 className="text-base font-bold text-slate-800">Vendas por Canal</h2>
        <span className="ml-auto text-xs text-slate-400">
          Saidas vinculadas a vendas e NFs confirmadas
        </span>
      </div>

      <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {vendasPorCanal.map(({ canal, qtd, valor, count, pct }) => {
          const labelCanal = labelsCanais[canal] || canal;
          const corCanal = estilosCanais[canal]?.card || "bg-slate-50 border-slate-200 text-slate-700";
          const barColor = estilosCanais[canal]?.bar || "bg-slate-400";

          return (
            <div key={canal} className={`rounded-xl border p-4 ${corCanal}`}>
              <div className="text-xs font-bold uppercase tracking-wide opacity-70">{labelCanal}</div>
              <div className="mt-2 flex items-end justify-between gap-2">
                <div>
                  <div className="text-2xl font-black">{formatQuantidade(qtd)} un</div>
                  <div className="mt-0.5 text-xs font-semibold opacity-80">
                    {valor > 0 ? formatMoney(valor) : "Sem vendas no historico"}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold">{pct.toFixed(0)}%</div>
                  <div className="text-[11px] opacity-60">
                    {count} venda{count !== 1 ? "s" : ""}
                  </div>
                </div>
              </div>
              <div className="mt-3 h-1.5 rounded-full bg-black/10">
                <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
