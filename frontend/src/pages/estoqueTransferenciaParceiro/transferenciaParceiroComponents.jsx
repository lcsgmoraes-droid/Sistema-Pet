export function StatusTransferenciaBadge({ status, label }) {
  const estilos = {
    pendente: "bg-amber-100 text-amber-800",
    parcial: "bg-sky-100 text-sky-800",
    recebido: "bg-emerald-100 text-emerald-800",
    vencido: "bg-rose-100 text-rose-800",
    cancelado: "bg-slate-200 text-slate-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${estilos[status] || estilos.pendente}`}
    >
      {label || status}
    </span>
  );
}

export function ResumoTransferenciaCard({ titulo, valor, descricao, destaque = "slate" }) {
  const estilos = {
    slate: "border-slate-200 bg-slate-50 text-slate-900",
    blue: "border-blue-100 bg-blue-50 text-blue-900",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
    amber: "border-amber-100 bg-amber-50 text-amber-900",
  };

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${estilos[destaque] || estilos.slate}`}>
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className="mt-2 text-2xl font-bold">{valor}</p>
      <p className="mt-2 text-xs opacity-75">{descricao}</p>
    </div>
  );
}
