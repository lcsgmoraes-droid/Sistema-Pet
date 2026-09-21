import {
  ArrowRight,
  Check,
  MessageCircle,
  Minus,
  Scissors,
  ShoppingBag,
  Stethoscope,
} from "lucide-react";
import { Link } from "react-router-dom";
import { buildSalesContactUrl, publicPlanComparisons, publicPlans } from "../../data/publicPlans";

const profileOptions = [
  {
    id: "pet",
    icon: ShoppingBag,
    eyebrow: "Comércio e gestão",
    title: "Planos para Pet Shop",
  },
  {
    id: "vet",
    icon: Stethoscope,
    eyebrow: "Atendimento e clínica",
    title: "Planos para Clínica Veterinária",
  },
  {
    id: "grooming",
    icon: Scissors,
    eyebrow: "Agenda e serviços",
    title: "Planos para Banho & Tosa",
  },
];

const tableTitles = {
  pet: "Planos para Pet Shop",
  vet: "Planos para Clínica Veterinária",
  grooming: "Planos para Banho & Tosa",
};

function ComparisonValue({ value }) {
  if (value === true) {
    return (
      <span className="inline-flex items-center text-emerald-700">
        <Check className="h-5 w-5" />
        <span className="sr-only">Incluído</span>
      </span>
    );
  }

  if (value === false) {
    return (
      <span className="inline-flex items-center text-slate-300">
        <Minus className="h-5 w-5" />
        <span className="sr-only">Não incluído</span>
      </span>
    );
  }

  return (
    <span className="inline-flex rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-extrabold text-slate-700">
      {value}
    </span>
  );
}

function PlanComparisonTable({ segmentId, salesContactUrl }) {
  const plans = publicPlans[segmentId];
  const rows = publicPlanComparisons[segmentId];

  return (
    <div
      id="comparacao-planos"
      className="scroll-mt-20 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5"
    >
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-6 sm:px-7">
        <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
          Compare recursos e valores
        </p>
        <h3 className="mt-1 text-2xl font-black tracking-tight sm:text-3xl">
          {tableTitles[segmentId]}
        </h3>
        <p className="mt-2 text-sm font-semibold text-slate-500 sm:hidden">
          Deslize a tabela para comparar os planos.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left">
          <thead>
            <tr className="border-b border-slate-200 bg-white">
              <th className="min-w-64 px-5 py-5 text-sm font-black text-slate-700 sm:px-7">
                Funcionalidade
              </th>
              {plans.map((plan) => (
                <th
                  key={plan.id}
                  className={`min-w-36 px-4 py-5 text-center align-top ${
                    plan.featured ? "bg-emerald-50" : ""
                  }`}
                >
                  <span className="block text-sm font-black text-slate-950">{plan.name}</span>
                  <span className="mt-1 block text-lg font-black text-emerald-700">
                    R$ {plan.price}
                  </span>
                  <span className="block text-[11px] font-semibold text-slate-500">por mês</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-slate-100 last:border-b-0">
                <th className="px-5 py-4 text-sm font-bold leading-5 text-slate-700 sm:px-7">
                  {row.label}
                </th>
                {row.values.map((value, index) => (
                  <td
                    key={`${row.label}-${plans[index].id}`}
                    className={`px-4 py-4 text-center ${
                      plans[index].featured ? "bg-emerald-50/60" : ""
                    }`}
                  >
                    <ComparisonValue value={value} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-200 bg-slate-50 px-5 py-5 sm:flex-row sm:items-center sm:justify-end sm:px-7">
        <Link
          to={`/planos?segment=${segmentId}`}
          className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-extrabold text-slate-800 transition hover:border-slate-400"
        >
          Ver detalhes
        </Link>
        <a
          href={salesContactUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-slate-800"
        >
          Solicitar demonstração
          <ArrowRight className="h-4 w-4" />
        </a>
      </div>
    </div>
  );
}

export default function LandingProfileSelector({
  activeProfileId,
  onProfileChange,
  salesContactUrl,
}) {
  const customContactUrl = buildSalesContactUrl(
    "Olá! Tenho mais de uma área e quero montar uma solução personalizada do CorePet.",
  );

  return (
    <section id="planos" className="scroll-mt-16 bg-slate-50 py-16 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-700">
            Escolha sua solução
          </p>
          <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">
            Qual é o seu tipo de negócio?
          </h2>
          <p className="mt-4 text-lg leading-8 text-slate-600">
            Clique em uma opção para ver os planos e preços.
          </p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {profileOptions.map((profile) => {
            const Icon = profile.icon;
            const isActive = profile.id === activeProfileId;

            return (
              <button
                key={profile.id}
                type="button"
                aria-pressed={isActive}
                onClick={() => onProfileChange(profile.id)}
                className={`group flex min-h-56 flex-col rounded-3xl border-2 p-6 text-left transition ${
                  isActive
                    ? "border-slate-950 bg-slate-950 text-white shadow-xl"
                    : "border-slate-200 bg-white text-slate-950 shadow-sm hover:-translate-y-1 hover:border-emerald-400 hover:shadow-xl"
                }`}
              >
                <span
                  className={`flex h-12 w-12 items-center justify-center rounded-2xl ${
                    isActive ? "bg-emerald-400 text-slate-950" : "bg-emerald-100 text-emerald-800"
                  }`}
                >
                  <Icon className="h-6 w-6" />
                </span>
                <span
                  className={`mt-6 text-xs font-black uppercase tracking-[0.12em] ${
                    isActive ? "text-emerald-300" : "text-slate-500"
                  }`}
                >
                  {profile.eyebrow}
                </span>
                <span className="mt-2 block text-xl font-black leading-7">{profile.title}</span>
                <span
                  className={`mt-auto flex items-center gap-2 pt-6 text-sm font-extrabold ${
                    isActive ? "text-emerald-300" : "text-emerald-800"
                  }`}
                >
                  Ver planos e preços
                  <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
                </span>
              </button>
            );
          })}

          <a
            href={customContactUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex min-h-56 flex-col rounded-3xl border-2 border-violet-200 bg-violet-50 p-6 text-left text-slate-950 shadow-sm transition hover:-translate-y-1 hover:border-violet-400 hover:shadow-xl"
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-200 text-violet-800">
              <MessageCircle className="h-6 w-6" />
            </span>
            <span className="mt-6 text-xs font-black uppercase tracking-[0.12em] text-violet-700">
              Solução personalizada
            </span>
            <span className="mt-2 block text-xl font-black leading-7">Tenho mais de uma área</span>
            <span className="mt-auto flex items-center gap-2 pt-6 text-sm font-extrabold text-violet-800">
              Falar com nosso time
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </span>
          </a>
        </div>

        <div className="mt-8" aria-live="polite">
          {activeProfileId ? (
            <PlanComparisonTable segmentId={activeProfileId} salesContactUrl={salesContactUrl} />
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-6 text-center text-sm font-semibold text-slate-500">
              Selecione seu negócio acima para comparar os planos.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
