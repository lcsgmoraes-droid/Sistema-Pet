import {
  ArrowRight,
  Check,
  FileText,
  Grid2X2,
  Scissors,
  ShieldCheck,
  ShoppingBag,
  Stethoscope,
} from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import LaunchOfferBanner from "../components/marketing/LaunchOfferBanner";
import {
  buildSalesContactUrl,
  planOrganizationTypes,
  publicPlans,
  segmentOptions,
  segmentSummaries,
  serviceInvoiceAddon,
} from "../data/publicPlans";

const segmentIcons = {
  all: Grid2X2,
  pet: ShoppingBag,
  vet: Stethoscope,
  grooming: Scissors,
};

const validSegments = new Set(segmentOptions.map((segment) => segment.id));

function PlanCard({ plan, segment }) {
  const contactUrl = buildSalesContactUrl(
    `Olá! Quero conhecer o plano ${plan.name} do CorePet para ${segmentOptions.find((item) => item.id === segment)?.label}.`,
  );

  return (
    <article
      className={`relative flex h-full flex-col rounded-3xl border bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-xl ${
        plan.featured ? "border-emerald-400 ring-4 ring-emerald-100" : "border-slate-200"
      }`}
    >
      {plan.featured && (
        <span className="absolute right-5 top-5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-black uppercase tracking-wide text-emerald-800">
          Mais indicado
        </span>
      )}
      <p className="pr-28 text-sm font-black uppercase tracking-[0.14em] text-emerald-700">
        {plan.name}
      </p>
      <div className="mt-4 flex items-end gap-1 text-slate-950">
        <span className="pb-1 text-lg font-bold">R$</span>
        <span className="text-4xl font-black tracking-tight">{plan.price}</span>
        <span className="pb-1 text-sm font-semibold text-slate-500">/mês</span>
      </div>
      <p className="mt-4 min-h-20 leading-7 text-slate-600">{plan.description}</p>
      <p className="mt-4 rounded-xl bg-amber-50 px-3 py-2 text-xs font-bold leading-5 text-amber-900">
        Primeiro mês: acesso completo ao CorePet com implantação assistida.
      </p>
      <ul className="mt-6 flex-1 space-y-3 border-t border-slate-100 pt-6">
        {plan.features.map((feature) => (
          <li key={feature} className="flex items-start gap-3 text-sm leading-6 text-slate-700">
            <Check className="mt-1 h-4 w-4 flex-none text-emerald-600" />
            <span>{feature}</span>
          </li>
        ))}
      </ul>
      <Link
        to={`/register?plan=${encodeURIComponent(plan.id)}&organization_type=${encodeURIComponent(planOrganizationTypes[segment])}`}
        className={`mt-7 inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 font-extrabold transition ${
          plan.featured
            ? "bg-emerald-400 text-slate-950 hover:bg-emerald-300"
            : "bg-slate-950 text-white hover:bg-slate-800"
        }`}
      >
        Quero este plano
        <ArrowRight className="h-4 w-4" />
      </Link>
      <a
        href={contactUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-3 text-center text-sm font-bold text-slate-600 underline decoration-slate-300 underline-offset-4 hover:text-slate-950"
      >
        Falar com um especialista
      </a>
    </article>
  );
}

function AllSegmentsOverview({ onSelect }) {
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      {["pet", "vet", "grooming"].map((segmentId) => {
        const summary = segmentSummaries[segmentId];
        const Icon = segmentIcons[segmentId];
        const planCount = publicPlans[segmentId].length;
        return (
          <article
            key={segmentId}
            className="flex flex-col rounded-3xl border border-slate-200 bg-white p-7 shadow-sm"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-emerald-300">
              <Icon className="h-6 w-6" />
            </div>
            <p className="mt-6 text-sm font-black uppercase tracking-[0.14em] text-emerald-700">
              {segmentOptions.find((item) => item.id === segmentId)?.label}
            </p>
            <h2 className="mt-2 text-2xl font-black tracking-tight">{summary.title}</h2>
            <p className="mt-3 flex-1 leading-7 text-slate-600">{summary.description}</p>
            <div className="mt-6 rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                {planCount} {planCount === 1 ? "plano" : "planos"} · a partir de
              </p>
              <p className="mt-1 text-2xl font-black">
                {summary.startingPrice}
                <span className="text-sm font-semibold text-slate-500">/mês</span>
              </p>
            </div>
            <button
              type="button"
              onClick={() => onSelect(segmentId)}
              className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 py-3 font-extrabold text-slate-800 transition hover:border-emerald-400 hover:bg-emerald-50"
            >
              Ver planos
              <ArrowRight className="h-4 w-4" />
            </button>
          </article>
        );
      })}
    </div>
  );
}

