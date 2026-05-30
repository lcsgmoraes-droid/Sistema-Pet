import {
  ArrowRight,
  BarChart3,
  Check,
  CreditCard,
  Database,
  MessageCircle,
  Package,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Users,
} from "lucide-react";
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const whatsappUrl =
  "https://wa.me/5518997401641?text=Ol%C3%A1!%20Quero%20come%C3%A7ar%20no%20Plano%20B%C3%A1sico%20do%20CorePet.";

const heroImage =
  "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=2200&q=85";

const includedItems = [
  { icon: Users, title: "Clientes e pets", text: "Cadastro, histórico essencial e organização da base." },
  { icon: Package, title: "Produtos e estoque", text: "SKU, validade, lotes, movimentações e saldo operacional." },
  { icon: ShoppingCart, title: "PDV e caixa", text: "Venda no balcão, pagamentos, sangria, suprimento e fechamento." },
  { icon: BarChart3, title: "Vendas e gestão", text: "Lista de vendas, visão por cliente e indicadores básicos." },
  { icon: CreditCard, title: "Formas de pagamento", text: "Cadastro de meios, operadoras e taxas para venda diária." },
  { icon: ShieldCheck, title: "Usuários e permissões", text: "Perfis de acesso, LGPD operacional e isolamento por empresa." },
];

const processSteps = [
  {
    title: "Teste o Básico",
    text: "30 dias grátis com o plano essencial completo.",
  },
  {
    title: "Crie sua empresa",
    text: "Cadastro online já cria o tenant no Plano Básico.",
  },
  {
    title: "Conheça os Betas",
    text: "Módulos avançados aparecem como vitrine e piloto acompanhado.",
  },
];

