const estilosResumo = {
  blue: "border-blue-100 bg-blue-50 text-blue-900",
  emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
  amber: "border-amber-100 bg-amber-50 text-amber-900",
  rose: "border-rose-100 bg-rose-50 text-rose-900",
  violet: "border-violet-100 bg-violet-50 text-violet-900",
  slate: "border-slate-200 bg-slate-50 text-slate-900",
};

export default function ProdutosRelatorioResumoCard({
  titulo,
  valor,
  descricao,
  destaque = "blue",
}) {
  return (
    <div
      className={`rounded-2xl border p-5 shadow-sm ${estilosResumo[destaque] || estilosResumo.blue}`}
    >
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className="mt-2 text-2xl font-bold">{valor}</p>
      <p className="mt-2 text-xs opacity-75">{descricao}</p>
    </div>
  );
}
