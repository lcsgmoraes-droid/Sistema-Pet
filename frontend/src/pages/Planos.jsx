import {
  ArrowRight,
  BarChart3,
  Check,
  Clock,
  CreditCard,
  Lock,
  Package,
  PawPrint,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Stethoscope,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";

const whatsappUrl =
  "https://wa.me/5518997401641?text=Ol%C3%A1!%20Quero%20entender%20o%20Plano%20B%C3%A1sico%20do%20Pet%20Shop%20Pro.";

const basicFeatures = [
  "Pessoas, clientes e pets",
  "Produtos, categorias, marcas e estoque",
  "Entrada, saída, lote e validade",
  "PDV completo, caixa, suprimento e sangria",
  "Histórico de vendas e visão por cliente",
  "Formas de pagamento e operadoras",
  "Usuários, permissões e LGPD operacional",
  "Relatórios essenciais para acompanhar a operação",
];

const basicOperations = [
  { icon: Users, title: "Atendimento", text: "Cadastre clientes e pets com histórico essencial." },
  { icon: Package, title: "Estoque", text: "Controle produtos, saldo, validade e movimentações." },
  { icon: ShoppingCart, title: "Venda", text: "Use PDV, caixa e pagamentos no fluxo de balcão." },
  { icon: BarChart3, title: "Gestão", text: "Acompanhe vendas, clientes e resultados básicos." },
];

const controlledModules = [
  {
    title: "Financeiro ERP",
    icon: BarChart3,
    description: "Contas a pagar, receber, DRE, conciliação e projeções.",
    status: "Adicional controlado",
  },
  {
    title: "Compras e integrações",
    icon: Package,
    description: "XML, Bling, fornecedores, marketplaces e automações.",
    status: "Em validação",
  },
  {
    title: "Veterinário",
    icon: Stethoscope,
    description: "Agenda clínica, prontuário, exames e relatórios veterinários.",
    status: "Módulo futuro",
  },
  {
    title: "Banho e Tosa",
    icon: Sparkles,
    description: "Agenda, serviços, pacotes e operação de atendimento.",
    status: "Módulo futuro",
  },
];

export default function Planos() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/landing" className="flex items-center gap-2 font-bold">
            <PawPrint className="h-6 w-6 text-emerald-600" />
            Pet Shop Pro
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <Link to="/login" className="font-semibold text-slate-600 hover:text-slate-900">
              Entrar
            </Link>
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md border border-slate-300 px-3 py-2 font-semibold text-slate-700 hover:bg-slate-100"
            >
              Falar com vendas
            </a>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-8 px-4 py-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
        <div>
          <span className="inline-flex items-center gap-2 rounded-md bg-emerald-100 px-3 py-1 text-sm font-bold text-emerald-800">
            <ShieldCheck className="h-4 w-4" />
            Plano validado para venda controlada
          </span>
          <h1 className="mt-5 max-w-3xl text-4xl font-extrabold tracking-normal text-slate-950 md:text-5xl">
            Comece pelo Básico e libere módulos avançados depois.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
            O Plano Básico concentra o que o pet shop precisa para operar: cadastro,
            estoque, PDV, caixa, vendas, usuários e gestão essencial.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              to="/register?plan=basico"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-950 px-5 py-3 font-bold text-white hover:bg-slate-800"
            >
              Selecionar Plano Básico
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/landing"
              className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-100"
            >
              Voltar para a landing
            </Link>
          </div>
        </div>

        <section className="rounded-lg border border-emerald-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-bold uppercase text-emerald-700">Plano Básico</p>
              <h2 className="mt-2 text-2xl font-extrabold text-slate-950">Operação essencial</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Contratação online nesta fase inicial. Pagamento e módulos adicionais podem ser
                tratados com a equipe comercial.
              </p>
            </div>
            <div className="rounded-md bg-emerald-50 p-3 text-emerald-700">
              <CreditCard className="h-6 w-6" />
            </div>
          </div>

          <ul className="mt-6 grid gap-3">
            {basicFeatures.map((feature) => (
              <li key={feature} className="flex items-start gap-3 text-sm text-slate-700">
                <Check className="mt-0.5 h-4 w-4 flex-none text-emerald-600" />
                <span>{feature}</span>
              </li>
            ))}
          </ul>

          <Link
            to="/register?plan=basico"
            className="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-md bg-emerald-500 px-4 py-3 font-bold text-slate-950 hover:bg-emerald-400"
          >
            Criar empresa no Básico
            <ArrowRight className="h-4 w-4" />
          </Link>
        </section>
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
            <div>
              <h2 className="text-2xl font-extrabold text-slate-950">O que o cliente faz primeiro</h2>
              <p className="mt-2 max-w-2xl text-slate-600">
                Esses são os blocos do uso inicial que precisam estar claros para quem contrata.
              </p>
            </div>
            <span className="inline-flex w-fit items-center gap-2 rounded-md bg-slate-100 px-3 py-2 text-sm font-bold text-slate-700">
              <Clock className="h-4 w-4" />
              Implantação enxuta
            </span>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-4">
            {basicOperations.map(({ icon: Icon, title, text }) => (
              <article key={title} className="rounded-lg border border-slate-200 bg-slate-50 p-5">
                <Icon className="h-6 w-6 text-violet-700" />
                <h3 className="mt-4 font-bold text-slate-950">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-slate-950">
        <div className="mx-auto max-w-6xl px-4 py-12 text-white">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
            <div>
              <h2 className="text-2xl font-extrabold">Módulos fora do Básico</h2>
              <p className="mt-2 max-w-2xl text-slate-300">
                Eles continuam bloqueados por plano para proteger o cliente de fluxos ainda em
                validação ou que precisam de contratação específica.
              </p>
            </div>
            <span className="inline-flex w-fit items-center gap-2 rounded-md bg-amber-300/15 px-3 py-2 text-sm font-bold text-amber-200">
              <Lock className="h-4 w-4" />
              Liberação controlada
            </span>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {controlledModules.map(({ icon: Icon, title, description, status }) => (
              <article key={title} className="rounded-lg border border-white/10 bg-white/5 p-5">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-white/10 text-amber-200">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-4 font-bold text-white">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-300">{description}</p>
                <p className="mt-4 text-xs font-bold uppercase text-slate-400">{status}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