function ServiceInvoiceAddon() {
  const contactUrl = buildSalesContactUrl(
    "Olá! Quero contratar a emissão de NFS-e integrada ao CorePet por R$ 59,90 mensais.",
  );

  return (
    <section className="mt-12 overflow-hidden rounded-3xl bg-slate-950 text-white shadow-xl">
      <div className="grid gap-8 p-7 sm:p-9 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full bg-amber-300/15 px-3 py-1.5 text-sm font-bold text-amber-200">
            <FileText className="h-4 w-4" />
            Adicional opcional
          </span>
          <h2 className="mt-5 text-3xl font-black tracking-tight">{serviceInvoiceAddon.name}</h2>
          <div className="mt-4 flex items-end gap-1">
            <span className="pb-1 text-lg font-bold">R$</span>
            <span className="text-4xl font-black">{serviceInvoiceAddon.price}</span>
            <span className="pb-1 text-sm font-semibold text-slate-400">/mês</span>
          </div>
          <p className="mt-4 leading-7 text-slate-300">{serviceInvoiceAddon.description}</p>
        </div>
        <div>
          <ul className="grid gap-3 sm:grid-cols-2">
            {serviceInvoiceAddon.features.map((feature) => (
              <li
                key={feature}
                className="flex items-start gap-3 rounded-2xl bg-white/5 p-4 text-sm leading-6 text-slate-200"
              >
                <Check className="mt-1 h-4 w-4 flex-none text-emerald-300" />
                <span>{feature}</span>
              </li>
            ))}
          </ul>
          <a
            href={contactUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-amber-300 px-5 py-3.5 font-extrabold text-slate-950 transition hover:bg-amber-200 sm:w-auto"
          >
            Quero ativar a emissão integrada
            <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </div>
    </section>
  );
}

export default function Planos() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedSegment = searchParams.get("segment") || "all";
  const activeSegment = validSegments.has(requestedSegment) ? requestedSegment : "all";
  const activeSummary = segmentSummaries[activeSegment];

  const selectSegment = (segmentId) => {
    setSearchParams(segmentId === "all" ? {} : { segment: segmentId });
    globalThis.scrollTo?.({ top: 0, behavior: "smooth" });
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/landing" className="flex items-center gap-2.5 font-extrabold">
            <img src="/brand/corepet/corepet-icon-64.png" alt="" className="h-8 w-8 rounded-lg" />
            CorePet
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <Link
              to="/landing"
              className="hidden font-semibold text-slate-600 hover:text-slate-950 sm:inline-flex"
            >
              Conhecer o sistema
            </Link>
            <Link
              to="/login"
              className="rounded-lg bg-slate-950 px-4 py-2 font-bold text-white hover:bg-slate-800"
            >
              Entrar
            </Link>
          </div>
        </div>
      </header>

      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-14 text-center sm:px-6 sm:py-20">
          <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-4 py-2 text-sm font-black text-emerald-800">
            <ShieldCheck className="h-4 w-4" />
            Planos para cada fase do negócio
          </span>
          <h1 className="mx-auto mt-5 max-w-4xl text-4xl font-black tracking-tight sm:text-6xl">
            Escolha como o CorePet vai trabalhar com você.
          </h1>
          <p className="mx-auto mt-5 max-w-3xl text-lg leading-8 text-slate-600">
            Comece com o necessário para a sua realidade e avance quando precisar de mais gestão,
            automação ou estrutura.
          </p>

          <div className="mx-auto mt-8 max-w-5xl text-left">
            <LaunchOfferBanner />
          </div>

          <div
            className="mx-auto mt-9 grid max-w-4xl gap-2 rounded-2xl bg-slate-100 p-2 sm:grid-cols-4"
            aria-label="Escolha o perfil do negócio"
          >
            {segmentOptions.map((segment) => {
              const Icon = segmentIcons[segment.id];
              const isActive = segment.id === activeSegment;
              return (
                <button
                  key={segment.id}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => selectSegment(segment.id)}
                  className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-extrabold transition ${
                    isActive
                      ? "bg-slate-950 text-white shadow-lg"
                      : "bg-transparent text-slate-600 hover:bg-white hover:text-slate-950"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-emerald-300" : ""}`} />
                  {segment.shortLabel}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20">
        <div className="mb-10 max-w-4xl">
          <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-700">
            {activeSummary.eyebrow}
          </p>
          <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">
            {activeSummary.title}
          </h2>
          <p className="mt-4 text-lg leading-8 text-slate-600">{activeSummary.description}</p>
        </div>

        {activeSegment === "all" ? (
          <AllSegmentsOverview onSelect={selectSegment} />
        ) : (
          <div
            className={`grid gap-5 ${publicPlans[activeSegment].length === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3"}`}
          >
            {publicPlans[activeSegment].map((plan) => (
              <PlanCard key={plan.id} plan={plan} segment={activeSegment} />
            ))}
          </div>
        )}

        {(activeSegment === "vet" || activeSegment === "grooming") && <ServiceInvoiceAddon />}

        {activeSegment === "all" && (
          <section className="mt-12 rounded-3xl border border-violet-200 bg-violet-50 p-7 sm:p-9">
            <p className="text-sm font-black uppercase tracking-[0.16em] text-violet-700">
              Precisa de mais de um módulo?
            </p>
            <div className="mt-3 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
              <div className="max-w-3xl">
                <h2 className="text-3xl font-black tracking-tight">
                  Monte o CorePet para a sua operação.
                </h2>
                <p className="mt-3 leading-7 text-slate-600">
                  Loja Pet, Veterinário e Banho & Tosa podem compartilhar clientes, pets, vendas e
                  gestão. Os combos serão configurados conforme os módulos e o tamanho da sua
                  equipe.
                </p>
              </div>
              <a
                href={buildSalesContactUrl(
                  "Olá! Quero conhecer uma combinação de módulos do CorePet.",
                )}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex flex-none items-center justify-center gap-2 rounded-xl bg-violet-700 px-5 py-3.5 font-extrabold text-white transition hover:bg-violet-600"
              >
                Montar minha solução
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </section>
        )}
      </section>

      <section className="bg-slate-950 py-14 text-white">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-7 px-4 sm:px-6 lg:flex-row lg:items-center">
          <div className="max-w-3xl">
            <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-300">
              Ainda não sabe qual escolher?
            </p>
            <h2 className="mt-3 text-3xl font-black tracking-tight">
              Mostre sua operação. A gente indica o melhor começo.
            </h2>
            <p className="mt-3 leading-7 text-slate-300">
              Sem contratar recursos que você ainda não precisa e com um caminho claro para crescer.
            </p>
          </div>
          <a
            href={buildSalesContactUrl("Olá! Quero ajuda para escolher o plano ideal do CorePet.")}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex flex-none items-center justify-center gap-2 rounded-xl bg-emerald-400 px-6 py-4 font-extrabold text-slate-950 transition hover:bg-emerald-300"
          >
            Falar com a CorePet
            <ArrowRight className="h-5 w-5" />
          </a>
        </div>
      </section>
    </main>
  );
}
