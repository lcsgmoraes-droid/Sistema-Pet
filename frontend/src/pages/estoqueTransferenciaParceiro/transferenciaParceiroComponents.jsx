export function StatusTransferenciaBadge({ status, label }) {
  const estilos = {
    pendente: "bg-amber-100 text-amber-800",
    parcial: "bg-sky-100 text-sky-800",
    pago: "bg-emerald-100 text-emerald-800",
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

export function ResumoTransferenciaCard({
  titulo,
  valor,
  descricao,
  destaque = "slate",
  onClick,
  selecionado = false,
}) {
  const estilos = {
    slate: "border-slate-200 bg-slate-50 text-slate-900",
    blue: "border-blue-100 bg-blue-50 text-blue-900",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-900",
    amber: "border-amber-100 bg-amber-50 text-amber-900",
  };

  const conteudo = (
    <>
      <p className="text-sm font-medium opacity-80">{titulo}</p>
      <p className="mt-2 text-2xl font-bold">{valor}</p>
      <p className="mt-2 text-xs opacity-75">{descricao}</p>
      {onClick ? <p className="mt-3 text-xs font-semibold">Ver no extrato →</p> : null}
    </>
  );

  const classes = `w-full rounded-2xl border p-5 text-left shadow-sm transition ${
    estilos[destaque] || estilos.slate
  } ${selecionado ? "ring-2 ring-blue-500 ring-offset-2" : ""}`;

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-pressed={selecionado}
        className={`${classes} hover:-translate-y-0.5 hover:shadow-md`}
      >
        {conteudo}
      </button>
    );
  }

  return <div className={classes}>{conteudo}</div>;
}
