export default function ResumoCard({ alerta = false, label, subtitle, value }) {
  return (
    <div
      className={[
        "rounded-xl border bg-white p-4",
        alerta ? "border-red-200" : "border-slate-200",
      ].join(" ")}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p
        className={["mt-1 text-lg font-semibold", alerta ? "text-red-600" : "text-slate-950"].join(
          " ",
        )}
      >
        {value}
      </p>
      {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}
