import { useState } from "react";
import {
  FiActivity,
  FiArrowLeft,
  FiCheck,
  FiCpu,
  FiGrid,
  FiPackage,
  FiShoppingBag,
} from "react-icons/fi";
import BlingIntegracao from "./BlingIntegracao";
import EcommerceAIIntegracaoCard from "./EcommerceAIIntegracaoCard";
import IfoodIntegracaoCard from "./IfoodIntegracaoCard";
import OpenAIIntegracaoCard from "./OpenAIIntegracaoCard";

const INTEGRACOES = [
  {
    id: "bling",
    nome: "Bling v3",
    categoria: "ERP e estoque",
    descricao: "Sincronize produtos, estoque e pedidos com a sua conta do Bling.",
    recursos: [
      "Sincronização de produtos e estoque",
      "Importação e acompanhamento de pedidos",
      "Renovação automática da conexão",
    ],
    icon: FiPackage,
    cardClass:
      "border-emerald-200 bg-emerald-50/70 hover:border-emerald-300 hover:bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/20 dark:hover:border-emerald-700",
    iconClass: "bg-emerald-600 text-white",
    linkClass: "text-emerald-700 dark:text-emerald-300",
  },
  {
    id: "ifood",
    nome: "iFood",
    categoria: "Marketplace",
    descricao: "Prepare produtos, preços e estoque do CorePet para vender no iFood.",
    recursos: [
      "Catálogo gerado a partir do ERP",
      "Validação de EAN, preço e estoque",
      "Simulação segura antes da publicação",
    ],
    icon: FiShoppingBag,
    cardClass:
      "border-red-200 bg-red-50/70 hover:border-red-300 hover:bg-red-50 dark:border-red-900 dark:bg-red-950/20 dark:hover:border-red-800",
    iconClass: "bg-red-600 text-white",
    linkClass: "text-red-700 dark:text-red-300",
  },
  {
    id: "ecommerceai",
    nome: "EcommerceAI",
    categoria: "Análise comercial",
    descricao: "Conecte vendas, catálogo e indicadores do CorePet às análises do EcommerceAI.",
    recursos: [
      "Leitura segura do catálogo",
      "Recebimento de indicadores de vendas",
      "Histórico dos eventos processados",
    ],
    icon: FiActivity,
    cardClass:
      "border-cyan-200 bg-cyan-50/70 hover:border-cyan-300 hover:bg-cyan-50 dark:border-cyan-800 dark:bg-cyan-950/20 dark:hover:border-cyan-700",
    iconClass: "bg-cyan-700 text-white",
    linkClass: "text-cyan-700 dark:text-cyan-300",
  },
  {
    id: "openai",
    nome: "OpenAI",
    categoria: "Exames veterinários",
    descricao: "Habilite o apoio de IA para interpretar PDFs e imagens de exames veterinários.",
    recursos: [
      "Leitura de hemograma e bioquímica",
      "Análise de PDF, raio-x e ultrassom",
      "Alertas e apoio à interpretação",
    ],
    icon: FiCpu,
    cardClass:
      "border-indigo-200 bg-indigo-50/70 hover:border-indigo-300 hover:bg-indigo-50 dark:border-indigo-800 dark:bg-indigo-950/20 dark:hover:border-indigo-700",
    iconClass: "bg-indigo-600 text-white",
    linkClass: "text-indigo-700 dark:text-indigo-300",
  },
];

const PAINEIS = {
  bling: BlingIntegracao,
  ifood: IfoodIntegracaoCard,
  ecommerceai: EcommerceAIIntegracaoCard,
  openai: OpenAIIntegracaoCard,
};

function integracaoInicial() {
  const params = new URLSearchParams(globalThis.location.search);
  return params.has("ecommerceai_request") ? "ecommerceai" : null;
}

export default function Integracoes() {
  const [selecionada, setSelecionada] = useState(integracaoInicial);
  const PainelSelecionado = selecionada ? PAINEIS[selecionada] : null;

  if (PainelSelecionado) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
        <button
          type="button"
          onClick={() => setSelecionada(null)}
          className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-blue-300 dark:hover:bg-blue-950/40"
        >
          <FiArrowLeft aria-hidden="true" />
          Voltar às integrações
        </button>
        <PainelSelecionado />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 shadow-sm dark:bg-blue-500/10 dark:text-blue-200">
          <FiGrid className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-950 dark:text-slate-100">Integrações</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Escolha uma integração para consultar, conectar ou alterar sua configuração.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {INTEGRACOES.map((integracao) => {
          const Icon = integracao.icon;

          return (
            <button
              key={integracao.id}
              type="button"
              onClick={() => setSelecionada(integracao.id)}
              className={`group flex h-full flex-col rounded-2xl border p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${integracao.cardClass}`}
              aria-label={`Abrir integração ${integracao.nome}`}
            >
              <div className="flex w-full items-start justify-between gap-3">
                <div className={`rounded-xl p-3 shadow-sm ${integracao.iconClass}`}>
                  <Icon className="h-6 w-6" aria-hidden="true" />
                </div>
                <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-slate-600 shadow-sm dark:bg-slate-900/70 dark:text-slate-300">
                  {integracao.categoria}
                </span>
              </div>

              <h2 className="mt-5 text-lg font-semibold text-slate-950 dark:text-slate-100">
                {integracao.nome}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {integracao.descricao}
              </p>

              <ul className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                {integracao.recursos.map((recurso) => (
                  <li key={recurso} className="flex items-start gap-2">
                    <FiCheck
                      className={`mt-0.5 h-4 w-4 shrink-0 ${integracao.linkClass}`}
                      aria-hidden="true"
                    />
                    <span>{recurso}</span>
                  </li>
                ))}
              </ul>

              <span
                className={`mt-6 inline-flex items-center gap-2 text-sm font-semibold ${integracao.linkClass}`}
              >
                Abrir integração
                <span aria-hidden="true" className="transition group-hover:translate-x-1">
                  →
                </span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
        As integrações funcionam de forma independente. Abra somente a que deseja configurar.
      </div>
    </div>
  );
}
