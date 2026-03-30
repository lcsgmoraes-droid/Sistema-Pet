import {
  ArrowRight,
  BarChart3,
  Bell,
  Brain,
  Building2,
  ChevronRight,
  CreditCard,
  FileText,
  MessageCircle,
  Package,
  PawPrint,
  ShoppingCart,
  Smartphone,
  Star,
} from "lucide-react";
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const features = [
  {
    icon: <Package className="w-6 h-6" />,
    title: "Gestão Completa",
    desc: "Estoque, PDV, clientes, pets e histórico veterinário em um só lugar.",
  },
  {
    icon: <ShoppingCart className="w-6 h-6" />,
    title: "E-commerce Integrado",
    desc: "Loja própria conectada com Bling, Mercado Livre e outros marketplaces.",
  },
  {
    icon: <Smartphone className="w-6 h-6" />,
    title: "APP Mobile",
    desc: "Clientes acompanham vacinas, consultas e histórico do pet pelo celular.",
  },
  {
    icon: <Brain className="w-6 h-6" />,
    title: "IA Integrada",
    desc: "Calculadora de ração com IA que indica o produto ideal por peso, raça e idade.",
  },
  {
    icon: <Bell className="w-6 h-6" />,
    title: "Automação de Pedidos",
    desc: "Pedidos ao fornecedor automáticos com controle de estoque em tempo real.",
  },
  {
    icon: <CreditCard className="w-6 h-6" />,
    title: "Pagamentos Stone",
    desc: "Integração nativa com a Stone para pagamentos diretamente no PDV.",
  },
  {
    icon: <MessageCircle className="w-6 h-6" />,
    title: "Campanhas Automáticas",
    desc: "Lembretes e campanhas automáticas via WhatsApp e e-mail.",
  },
  {
    icon: <FileText className="w-6 h-6" />,
    title: "Notas Fiscais",
    desc: "Emissão de NF-e integrada, simples e sem complicação.",
  },
  {
    icon: <BarChart3 className="w-6 h-6" />,
    title: "Dashboard Gerencial",
    desc: "Relatórios de vendas, estoque e financeiro com gráficos em tempo real.",
  },
  {
    icon: <Building2 className="w-6 h-6" />,
    title: "Multi-loja",
    desc: "Gerencie várias unidades com uma única conta e controle centralizado.",
  },
];

const steps = [
  {
    num: "01",
    title: "Solicite uma demo",
    desc: "Fale com nossa equipe pelo WhatsApp e agende uma apresentação gratuita.",
  },
  {
    num: "02",
    title: "Configure seu pet shop",
    desc: "Cadastramos sua loja, produtos e equipe em menos de 24 horas.",
  },
  {
    num: "03",
    title: "Comece a usar",
    desc: "Sistema 100% online, sem instalação. Acesse de qualquer dispositivo.",
  },
];

const testimonials = [
  {
    name: "Carla Souza",
    role: "Pet Shop Patinhas Felizes",
    text: "Antes eu controlava tudo em planilha. Hoje tenho estoque, vendas e IA na mesma tela. Economizo horas por semana.",
    stars: 5,
  },
  {
    name: "Marcos Lima",
    role: "Rede PetCenter (3 lojas)",
    text: "O módulo multi-loja salvou minha operação. Consigo ver tudo das três unidades em tempo real sem precisar ligar para ninguém.",
    stars: 5,
  },
  {
    name: "Ana Rodrigues",
    role: "Clínica & Pet Shop Amigo Animal",
    text: "A integração do e-commerce com o estoque físico foi o que me convenceu. Nunca mais vendi produto zerado.",
    stars: 5,
  },
];

function StarRating({ count }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: count }).map((_, i) => (
        <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
      ))}
    </div>
  );
}

