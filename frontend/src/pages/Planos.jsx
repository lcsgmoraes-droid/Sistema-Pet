import {
  ArrowRight,
  BarChart3,
  Check,
  CreditCard,
  Lock,
  Package,
  PawPrint,
  ShoppingCart,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import { Link } from "react-router-dom";

const whatsappUrl =
  "https://wa.me/5518997401641?text=Ol%C3%A1!%20Quero%20entender%20os%20planos%20do%20Pet%20Shop%20Pro.";

const basicFeatures = [
  "Pessoas, clientes e pets",
  "Produtos, categorias e estoque",
  "PDV completo e controle de caixa",
  "Histórico de vendas e cliente",
  "Relatórios gerenciais de vendas",
  "Formas de pagamento e operadoras",
  "Usuários, permissões e LGPD operacional",
  "Templates iniciais copiados para a empresa",
];

const futurePlans = [
  {
    title: "Compras e XML",
    icon: <Package className="h-5 w-5" />,
    description: "Fornecedor, sugestão de compra, pedidos e entrada por XML.",
    status: "Adicional em validação",
  },
  {
    title: "Financeiro ERP",
    icon: <BarChart3 className="h-5 w-5" />,
    description: "Contas a pagar, receber, DRE, conciliação e projeções.",
    status: "Beta controlado",
  },
  {
    title: "Veterinário",
    icon: <Stethoscope className="h-5 w-5" />,
    description: "Agenda, prontuário, consultas, exames e relatórios clínicos.",
    status: "Vertical futura",
  },
  {
    title: "Banho e Tosa",
    icon: <Sparkles className="h-5 w-5" />,
    description: "Agenda, serviços, pacotes, fila e jornada de atendimento.",
    status: "Vertical futura",
  },
];

export default function Planos() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/landing" className="flex items-center gap-2 font-bold">
            <PawPrint className="h-6 w-6 text-violet-600" />
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

      <section className="mx-auto grid max-w-6xl gap-10 px-4 py-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
        <div>
          <span className="inline-flex items-center gap-2 rounded-md bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
            <ShoppingCart className="h-4 w-4" />
            Plano inicial para pet shop
          </span>
          <h1 className="mt-5 max-w-3xl text-4xl font-bold tracking-normal text-slate-950 md:text-5xl">
            Comece pelo módulo básico, com a operação do dia a dia pronta.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
            O plano básico libera cadastro, produtos, estoque, PDV, vendas e visão gerencial.
            Os módulos maiores ficam separados para crescer sem misturar beta com operação essencial.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              to="/register?plan=basico"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-violet-600 px-5 py-3 font-bold text-white hover:bg-violet-700"
            >
              Selecionar Plano Básico
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-100"
            >
              Tirar dúvidas
            </a>
          </div>
        </div>

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase text-violet-700">Plano Básico</p>
              <h2 className="mt-2 text-2xl font-bold text-slate-950">Operação essencial</h2>
              <p className="mt-2 text-sm text-slate-500">Sem pagamento online nesta fase de teste comercial.</p>
            </div>
            <div className="rounded-md bg-violet-50 p-3 text-violet-700">
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
            className="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 py-3 font-bold text-white hover:bg-slate-800"
          >
            Criar conta no Básico
            <ArrowRight className="h-4 w-4" />
          </Link>
        </section>
      </section>

      <section className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
            <div>
              <h2 className="text-2xl font-bold text-slate-950">Módulos para liberar depois</h2>
              <p className="mt-2 max-w-2xl text-slate-600">
                Eles ficam bloqueados por plano para proteger o cliente do que ainda está em validação.
              </p>
            </div>
            <span className="inline-flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">
              <Lock className="h-4 w-4" />
              Liberação controlada
            </span>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {futurePlans.map((plan) => (
              <article key={plan.title} className="rounded-lg border border-slate-200 bg-slate-50 p-5">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-white text-slate-700 shadow-sm">
                  {plan.icon}
                </div>
                <h3 className="mt-4 font-bold text-slate-950">{plan.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{plan.description}</p>
                <p className="mt-4 text-xs font-bold uppercase text-slate-500">{plan.status}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
