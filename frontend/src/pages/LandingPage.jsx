import { ArrowRight, CheckCircle2, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import LandingProfileSelector from "../components/landing/LandingProfileSelector";

const salesContactUrl =
  "https://wa.me/5518997401641?text=Ol%C3%A1!%20Quero%20conhecer%20o%20CorePet%20e%20ver%20uma%20demonstra%C3%A7%C3%A3o.";

const businessTypes = ["Pet Shop", "Clínica Veterinária", "Banho & Tosa"];

export default function LandingPage() {
  const [activeProfileId, setActiveProfileId] = useState(null);

  useEffect(() => {
    const previousTitle = document.title;
    const existingMetaDescription = document.querySelector('meta[name="description"]');
    const previousDescription = existingMetaDescription?.getAttribute("content") || "";
    const metaDescription = existingMetaDescription || document.createElement("meta");

    if (!existingMetaDescription) {
      metaDescription.setAttribute("name", "description");
      document.head.appendChild(metaDescription);
    }

    document.title = "CorePet | Gestão para Pet Shop, Veterinário e Banho & Tosa";
    metaDescription.setAttribute(
      "content",
      "Planos de gestão para Pet Shop, Clínica Veterinária e Banho & Tosa.",
    );

    return () => {
      document.title = previousTitle;
      if (existingMetaDescription) {
        existingMetaDescription.setAttribute("content", previousDescription);
      } else {
        metaDescription.remove();
      }
    };
  }, []);

  const selectProfile = (profileId) => {
    setActiveProfileId(profileId);
    globalThis.setTimeout(() => {
      document.getElementById("comparacao-planos")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 80);
  };

  return (
    <div className="min-h-screen bg-white text-slate-950">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-violet-700 focus:shadow-xl"
      >
        Pular para o conteúdo principal
      </a>

      <nav className="fixed left-0 right-0 top-0 z-50 border-b border-white/10 bg-slate-950/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/landing" className="flex items-center gap-2.5 font-extrabold text-white">
            <img src="/brand/corepet/corepet-icon-64.png" alt="" className="h-8 w-8 rounded-lg" />
            CorePet
          </Link>

          <div className="hidden items-center gap-7 text-sm font-semibold text-slate-300 md:flex">
            <a href="#planos" className="transition hover:text-white">
              Planos
            </a>
            <a href="#demonstracao" className="transition hover:text-white">
              Demonstração
            </a>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="hidden text-sm font-semibold text-white/90 hover:text-white sm:inline-flex"
            >
              Entrar
            </Link>
            <a
              href={salesContactUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-4 py-2 text-sm font-extrabold text-slate-950 transition hover:bg-emerald-300"
            >
              <span className="hidden sm:inline">Quero uma demonstração</span>
              <span className="sm:hidden">Quero uma demo</span>
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </nav>

      <main id="main-content">
        <section className="relative isolate overflow-hidden bg-slate-950 pt-16 text-white">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_78%_28%,rgba(52,211,153,0.18),transparent_30%),radial-gradient(circle_at_16%_85%,rgba(124,58,237,0.14),transparent_32%)]" />
          <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-20 sm:px-6 sm:py-24 lg:grid-cols-[1.15fr_0.85fr] lg:py-28">
            <div className="max-w-3xl">
              <p className="text-sm font-black uppercase tracking-[0.18em] text-emerald-300">
                Gestão para o mercado pet
              </p>
              <h1 className="mt-4 text-4xl font-black leading-[1.05] tracking-tight sm:text-6xl">
                O CorePet certo para o seu negócio.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300 sm:text-xl">
                Escolha sua área e veja diretamente os planos, preços e recursos disponíveis.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <a
                  href="#planos"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-6 py-3.5 font-extrabold text-slate-950 transition hover:bg-emerald-300"
                >
                  Ver planos e preços
                  <ArrowRight className="h-5 w-5" />
                </a>
                <a
                  href={salesContactUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center rounded-xl border border-white/20 px-6 py-3.5 font-bold text-white transition hover:border-white/40 hover:bg-white/10"
                >
                  Falar com nosso time
                </a>
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-black/30 backdrop-blur sm:p-8">
              <p className="text-sm font-bold text-slate-400">Uma plataforma para</p>
              <div className="mt-5 space-y-3">
                {businessTypes.map((business) => (
                  <div
                    key={business}
                    className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3.5"
                  >
                    <CheckCircle2 className="h-5 w-5 flex-none text-emerald-400" />
                    <span className="font-extrabold text-white">{business}</span>
                  </div>
                ))}
              </div>
              <p className="mt-5 text-sm leading-6 text-slate-400">
                Use uma área ou combine várias na mesma operação.
              </p>
            </div>
          </div>
        </section>

        <LandingProfileSelector
          activeProfileId={activeProfileId}
          onProfileChange={selectProfile}
          salesContactUrl={salesContactUrl}
        />

        <section
          id="demonstracao"
          className="scroll-mt-16 border-t border-slate-200 bg-white py-16 sm:py-20"
        >
          <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 sm:px-6 lg:grid-cols-[0.72fr_1.28fr]">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-700">
                Veja em funcionamento
              </p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
                Conheça o CorePet em 30 segundos.
              </h2>
              <p className="mt-4 leading-7 text-slate-600">
                Uma visão rápida de como o sistema conecta operação, gestão e novas vendas.
              </p>
              <a
                href={salesContactUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-7 inline-flex items-center gap-2 font-extrabold text-emerald-800 hover:text-emerald-600"
              >
                Agendar uma demonstração
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>

            <div className="overflow-hidden rounded-3xl border border-slate-200 bg-slate-950 p-3 shadow-2xl shadow-slate-900/15">
              <div className="relative">
                <video
                  className="aspect-video w-full rounded-2xl bg-black object-contain"
                  controls
                  playsInline
                  preload="metadata"
                  poster="/marketing/corepet-demo-ecossistema-integrado-poster.jpg"
                >
                  <source
                    src="/marketing/corepet-demo-ecossistema-integrado.mp4"
                    type="video/mp4"
                  />
                  Seu navegador não suporta vídeo HTML5.
                </video>
                <span className="pointer-events-none absolute left-4 top-4 inline-flex items-center gap-2 rounded-full bg-slate-950/80 px-3 py-1.5 text-xs font-black text-white backdrop-blur">
                  <Play className="h-3.5 w-3.5 fill-current text-emerald-300" />
                  CorePet por dentro
                </span>
              </div>
            </div>
          </div>
        </section>

        <section className="bg-emerald-50 py-16">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-7 px-4 sm:px-6 lg:flex-row lg:items-center">
            <div>
              <h2 className="text-3xl font-black tracking-tight">
                Quer ver o CorePet no seu dia a dia?
              </h2>
              <p className="mt-3 text-lg text-slate-600">
                Fale com nosso time e veja a solução mais adequada para sua operação.
              </p>
            </div>
            <a
              href={salesContactUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex flex-none items-center justify-center gap-2 rounded-xl bg-slate-950 px-7 py-4 font-extrabold text-white transition hover:bg-slate-800"
            >
              Falar com nosso time
              <ArrowRight className="h-5 w-5" />
            </a>
          </div>
        </section>
      </main>

      <footer className="bg-white py-8 text-slate-500">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 text-sm sm:px-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-2 font-extrabold text-slate-950">
            <img src="/brand/corepet/corepet-icon-64.png" alt="" className="h-6 w-6 rounded" />
            CorePet
          </div>
          <div className="flex flex-wrap gap-5">
            <Link to="/termos" className="hover:text-slate-950">
              Termos
            </Link>
            <Link to="/privacidade" className="hover:text-slate-950">
              Privacidade
            </Link>
            <Link to="/planos" className="hover:text-slate-950">
              Planos
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
