import {
  ArrowRight,
  BarChart3,
  BellRing,
  Boxes,
  Calculator,
  CheckCircle2,
  Clock3,
  Megaphone,
  PackageCheck,
  Play,
  Route,
  ShoppingBag,
  Smartphone,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const salesContactUrl =
  "https://wa.me/5518997401641?text=Ol%C3%A1!%20Quero%20conhecer%20o%20CorePet%20e%20ver%20uma%20demonstra%C3%A7%C3%A3o.";

const heroImage =
  "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=2200&q=88";

const activeSalesSteps = [
  {
    icon: ShoppingBag,
    label: "O cliente compra",
    text: "No balcão, no app ou no e-commerce.",
  },
  {
    icon: Sparkles,
    label: "O CorePet aprende",
    text: "Identifica consumo recorrente e protocolos configurados.",
  },
  {
    icon: BellRing,
    label: "O CorePet oferece",
    text: "Lembra o cliente pelo app no momento certo da recompra.",
  },
  {
    icon: TrendingUp,
    label: "Sua loja vende de novo",
    text: "Sem depender apenas de o cliente lembrar de voltar.",
  },
];

const platformPillars = [
  {
    icon: Smartphone,
    title: "ERP, app e e-commerce",
    text: "Cadastre uma vez. Produtos, preços, pedidos e estoque permanecem conectados em todos os canais.",
  },
  {
    icon: Calculator,
    title: "Lucro real em cada venda",
    text: "Taxas de cartão, impostos, custos, comissão e margem aparecem para o gestor acompanhar o resultado.",
  },
  {
    icon: Megaphone,
    title: "Campanhas dentro do sistema",
    text: "Crie públicos, ofertas e notificações no app usando os dados da própria operação.",
  },
  {
    icon: Route,
    title: "Entregas sob controle",
    text: "Organize rotas, entregadores, andamento e custos para entender o resultado além do caixa.",
  },
  {
    icon: BarChart3,
    title: "Gestão clara e automática",
    text: "DRE, fluxo de caixa, ponto de equilíbrio e indicadores transformam a operação em decisão.",
  },
  {
    icon: PackageCheck,
    title: "Compras mais inteligentes",
    text: "Sugestões de pedido ajudam a ganhar tempo, repor melhor e evitar excesso ou falta de produtos.",
  },
];

const unifiedChannels = [
  "Produto cadastrado uma única vez",
  "Publicação integrada no app e e-commerce",
  "Compra disponível 24 horas por dia",
  "Estoque atualizado independentemente do canal",
];

const screenHighlights = [
  {
    eyebrow: "E-commerce 24 horas",
    title: "Uma loja completa, bonita e conectada ao estoque",
    text: "Catálogo, busca, categorias, carrinho e pedidos usam os mesmos produtos e o mesmo estoque do ERP.",
    image: "/marketing/product-shots/ecommerce-catalogo.png",
    alt: "Catálogo real do e-commerce integrado ao CorePet",
    wide: true,
  },
  {
    eyebrow: "App do cliente",
    title: "A loja acompanha o cliente no celular",
    text: "Compra sem fila, loja, veterinário, calculadora de ração, pedidos e benefícios em um único app.",
    image: "/marketing/product-shots/app-inicio.png",
    alt: "Tela inicial real do aplicativo CorePet",
    portrait: true,
  },
  {
    eyebrow: "Catálogo no app",
    title: "Produtos disponíveis para comprar de qualquer lugar",
    text: "Busca, filtros, favoritos, preço e disponibilidade atualizados diretamente pela operação da loja.",
    image: "/marketing/product-shots/app-produtos.png",
    alt: "Catálogo de produtos real no aplicativo CorePet",
    portrait: true,
  },
  {
    eyebrow: "Recompra simplificada",
    title: "O cliente repete um pedido em poucos toques",
    text: "O histórico reúne compras do app, e-commerce e loja física e oferece a ação de comprar novamente.",
    image: "/marketing/product-shots/app-pedidos.png",
    alt: "Histórico de pedidos e botão repetir no aplicativo CorePet",
    portrait: true,
  },
  {
    eyebrow: "Fidelização integrada",
    title: "Cashback, cupons e cartão fidelidade visíveis",
    text: "O cliente entende seus benefícios e encontra motivos concretos para continuar comprando na mesma loja.",
    image: "/marketing/product-shots/app-beneficios.png",
    alt: "Benefícios, cashback e fidelidade no aplicativo CorePet",
    portrait: true,
  },
  {
    eyebrow: "Gestão em tempo real",
    title: "O gestor enxerga o resultado, não apenas o faturamento",
    text: "Taxas, impostos, descontos, custos, valor recebido, lucro e margem aparecem juntos e de forma clara.",
    image: "/marketing/product-shots/erp-resultado.png",
    alt: "Composição real do resultado de vendas no ERP CorePet",
    wide: true,
  },
  {
    eyebrow: "Automação no PDV",
    title: "Produto em falta entra na lista de espera",
    text: "Quando o estoque é reposto, o CorePet notifica o cliente automaticamente pelo app.",
    image: "/marketing/product-shots/pdv-lista-espera.png",
    alt: "Lista de espera automática para produtos sem estoque no PDV CorePet",
    wide: true,
  },
];

const systemDemoVideos = [
  {
    id: "recorrencia",
    eyebrow: "Recorrência inteligente · 28 segundos",
    title: "A próxima venda antes de o cliente esquecer.",
    text: "O CorePet aprende o intervalo de consumo, identifica a recompra e notifica o cliente automaticamente pelo app.",
    source: "/marketing/corepet-demo-recorrencia-inteligente.mp4",
    poster: "/marketing/corepet-demo-recorrencia-inteligente-poster.jpg",
    shortTitle: "Recorrência automática",
    duration: "0:28",
  },
  {
    id: "lista-espera",
    eyebrow: "Lista de espera automática · 26 segundos",
    title: "O estoque voltou. O cliente fica sabendo.",
    text: "O interesse é registrado no PDV e vira uma nova oportunidade quando o produto entra novamente no estoque.",
    source: "/marketing/corepet-demo-lista-espera-automatica.mp4",
    poster: "/marketing/corepet-demo-lista-espera-automatica-poster.jpg",
    shortTitle: "Lista de espera",
    duration: "0:26",
  },
  {
    id: "integracao",
    eyebrow: "Um único ecossistema · 26 segundos",
    title: "ERP, App e E-commerce trabalhando juntos.",
    text: "Cadastre uma vez, venda em todos os canais e mantenha pedidos e estoque em uma única operação.",
    source: "/marketing/corepet-demo-ecossistema-integrado.mp4",
    poster: "/marketing/corepet-demo-ecossistema-integrado-poster.jpg",
    shortTitle: "Tudo integrado",
    duration: "0:26",
  },
  {
    id: "resultado",
    eyebrow: "Gestão em tempo real · 27 segundos",
    title: "Cada venda mostra o que entrou, o que custou e o que virou lucro.",
    text: "Abra a venda, veja os produtos e acompanhe custos, lucro e margem de cada item em tempo real.",
    source: "/marketing/corepet-resultado-venda-por-venda.mp4",
    poster: "/marketing/corepet-resultado-venda-por-venda-poster.jpg",
    shortTitle: "Resultado da venda",
    duration: "0:27",
  },
  {
    id: "campanhas",
    eyebrow: "Motor de campanhas · 29 segundos",
    title: "Regras automáticas para trazer o cliente de volta.",
    text: "Retenção, cupons, validade e notificações do app trabalham no mesmo motor de campanhas.",
    source: "/marketing/corepet-demo-motor-campanhas.mp4",
    poster: "/marketing/corepet-demo-motor-campanhas-poster.jpg",
    shortTitle: "Campanhas automáticas",
    duration: "0:29",
  },
  {
    id: "entregas",
    eyebrow: "Rotas e custos · 30 segundos",
    title: "Controle a entrega sem perder margem no caminho.",
    text: "Rotas, entregadores, rastreio, custos e repasses ficam reunidos na mesma operação.",
    source: "/marketing/corepet-demo-entregas-rotas-custos.mp4",
    poster: "/marketing/corepet-demo-entregas-rotas-custos-poster.jpg",
    shortTitle: "Entregas e custos",
    duration: "0:30",
  },
];

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [activeDemoId, setActiveDemoId] = useState(systemDemoVideos[0].id);
  const activeDemo =
    systemDemoVideos.find((video) => video.id === activeDemoId) || systemDemoVideos[0];

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

    document.title = "CorePet | O sistema que trabalha para vender de novo";
    metaDescription.setAttribute(
      "content",
      "ERP, app e e-commerce para pet shops: recorrência inteligente, campanhas, estoque integrado, entregas e gestão do lucro em tempo real.",
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
    <div className="min-h-screen bg-white text-slate-950">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-violet-700 focus:shadow-xl"
      >
        Pular para o conteúdo principal
      </a>

      <nav className="fixed left-0 right-0 top-0 z-50 border-b border-white/10 bg-slate-950/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/landing" className="flex items-center gap-2.5 font-extrabold text-white">
            <img src="/brand/corepet/corepet-icon-64.png" alt="" className="h-8 w-8 rounded-lg" />
            CorePet
          </Link>

          <div className="hidden items-center gap-7 text-sm font-semibold text-slate-300 lg:flex">
            <a href="#venda-ativa" className="transition hover:text-white">
              Venda ativa
            </a>
            <a href="#plataforma" className="transition hover:text-white">
              Plataforma
            </a>
            <a href="#sistema-por-dentro" className="transition hover:text-white">
              Por dentro
            </a>
            <a href="#integracao" className="transition hover:text-white">
              Integração
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
              Quero uma demonstração
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </nav>

      <main id="main-content">
        <section
          className="relative isolate overflow-hidden bg-slate-950 pt-16 text-white"
          style={{
            backgroundImage: `linear-gradient(92deg, rgba(2,6,23,0.98) 0%, rgba(2,6,23,0.92) 48%, rgba(2,6,23,0.58) 100%), url(${heroImage})`,
            backgroundPosition: "center",
            backgroundSize: "cover",
          }}
        >
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_72%_30%,rgba(52,211,153,0.18),transparent_34%)]" />
          <div className="mx-auto grid min-h-[820px] max-w-7xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1.08fr_0.92fr]">
            <div className="max-w-3xl">
              <span className="inline-flex items-center gap-2 rounded-full border border-emerald-300/30 bg-emerald-300/10 px-4 py-2 text-sm font-bold text-emerald-200">
                <Sparkles className="h-4 w-4" />
                Tecnologia para o mercado pet vender todos os dias
              </span>
              <h1 className="mt-7 text-4xl font-black leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
                Sua loja ainda espera o cliente voltar?
              </h1>
              <p className="mt-7 max-w-2xl text-xl leading-8 text-slate-200 sm:text-2xl">
                O CorePet aprende o consumo, identifica a hora da recompra e trabalha para oferecer
                o produto certo pelo app.
              </p>
              <p className="mt-5 max-w-2xl text-lg font-bold leading-8 text-emerald-300">
                Seu ERP registra o que você vendeu. O CorePet trabalha para vender de novo.
              </p>

              <div className="mt-9 flex flex-col gap-3 sm:flex-row">
                <a
                  href={salesContactUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-6 py-3.5 font-extrabold text-slate-950 shadow-xl shadow-emerald-950/30 transition hover:-translate-y-0.5 hover:bg-emerald-300"
                >
                  Ver uma demonstração
                  <ArrowRight className="h-5 w-5" />
                </a>
                <a
                  href="#video-corepet"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/25 bg-white/10 px-6 py-3.5 font-bold text-white backdrop-blur transition hover:bg-white/15"
                >
                  <Play className="h-5 w-5 fill-current" />
                  Assistir em 30 segundos
                </a>
              </div>

              <div className="mt-10 flex flex-wrap gap-x-7 gap-y-3 text-sm font-semibold text-slate-300">
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" /> ERP completo
                </span>
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" /> App + e-commerce
                </span>
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" /> Tudo integrado
                </span>
              </div>
            </div>

            <div id="video-corepet" className="relative mx-auto w-full max-w-xl scroll-mt-24">
              <div className="absolute -inset-5 rounded-[2rem] bg-emerald-400/15 blur-3xl" />
              <div className="relative overflow-hidden rounded-[2rem] border border-white/15 bg-slate-900/85 p-3 shadow-2xl shadow-black/50 backdrop-blur">
                <div className="aspect-[9/16] overflow-hidden rounded-[1.45rem] bg-gradient-to-br from-violet-950 via-slate-950 to-emerald-950">
                  <video
                    className="h-full w-full object-cover"
                    controls
                    playsInline
                    preload="metadata"
                    poster="/marketing/corepet-vende-de-novo-poster.jpg"
                  >
                    <source src="/marketing/corepet-vende-de-novo-vertical.mp4" type="video/mp4" />
                    Seu navegador não suporta vídeo HTML5.
                  </video>
                </div>
              </div>
              <div className="relative mx-3 mt-4 rounded-2xl border border-white/10 bg-slate-950/95 p-4 shadow-xl">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">
                  Venda ativa
                </p>
                <p className="mt-1 font-bold text-white">A recompra acontece no momento certo.</p>
              </div>
            </div>
          </div>
        </section>

        <section
          id="venda-ativa"
          className="scroll-mt-16 border-b border-slate-200 bg-slate-50 py-20"
        >
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-sm font-black uppercase tracking-[0.16em] text-violet-700">
                Da venda passada à próxima venda
              </p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">
                Recorrência não é uma lista de lembretes. É uma estratégia de venda.
              </h2>
              <p className="mt-5 text-lg leading-8 text-slate-600">
                Ração, antipulgas, medicamentos com protocolo e outros produtos recorrentes deixam
                sinais. O CorePet usa esses sinais para ajudar a loja a agir antes de perder a
                recompra.
              </p>
            </div>

            <div className="mt-12 grid gap-4 lg:grid-cols-4">
              {activeSalesSteps.map(({ icon: Icon, label, text }, index) => (
                <article
                  key={label}
                  className="relative rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <span className="absolute right-5 top-5 text-sm font-black text-slate-300">
                    0{index + 1}
                  </span>
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="mt-5 text-lg font-extrabold">{label}</h3>
                  <p className="mt-2 leading-7 text-slate-600">{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="plataforma" className="scroll-mt-16 bg-white py-20">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <div className="max-w-3xl">
              <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-700">
                Uma plataforma, a operação inteira
              </p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">
                Mais do que organizar. Enxergar, decidir e vender.
              </h2>
            </div>

            <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {platformPillars.map(({ icon: Icon, title, text }) => (
                <article
                  key={title}
                  className="group rounded-2xl border border-slate-200 p-6 transition hover:-translate-y-1 hover:border-emerald-300 hover:shadow-xl"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-950 text-emerald-300 transition group-hover:bg-emerald-400 group-hover:text-slate-950">
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="mt-5 text-xl font-extrabold">{title}</h3>
                  <p className="mt-3 leading-7 text-slate-600">{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section
          id="sistema-por-dentro"
          className="scroll-mt-16 overflow-hidden border-y border-slate-200 bg-slate-100 py-20"
        >
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <div className="mx-auto max-w-4xl text-center">
              <p className="text-sm font-black uppercase tracking-[0.16em] text-violet-700">
                Veja o sistema por dentro
              </p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">
                Não é promessa. São telas reais trabalhando juntas.
              </h2>
              <p className="mt-5 text-lg leading-8 text-slate-600">
                Do pedido do cliente à análise do lucro, o CorePet conecta a experiência de compra
                com a operação e a gestão da empresa.
              </p>
            </div>

            <article className="mt-12 grid overflow-hidden rounded-[2rem] bg-slate-950 text-white shadow-2xl shadow-slate-900/20 lg:grid-cols-[0.72fr_1.28fr]">
              <div className="order-2 flex flex-col justify-center p-7 sm:p-10 lg:order-1 lg:p-12">
                <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-300">
                  {activeDemo.eyebrow}
                </p>
                <h3 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">
                  {activeDemo.title}
                </h3>
                <p className="mt-5 text-lg leading-8 text-slate-300">{activeDemo.text}</p>
                <div className="mt-7 flex items-center gap-3 text-sm font-bold text-emerald-200">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-400 text-slate-950">
                    <Play className="h-4 w-4 fill-current" />
                  </span>
                  Aperte o play e ouça com som
                </div>
              </div>

              <div className="order-1 flex items-center bg-black p-3 sm:p-5 lg:order-2">
                <video
                  key={activeDemo.source}
                  className="aspect-video w-full rounded-2xl bg-black object-contain shadow-2xl"
                  controls
                  playsInline
                  preload="metadata"
                  poster={activeDemo.poster}
                >
                  <source src={activeDemo.source} type="video/mp4" />
                  Seu navegador não suporta vídeo HTML5.
                </video>
              </div>
            </article>

            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {systemDemoVideos.map((video, index) => {
                const isActive = video.id === activeDemo.id;
                return (
                  <button
                    key={video.id}
                    type="button"
                    aria-pressed={isActive}
                    onClick={() => setActiveDemoId(video.id)}
                    className={`flex items-center gap-4 rounded-2xl border p-4 text-left transition ${
                      isActive
                        ? "border-slate-950 bg-slate-950 text-white shadow-xl"
                        : "border-slate-200 bg-white text-slate-900 hover:-translate-y-0.5 hover:border-emerald-400 hover:shadow-lg"
                    }`}
                  >
                    <span
                      className={`flex h-10 w-10 flex-none items-center justify-center rounded-xl text-sm font-black ${
                        isActive ? "bg-emerald-400 text-slate-950" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      0{index + 1}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-extrabold">{video.shortTitle}</span>
                      <span
                        className={`mt-1 block text-xs ${isActive ? "text-slate-300" : "text-slate-500"}`}
                      >
                        Narrado · {video.duration}
                      </span>
                    </span>
                    <Play
                      className={`h-4 w-4 flex-none ${isActive ? "text-emerald-300" : "text-slate-400"}`}
                    />
                  </button>
                );
              })}
            </div>

            <div className="mt-8 grid gap-6 lg:grid-cols-3">
              {screenHighlights.map((screen) => (
                <article
                  key={screen.title}
                  className={`group overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-2xl ${screen.wide ? "lg:col-span-2" : ""}`}
                >
                  <div
                    className={`relative overflow-hidden border-b border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-violet-950 p-4 ${screen.portrait ? "h-[34rem]" : "h-[22rem]"}`}
                  >
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_15%,rgba(52,211,153,0.18),transparent_30%)]" />
                    <img
                      src={screen.image}
                      alt={screen.alt}
                      loading="lazy"
                      className={`relative mx-auto h-full rounded-2xl object-contain shadow-2xl transition duration-500 group-hover:scale-[1.025] ${screen.portrait ? "w-auto" : "w-full"}`}
                    />
                  </div>
                  <div className="p-6 sm:p-7">
                    <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-700">
                      {screen.eyebrow}
                    </p>
                    <h3 className="mt-2 text-2xl font-black tracking-tight">{screen.title}</h3>
                    <p className="mt-3 leading-7 text-slate-600">{screen.text}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section
          id="integracao"
          className="scroll-mt-16 overflow-hidden bg-slate-950 py-20 text-white"
        >
          <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-violet-400/15 px-4 py-2 text-sm font-bold text-violet-200">
                <Boxes className="h-4 w-4" />
                Integração de verdade
              </span>
              <h2 className="mt-6 text-3xl font-black tracking-tight sm:text-5xl">
                O cliente compra 24 horas. A gestão continua no controle.
              </h2>
              <p className="mt-5 text-lg leading-8 text-slate-300">
                ERP, app e e-commerce compartilham produtos, pedidos e estoque. Uma venda feita em
                qualquer canal entra na mesma operação e atualiza as informações do gestor.
              </p>
              <p className="mt-4 text-sm font-semibold text-amber-200">
                Aplicativos em fase final de aprovação para publicação na App Store e Google Play.
              </p>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/5 p-7 backdrop-blur">
              <div className="flex items-center justify-between border-b border-white/10 pb-5">
                <div>
                  <p className="text-sm font-bold uppercase tracking-wider text-emerald-300">
                    Ecossistema CorePet
                  </p>
                  <p className="mt-1 text-xl font-extrabold">Tudo conversa com tudo</p>
                </div>
                <Clock3 className="h-9 w-9 text-emerald-300" />
              </div>
              <div className="mt-6 space-y-4">
                {unifiedChannels.map((item) => (
                  <div key={item} className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-5 w-5 flex-none text-emerald-400" />
                    <span className="font-semibold text-slate-200">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="bg-emerald-50 py-20">
          <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 px-4 sm:px-6 lg:flex-row lg:items-center">
            <div className="max-w-3xl">
              <p className="text-sm font-black uppercase tracking-[0.16em] text-emerald-700">
                A próxima venda pode começar agora
              </p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">
                Pare de apenas esperar. Coloque o CorePet para trabalhar.
              </h2>
              <p className="mt-5 text-lg leading-8 text-slate-600">
                Veja, em uma demonstração, como venda ativa, operação e gestão funcionam juntas no
                dia a dia de uma empresa do mercado pet.
              </p>
            </div>
            <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row lg:flex-col">
              <a
                href={salesContactUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-7 py-4 font-extrabold text-white transition hover:bg-slate-800"
              >
                Solicitar demonstração
                <ArrowRight className="h-5 w-5" />
              </a>
              <Link
                to="/register?plan=basico"
                className="inline-flex items-center justify-center rounded-xl border border-emerald-300 bg-white px-7 py-4 font-extrabold text-slate-800 transition hover:bg-emerald-100"
              >
                Começar 30 dias grátis
              </Link>
            </div>
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