const nextModules = [
  "Financeiro ERP completo",
  "Campanhas e fidelidade avançadas",
  "E-commerce e canais de venda",
  "Veterinário, banho e tosa e app mobile",
];

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/lembretes", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    const previousTitle = document.title;
    const existingMetaDescription = document.querySelector('meta[name="description"]');
    const previousDescription = existingMetaDescription?.getAttribute("content") || "";
    const metaDescription = existingMetaDescription || document.createElement("meta");

    if (!existingMetaDescription) {
      metaDescription.setAttribute("name", "description");
      document.head.appendChild(metaDescription);
    }

    document.title = "CorePet | 30 dias grátis do Plano Básico";
    metaDescription.setAttribute(
      "content",
      "Teste o Plano Básico do CorePet por 30 dias: clientes, pets, produtos, estoque, PDV, caixa, vendas, usuários e permissões."
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

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-violet-700 focus:shadow-lg"
      >
        Pular para o conteúdo principal
      </a>

      <nav className="fixed left-0 right-0 top-0 z-50 border-b border-white/15 bg-slate-950/70 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/landing" className="flex items-center gap-2 font-bold text-white">
            <img src="/favicon.svg" alt="" className="h-7 w-7 rounded-md" />
            CorePet
          </Link>

          <div className="hidden items-center gap-7 text-sm font-semibold text-slate-200 md:flex">
            <a href="#plano-basico" className="hover:text-white">Plano Básico</a>
            <a href="#incluido" className="hover:text-white">Incluído</a>
            <a href="#proximos-modulos" className="hover:text-white">Módulos futuros</a>
          </div>

          <div className="flex items-center gap-3">
            <Link to="/login" className="hidden text-sm font-semibold text-white/90 hover:text-white sm:inline-flex">
              Entrar
            </Link>
            <Link
              to="/register?plan=basico"
              className="inline-flex items-center gap-2 rounded-md bg-emerald-400 px-4 py-2 text-sm font-bold text-slate-950 transition hover:bg-emerald-300"
            >
              Começar
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </nav>

      <main id="main-content">
        <section
          className="relative flex min-h-[86vh] items-center bg-cover bg-center pt-16"
          style={{
            backgroundImage: `linear-gradient(90deg, rgba(15,23,42,0.92) 0%, rgba(15,23,42,0.78) 46%, rgba(15,23,42,0.30) 100%), url(${heroImage})`,
          }}
        >
          <div className="mx-auto w-full max-w-6xl px-4 py-20 text-white">
            <div className="max-w-3xl">
              <span className="inline-flex items-center gap-2 rounded-md border border-emerald-300/40 bg-emerald-300/15 px-3 py-1 text-sm font-bold text-emerald-100">
                <Sparkles className="h-4 w-4" />
                30 dias grátis do Plano Básico
              </span>
              <h1 className="mt-6 text-4xl font-extrabold leading-tight md:text-6xl">
                CorePet
              </h1>
              <p className="mt-5 max-w-2xl text-xl leading-8 text-slate-100">
                Use clientes, pets, estoque, PDV, caixa, vendas e permissões sem pagar no
                primeiro mês. Os módulos avançados aparecem como próximos passos ou pilotos.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  to="/register?plan=basico"
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-400 px-6 py-3 font-bold text-slate-950 shadow-lg shadow-emerald-950/20 transition hover:bg-emerald-300"
                >
                  Começar 30 dias grátis
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href={whatsappUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-2 rounded-md border border-white/30 bg-white/10 px-6 py-3 font-semibold text-white backdrop-blur transition hover:bg-white/20"
                >
                  <MessageCircle className="h-4 w-4" />
                  Falar com vendas
                </a>
              </div>
            </div>
          </div>
        </section>

        <section id="plano-basico" className="border-b border-slate-200 bg-slate-50">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <div>
              <p className="text-sm font-bold uppercase tracking-wide text-violet-700">
                Contratação guiada
              </p>
              <h2 className="mt-2 text-3xl font-extrabold text-slate-950 md:text-4xl">
                O Básico é o ponto de entrada.
              </h2>
              <p className="mt-4 text-lg leading-8 text-slate-600">
                O primeiro acesso libera 30 dias do Básico completo. Quando o cliente decidir
                contratar, ele segue no mesmo plano, sem troca de promessa no meio do caminho.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              {processSteps.map((step, index) => (
                <article key={step.title} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                  <span className="text-sm font-extrabold text-emerald-600">0{index + 1}</span>
                  <h3 className="mt-3 font-bold text-slate-950">{step.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{step.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="incluido" className="bg-white py-16">
          <div className="mx-auto max-w-6xl px-4">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
              <div>
                <p className="text-sm font-bold uppercase tracking-wide text-emerald-700">
                  Incluso no Plano Básico
                </p>
                <h2 className="mt-2 text-3xl font-extrabold text-slate-950">
                  O essencial para operar sem planilha.
                </h2>
              </div>
              <Link
                to="/planos"
                className="inline-flex w-fit items-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
              >
                Ver detalhes do plano
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {includedItems.map(({ icon: Icon, title, text }) => (
                <article key={title} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-50 text-emerald-700">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-4 font-bold text-slate-950">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="proximos-modulos" className="bg-slate-950 py-16 text-white">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 lg:grid-cols-[1fr_1fr] lg:items-center">
            <div>
              <span className="inline-flex items-center gap-2 rounded-md bg-amber-300/15 px-3 py-1 text-sm font-bold text-amber-200">
                <Sparkles className="h-4 w-4" />
                O que vem por aí
              </span>
              <h2 className="mt-5 text-3xl font-extrabold md:text-4xl">
                Mais recursos para conhecer e pedir acesso.
              </h2>
              <p className="mt-4 text-lg leading-8 text-slate-300">
                A vitrine mostra módulos em validação com selo Beta. Eles não são liberados
                automaticamente: entram como piloto acompanhado quando fizer sentido para o cliente.
              </p>
            </div>

            <div className="grid gap-3">
              {nextModules.map((module) => (
                <div key={module} className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-4 py-3">
                  <Database className="h-5 w-5 flex-none text-amber-200" />
                  <span className="font-semibold text-slate-100">{module}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-emerald-50 py-16">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-4 md:flex-row md:items-center">
            <div>
              <p className="text-sm font-bold uppercase tracking-wide text-emerald-700">
                Próximo passo
              </p>
              <h2 className="mt-2 text-3xl font-extrabold text-slate-950">
                Comece com 30 dias grátis no Básico.
              </h2>
              <p className="mt-3 max-w-2xl text-slate-600">
                O cadastro cria a empresa no Plano Básico e mantém módulos avançados como
                Beta sob liberação acompanhada. Integrações externas específicas não fazem parte desta oferta.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link
                to="/register?plan=basico"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-950 px-6 py-3 font-bold text-white transition hover:bg-slate-800"
              >
                Começar 30 dias grátis
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center justify-center rounded-md border border-emerald-200 bg-white px-6 py-3 font-bold text-slate-700 transition hover:bg-emerald-100"
              >
                Já sou cliente
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-white py-8 text-slate-500">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 text-sm md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <img src="/favicon.svg" alt="" className="h-5 w-5 rounded" />
            CorePet
          </div>
          <div className="flex flex-wrap gap-5">
            <Link to="/termos" className="hover:text-slate-900">Termos</Link>
            <Link to="/privacidade" className="hover:text-slate-900">Privacidade</Link>
            <Link to="/planos" className="hover:text-slate-900">Planos</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