export default function LandingPage() {
  const whatsappUrl =
    "https://wa.me/5518997401641?text=Olá!%20Quero%20conhecer%20o%20Pet%20Shop%20Pro.";
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  // Se já está logado, vai direto para o sistema
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/lembretes', { replace: true });
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

    document.title =
      "Pet Shop Pro | ERP para pet shop com PDV, estoque, NF, Bling e veterinario";
    metaDescription.setAttribute(
      "content",
      "Sistema de gestao para pet shop com PDV, estoque, notas fiscais, integracao com Bling, e-commerce, entregas e modulo veterinario."
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
    <div className="min-h-screen bg-white font-sans text-gray-800">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-purple-700 focus:shadow-lg"
      >
        Pular para o conteudo principal
      </a>

      {/* ============ NAVBAR ============ */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur border-b border-gray-100 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PawPrint className="w-7 h-7 text-purple-600" />
            <span className="text-xl font-bold text-gray-900">
              Pet Shop <span className="text-purple-600">Pro</span>
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
            <a
              href="#funcionalidades"
              className="hover:text-purple-600 transition-colors"
            >
              Funcionalidades
            </a>
            <a
              href="#como-funciona"
              className="hover:text-purple-600 transition-colors"
            >
              Como funciona
            </a>
            <a
              href="#depoimentos"
              className="hover:text-purple-600 transition-colors"
            >
              Depoimentos
            </a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="hidden md:inline-flex items-center gap-1.5 text-sm font-semibold text-purple-700 bg-purple-100 hover:bg-purple-200 px-4 py-2 rounded-lg transition-colors border border-purple-200"
            >
              🔐 Já sou cliente
            </Link>
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              Falar com vendas
            </a>
          </div>
        </div>
      </nav>

      <main id="main-content">
      {/* ============ HERO ============ */}
      <section className="pt-16 min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-purple-900 flex items-center">
        <div className="max-w-6xl mx-auto px-4 py-24 grid md:grid-cols-2 gap-12 items-center">
          {/* Texto */}
          <div className="text-white">
            <span className="inline-flex items-center gap-2 bg-white/20 text-white text-xs font-semibold px-3 py-1 rounded-full mb-6 backdrop-blur">
              <Brain className="w-3.5 h-3.5" />
              Gestão + E-commerce + APP + IA
            </span>
            <h1 className="text-4xl md:text-5xl font-extrabold leading-tight mb-6">
              Tudo que seu <span className="text-yellow-300">pet shop</span>{" "}
              precisa, em um único lugar
            </h1>
            <p className="text-lg text-purple-100 mb-8 leading-relaxed">
              Do pedido ao fornecedor até a contabilidade final — com e-commerce
              próprio, app mobile para clientes e inteligência artificial
              integrada.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 bg-yellow-400 hover:bg-yellow-300 text-gray-900 font-bold px-6 py-3 rounded-xl transition-colors shadow-lg"
              >
                <MessageCircle className="w-5 h-5" />
                Quero uma demonstração
              </a>
              <a
                href="#funcionalidades"
                className="inline-flex items-center justify-center gap-2 bg-white/20 hover:bg-white/30 text-white font-semibold px-6 py-3 rounded-xl transition-colors backdrop-blur"
              >
                Ver funcionalidades
                <ChevronRight className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Card de destaque */}
          <div className="hidden md:block">
            <div className="bg-white/10 backdrop-blur rounded-2xl p-6 border border-white/20">
              <div className="grid grid-cols-2 gap-4">
                {[
                  {
                    icon: <Package className="w-5 h-5 text-yellow-300" />,
                    label: "Estoque inteligente",
                  },
                  {
                    icon: <ShoppingCart className="w-5 h-5 text-yellow-300" />,
                    label: "E-commerce",
                  },
                  {
                    icon: <Brain className="w-5 h-5 text-yellow-300" />,
                    label: "IA integrada",
                  },
                  {
                    icon: <Smartphone className="w-5 h-5 text-yellow-300" />,
                    label: "APP mobile",
                  },
                  {
                    icon: <BarChart3 className="w-5 h-5 text-yellow-300" />,
                    label: "Relatórios",
                  },
                  {
                    icon: <CreditCard className="w-5 h-5 text-yellow-300" />,
                    label: "PDV & Stone",
                  },
                ].map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 bg-white/10 rounded-xl px-4 py-3"
                  >
                    {item.icon}
                    <span className="text-white text-sm font-medium">
                      {item.label}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-4 bg-white/10 rounded-xl p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-8 h-8 bg-yellow-400 rounded-full flex items-center justify-center">
                    <PawPrint className="w-4 h-4 text-gray-900" />
                  </div>
                  <div>
                    <p className="text-white font-semibold text-sm">
                      Pet Shop Pro
                    </p>
                    <p className="text-purple-200 text-xs">
                      Sistema completo de gestão
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 mt-2">
                  <StarRating count={5} />
                  <span className="text-purple-200 text-xs ml-1">
                    Avaliação dos clientes
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ NÚMEROS ============ */}
      <section className="bg-purple-50 py-12">
        <div className="max-w-6xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { num: "100%", label: "Online e sem instalação" },
            { num: "10+", label: "Módulos integrados" },
            { num: "24h", label: "Onboarding ultrarrápido" },
            { num: "IA", label: "Inteligência artificial nativa" },
          ].map((item, i) => (
            <div key={i} className="p-4">
              <div className="text-3xl font-extrabold text-purple-600 mb-1">
                {item.num}
              </div>
              <div className="text-sm text-gray-600">{item.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ============ FUNCIONALIDADES ============ */}
      <section id="funcionalidades" className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-14">
            <span className="text-purple-600 font-semibold text-sm uppercase tracking-wide">
              O que você ganha
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold text-gray-900 mt-2 mb-4">
              Um sistema feito para pet shop de verdade
            </h2>
            <p className="text-gray-500 max-w-xl mx-auto">
              Tudo pensado para quem vende ração, faz banho e tosa, atende
              clientes e ainda precisa cuidar do estoque no fim do dia.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div
                key={i}
                className="group p-6 rounded-2xl border border-gray-100 hover:border-purple-200 hover:shadow-lg hover:shadow-purple-50 transition-all"
              >
                <div className="w-12 h-12 bg-purple-100 group-hover:bg-purple-600 rounded-xl flex items-center justify-center mb-4 transition-colors text-purple-600 group-hover:text-white">
                  {f.icon}
                </div>
                <h3 className="font-bold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ COMO FUNCIONA ============ */}
      <section
        id="como-funciona"
        className="py-20 bg-gradient-to-br from-gray-50 to-purple-50"
      >
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-14">
            <span className="text-purple-600 font-semibold text-sm uppercase tracking-wide">
              Simples e rápido
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold text-gray-900 mt-2 mb-4">
              Como contratar
            </h2>
            <p className="text-gray-500 max-w-md mx-auto">
              Em 3 passos você já está usando o sistema.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((s, i) => (
              <div key={i} className="relative">
                <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 h-full">
                  <span className="text-5xl font-extrabold text-purple-100">
                    {s.num}
                  </span>
                  <h3 className="text-lg font-bold text-gray-900 mt-3 mb-2">
                    {s.title}
                  </h3>
                  <p className="text-sm text-gray-500 leading-relaxed">
                    {s.desc}
                  </p>
                </div>
                {i < steps.length - 1 && (
                  <div className="hidden md:flex absolute top-1/2 -right-4 z-10 w-8 h-8 bg-purple-600 rounded-full items-center justify-center shadow-md">
                    <ArrowRight className="w-4 h-4 text-white" />
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="text-center mt-12">
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-bold px-8 py-4 rounded-xl transition-colors shadow-lg text-lg"
            >
              <MessageCircle className="w-5 h-5" />
              Solicitar demonstração grátis
            </a>
            <p className="text-gray-400 text-sm mt-3">
              Sem compromisso. Respondemos em minutos.
            </p>
          </div>
        </div>
      </section>

      {/* ============ DEPOIMENTOS ============ */}
      <section id="depoimentos" className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-14">
            <span className="text-purple-600 font-semibold text-sm uppercase tracking-wide">
              Quem já usa
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold text-gray-900 mt-2">
              Pet shops que transformaram a gestão
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((t, i) => (
              <div
                key={i}
                className="bg-gray-50 rounded-2xl p-6 border border-gray-100"
              >
                <StarRating count={t.stars} />
                <p className="text-gray-700 mt-4 mb-6 text-sm leading-relaxed">
                  "{t.text}"
                </p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                    {t.name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900 text-sm">
                      {t.name}
                    </div>
                    <div className="text-gray-500 text-xs">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ CTA FINAL ============ */}
      <section className="py-20 bg-gradient-to-br from-purple-600 via-purple-700 to-purple-900 text-white">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-full mb-6">
            <PawPrint className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold mb-4">
            Pronto para transformar seu pet shop?
          </h2>
          <p className="text-purple-200 mb-8 text-lg">
            Fale com nossa equipe agora. Demo gratuita, sem burocracia.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 bg-yellow-400 hover:bg-yellow-300 text-gray-900 font-bold px-8 py-4 rounded-xl transition-colors shadow-lg text-lg"
            >
              <MessageCircle className="w-5 h-5" />
              Falar pelo WhatsApp
            </a>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 bg-white/20 hover:bg-white/30 text-white font-semibold px-8 py-4 rounded-xl transition-colors backdrop-blur text-lg"
            >
              Já sou cliente — Entrar
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      </main>

      {/* ============ FOOTER ============ */}
      <footer className="bg-gray-900 text-gray-400 py-10">
        <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <PawPrint className="w-5 h-5 text-purple-400" />
            <span className="text-white font-bold">Pet Shop Pro</span>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <a
              href="#funcionalidades"
              className="hover:text-white transition-colors"
            >
              Funcionalidades
            </a>
            <a
              href="#como-funciona"
              className="hover:text-white transition-colors"
            >
              Como funciona
            </a>
            <Link to="/login" className="hover:text-white transition-colors">
              Entrar
            </Link>
          </div>
          <p className="text-xs text-center md:text-right">
            © {new Date().getFullYear()} Pet Shop Pro · Todos os direitos
            reservados
          </p>
        </div>
      </footer>
    </div>
  );
}
