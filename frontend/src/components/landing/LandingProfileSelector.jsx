import {
  ArrowRight,
  Check,
  CheckCircle2,
  Grid2X2,
  Minus,
  Scissors,
  ShoppingBag,
  Stethoscope,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  publicPlanComparisons,
  publicPlans,
  segmentOptions,
  segmentSummaries,
} from "../../data/publicPlans";

const profileIcons = {
  all: Grid2X2,
  pet: ShoppingBag,
  vet: Stethoscope,
  grooming: Scissors,
};

const profileActionLabels = {
  all: "Quero combinar áreas",
  pet: "CorePet para meu Pet Shop",
  vet: "CorePet para Veterinário",
  grooming: "CorePet para Banho & Tosa",
};

function ComparisonValue({ value }) {
  if (value === true) {
    return (
      <span className="inline-flex items-center gap-1.5 font-bold text-emerald-700">
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
    <div className="mt-8 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-lg">
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-5 sm:px-7">
        <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
          Compare sem complicação
        </p>
        <h3 className="mt-1 text-2xl font-black tracking-tight">O que cada plano tem</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Todos começam com 30 dias de acesso completo. Depois, você continua no plano escolhido.
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
                    className={`px-4 py-4 text-center ${plans[index].featured ? "bg-emerald-50/60" : ""}`}
                  >
                    <ComparisonValue value={value} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-200 bg-slate-50 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
        <p className="text-sm font-semibold text-slate-600">
          Precisa de ajuda? A implantação humana está incluída para as primeiras empresas.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Link
            to={`/planos?segment=${segmentId}`}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-slate-800"
          >
            Ver detalhes dos planos
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href={salesContactUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-xl border-2 border-emerald-500 px-4 py-3 text-sm font-extrabold text-emerald-800 transition hover:bg-emerald-50"
          >
            Falar com a CorePet
          </a>
        </div>
      </div>
    </div>
  );
}

export default function LandingProfileSelector({
  activeProfileId,
  onProfileChange,
  salesContactUrl,
}) {
  const activeProfile = segmentSummaries[activeProfileId];

  return (
    <section
      id="solucoes"
      className="scroll-mt-16 border-b border-slate-200 bg-slate-50 py-14 sm:py-16"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-700">
              Escolha o seu negócio
            </p>
            <h2 className="mt-2 text-3xl font-black tracking-tight sm:text-5xl">
              Clique no seu perfil e veja somente o que interessa.
            </h2>
          </div>
          <p className="max-w-md text-base leading-7 text-slate-600">
            Você pode trocar o perfil a qualquer momento ou combinar áreas na mesma operação.
          </p>
        </div>

        <div
          className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
          aria-label="Escolha o perfil do negócio"
        >
          {segmentOptions.map((profile) => {
            const Icon = profileIcons[profile.id];
            const isActive = profile.id === activeProfileId;
            return (
              <button
                key={profile.id}
                type="button"
                aria-pressed={isActive}
                onClick={() => onProfileChange(profile.id)}
                className={`group flex min-h-24 items-center gap-4 rounded-2xl border-2 px-5 py-4 text-left shadow-sm transition ${
                  isActive
                    ? "border-slate-950 bg-slate-950 text-white shadow-xl"
                    : "border-slate-200 bg-white text-slate-800 hover:-translate-y-0.5 hover:border-emerald-500 hover:shadow-lg"
                }`}
              >
                <span
                  className={`flex h-11 w-11 flex-none items-center justify-center rounded-xl ${
                    isActive ? "bg-emerald-400 text-slate-950" : "bg-emerald-100 text-emerald-800"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                </span>
                <span>
                  <span
                    className={`block text-xs font-bold ${isActive ? "text-emerald-300" : "text-slate-500"}`}
                  >
                    Clique para selecionar
                  </span>
                  <span className="mt-0.5 block text-sm font-black leading-5">
                    {profileActionLabels[profile.id]}
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        <article className="mt-7 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="grid gap-7 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-700">
                {activeProfile.eyebrow}
              </p>
              <h3 className="mt-2 text-3xl font-black tracking-tight">{activeProfile.title}</h3>
              <p className="mt-4 text-base leading-7 text-slate-600">{activeProfile.description}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {activeProfile.highlights.map((highlight) => (
                <div key={highlight} className="flex items-start gap-3 rounded-2xl bg-slate-50 p-4">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 flex-none text-emerald-600" />
                  <span className="text-sm font-bold leading-6 text-slate-700">{highlight}</span>
                </div>
              ))}
            </div>
          </div>
        </article>

        {activeProfileId === "all" ? (
          <div className="mt-7 grid gap-4 lg:grid-cols-3">
            {["pet", "vet", "grooming"].map((segmentId) => {
              const summary = segmentSummaries[segmentId];
              const Icon = profileIcons[segmentId];
              return (
                <button
                  key={segmentId}
                  type="button"
                  onClick={() => onProfileChange(segmentId)}
                  className="flex items-center gap-4 rounded-2xl border-2 border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-500 hover:shadow-lg"
                >
                  <span className="flex h-12 w-12 flex-none items-center justify-center rounded-xl bg-slate-950 text-emerald-300">
                    <Icon className="h-6 w-6" />
                  </span>
                  <span className="flex-1">
                    <span className="block font-black">{profileActionLabels[segmentId]}</span>
                    <span className="mt-1 block text-sm font-semibold text-slate-500">
                      Planos a partir de {summary.startingPrice}/mês
                    </span>
                  </span>
                  <ArrowRight className="h-5 w-5 text-emerald-700" />
                </button>
              );
            })}
          </div>
        ) : (
          <PlanComparisonTable segmentId={activeProfileId} salesContactUrl={salesContactUrl} />
        )}
      </div>
    </section>
  );
}
