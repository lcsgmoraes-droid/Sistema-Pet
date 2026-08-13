import { FiAlertCircle, FiBell, FiClock } from "react-icons/fi";

export default function LembretesHeader({ controller }) {
  const cards = [
    {
      icon: FiBell,
      label: "Total de lembretes",
      value: controller.lembretes.length,
      tone: "text-slate-600 dark:text-slate-300",
      iconTone: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    },
    {
      icon: FiClock,
      label: "Proximos em 7 dias",
      value: controller.proximosEmBreve.length,
      tone: "text-amber-700 dark:text-amber-300",
      iconTone: "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300",
    },
    {
      icon: FiAlertCircle,
      label: "Vencidos",
      value: controller.vencidos.length,
      tone: "text-red-700 dark:text-red-300",
      iconTone: "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300",
    },
  ];

  return (
    <header className="mb-5">
      <div className="mb-4">
        <p className="m-0 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
          Relacionamento
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100 sm:text-3xl">
          Lembretes de Recorrencia
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Acompanhe recompras previstas e oportunidades de contato com seus clientes.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {cards.map(({ icon: Icon, iconTone, label, tone, value }) => (
          <article
            key={label}
            className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <span
              className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${iconTone}`}
            >
              <Icon aria-hidden="true" />
            </span>
            <div>
              <p className={`m-0 text-2xl font-bold ${tone}`}>{value}</p>
              <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">{label}</p>
            </div>
          </article>
        ))}
      </div>
    </header>
  );
}
