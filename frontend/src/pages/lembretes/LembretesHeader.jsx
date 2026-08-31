import { FiAlertCircle, FiBell, FiClock, FiMessageCircle } from "react-icons/fi";

export default function LembretesHeader({ controller }) {
  const contacted = controller.lembretes.filter((item) => item.contatos_total > 0).length;
  const cards = [
    {
      icon: FiBell,
      label: "Oportunidades ativas",
      value: controller.lembretes.length,
      iconTone: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    },
    {
      icon: FiAlertCircle,
      label: "Atrasadas",
      value: controller.vencidos.length,
      iconTone: "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300",
    },
    {
      icon: FiClock,
      label: "Hoje até 7 dias",
      value: controller.proximosEmBreve.length,
      iconTone: "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300",
    },
    {
      icon: FiMessageCircle,
      label: "Já contatadas",
      value: contacted,
      iconTone: "bg-teal-50 text-teal-700 dark:bg-teal-500/10 dark:text-teal-300",
    },
  ];

  return (
    <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(({ icon: Icon, iconTone, label, value }) => (
        <article
          className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm dark:border-slate-700 dark:bg-slate-900"
          key={label}
        >
          <span
            className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${iconTone}`}
          >
            <Icon aria-hidden="true" />
          </span>
          <div>
            <p className="m-0 text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
            <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">{label}</p>
          </div>
        </article>
      ))}
    </section>
  );
}
