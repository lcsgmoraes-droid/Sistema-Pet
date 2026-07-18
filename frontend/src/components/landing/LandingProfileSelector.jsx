import {
  ArrowRight,
  CheckCircle2,
  Grid2X2,
  Scissors,
  ShoppingBag,
  Stethoscope,
} from "lucide-react";
import { Link } from "react-router-dom";
import { publicPlans, segmentOptions, segmentSummaries } from "../../data/publicPlans";

const profileIcons = {
  all: Grid2X2,
  pet: ShoppingBag,
  vet: Stethoscope,
  grooming: Scissors,
};

export default function LandingProfileSelector({
  activeProfileId,
  onProfileChange,
  salesContactUrl,
}) {
  const activeProfile = segmentSummaries[activeProfileId];

  return (
    <section id="solucoes" className="scroll-mt-16 border-b border-slate-200 bg-white py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mx-auto max-w-4xl text-center">
          <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-700">
            Qual é o seu perfil?
          </p>
          <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">
            Veja somente o que faz sentido para o seu negócio.
          </h2>
          <p className="mt-5 text-lg leading-8 text-slate-600">
            Você pode contratar um módulo, combinar dois ou reunir toda a operação no CorePet.
          </p>
        </div>

        <div
          className="mx-auto mt-10 grid max-w-5xl gap-3 rounded-3xl bg-slate-100 p-3 sm:grid-cols-2 lg:grid-cols-4"
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
                className={`flex items-center justify-center gap-2 rounded-2xl px-4 py-4 text-sm font-extrabold transition ${
                  isActive
                    ? "bg-slate-950 text-white shadow-xl"
                    : "bg-white text-slate-700 hover:-translate-y-0.5 hover:text-slate-950 hover:shadow-md"
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? "text-emerald-300" : "text-emerald-700"}`} />
                {profile.label}
              </button>
            );
          })}
        </div>

        <article className="mt-8 overflow-hidden rounded-[2rem] border border-slate-200 bg-slate-950 text-white shadow-2xl">
          <div className="grid gap-8 p-7 sm:p-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:p-12">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-300">
                {activeProfile.eyebrow}
              </p>
              <h3 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
                {activeProfile.title}
              </h3>
              <p className="mt-5 text-lg leading-8 text-slate-300">{activeProfile.description}</p>
              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <Link
                  to={`/planos${activeProfileId === "all" ? "" : `?segment=${activeProfileId}`}`}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-5 py-3.5 font-extrabold text-slate-950 transition hover:bg-emerald-300"
                >
                  Ver funcionalidades e planos
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href={salesContactUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center rounded-xl border border-white/20 px-5 py-3.5 font-extrabold text-white transition hover:bg-white/10"
                >
                  Pedir uma demonstração
                </a>
              </div>
            </div>

            <div className="space-y-3">
              {activeProfile.highlights.map((highlight) => (
                <div key={highlight} className="flex items-start gap-3 rounded-2xl bg-white/5 p-4">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 flex-none text-emerald-300" />
                  <span className="font-semibold text-slate-200">{highlight}</span>
                </div>
              ))}
              {activeProfileId !== "all" && (
                <div className="grid gap-2 pt-2 sm:grid-cols-2">
                  {publicPlans[activeProfileId].map((plan) => (
                    <div
                      key={plan.id}
                      className="rounded-2xl border border-white/10 bg-white/10 p-4"
                    >
                      <p className="text-sm font-bold text-slate-300">{plan.name}</p>
                      <p className="mt-1 text-xl font-black text-white">
                        R$ {plan.price}
                        <span className="text-xs font-semibold text-slate-400">/mês</span>
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}
