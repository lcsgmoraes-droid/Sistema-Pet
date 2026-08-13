import { FiAlertCircle, FiBell, FiCalendar, FiClock } from "react-icons/fi";
import LembreteCard from "./LembreteCard";

export default function LembretesList({ controller }) {
  if (controller.loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-600 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
        Carregando lembretes...
      </div>
    );
  }

  if (controller.semPendencias) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-5 py-12 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-500/10 dark:text-teal-300">
          <FiBell size={22} aria-hidden="true" />
        </span>
        <h2 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
          Nenhum lembrete pendente
        </h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Lembretes serao criados automaticamente para produtos recorrentes.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-5">
      <LembretesSection
        icon={FiAlertCircle}
        lembretes={controller.vencidos}
        tone="danger"
        title="Vencidos"
        controller={controller}
      />
      <LembretesSection
        icon={FiClock}
        lembretes={controller.proximosEmBreve}
        tone="warning"
        title="Proximos em ate 7 dias"
        controller={controller}
      />
      <LembretesSection
        icon={FiCalendar}
        lembretes={controller.futuros}
        tone="neutral"
        title="Proximos (mais de 7 dias)"
        controller={controller}
      />
    </div>
  );
}

const TONES = {
  danger: {
    icon: "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300",
    count:
      "bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-300 dark:ring-red-500/30",
  },
  neutral: {
    icon: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    count:
      "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
  },
  warning: {
    icon: "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300",
    count:
      "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30",
  },
};

function LembretesSection({ controller, icon: Icon, lembretes, title, tone }) {
  if (lembretes.length === 0) return null;
  const styles = TONES[tone] || TONES.neutral;

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3.5 dark:border-slate-800 sm:px-5">
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex h-9 w-9 items-center justify-center rounded-xl ${styles.icon}`}
          >
            <Icon aria-hidden="true" />
          </span>
          <h2 className="m-0 text-base font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </h2>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset ${styles.count}`}
        >
          {lembretes.length} {lembretes.length === 1 ? "item" : "itens"}
        </span>
      </header>
      <div className="grid gap-3 p-4 sm:p-5">
        {lembretes.map((lembrete) => (
          <LembreteCard
            key={lembrete.id}
            lembrete={lembrete}
            onCancelar={controller.cancelarLembrete}
            onCompletar={controller.completarLembrete}
            onRenovar={controller.renovarLembrete}
          />
        ))}
      </div>
    </section>
  );
}
