export default function ExameIAAlertas({ alertasIA }) {
  if (alertasIA.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="font-medium text-indigo-900">Alertas automaticos</p>
      <div className="flex flex-wrap gap-2">
        {alertasIA.map((alerta, index) => {
          const status = String(alerta.status || "atencao").toLowerCase();
          const classes =
            status === "alto" || status === "baixo"
              ? "border-red-200 bg-red-50 text-red-700"
              : "border-amber-200 bg-amber-50 text-amber-700";
          return (
            <span
              key={`${alerta.campo || "alerta"}_${index}`}
              className={`rounded-full border px-2 py-1 text-[11px] ${classes}`}
            >
              {alerta.mensagem || alerta.campo}
            </span>
          );
        })}
      </div>
    </div>
  );
}
