/**
 * Ajuda.jsx — Página central de ajuda e planos do CorePet.
 * Linguagem simples, foco em benefício para o usuário.
 */
import { useState } from "react";
import {
  FiBookOpen,
  FiCheckCircle,
  FiCheckSquare,
  FiChevronDown,
  FiChevronUp,
  FiCreditCard,
  FiGift,
  FiGlobe,
  FiMessageCircle,
  FiSmartphone,
  FiStar,
  FiTruck,
  FiZap,
} from "react-icons/fi";
import { Link } from "react-router-dom";
import { MODULOS_INFO } from "../contexts/ModulosContext";
import CentralAjuda from "./CentralAjuda";
import IntroducaoGuiada from "./IntroducaoGuiada";

const WHATSAPP_NUMERO = "5518997401641";

/* Ícones por módulo */
const ICONES_MODULO = {
  compras: FiCreditCard,
  financeiro_erp: FiCreditCard,
  comissoes: FiCreditCard,
  veterinario: FiZap,
  banho_tosa: FiZap,
  fiscal: FiCreditCard,
  bling: FiZap,
  integracoes: FiZap,
  rh: FiZap,
  ia_avancada: FiZap,
  entregas: FiTruck,
  campanhas: FiGift,
  whatsapp: FiMessageCircle,
  ecommerce: FiGlobe,
  app_mobile: FiSmartphone,
  marketplaces: FiZap,
};

/* FAQ — dúvidas comuns */
const FAQS = [
  {
    pergunta: "Como faco para contratar?",
    resposta:
      "O Plano Basico e a oferta inicial. A ativacao paga acontece com atendimento assistido e registro manual pelo administrativo.",
  },
  {
    pergunta: "Posso testar antes de pagar?",
    resposta: "Sim. Novas empresas comecam com 30 dias gratis do Plano Basico.",
  },
  {
    pergunta: "Como funciona o pagamento?",
    resposta:
      "Nesta etapa, o pagamento e feito fora do sistema. Depois da confirmacao, o acesso e ativado manualmente.",
  },
  {
    pergunta: "Os modulos extras entram no trial?",
    resposta:
      "Nao automaticamente. Modulos extras ficam como Beta acompanhado e podem ser solicitados caso a caso.",
  },
  {
    pergunta: "Se eu cancelar, perco os dados?",
    resposta:
      "Nao. Seus dados ficam salvos. Se reativar o acesso no futuro, tudo continua no tenant.",
  },
  {
    pergunta: "Tenho duvidas sobre um modulo especifico. O que faco?",
    resposta:
      "Fale direto pelo WhatsApp. A gente explica o funcionamento e avalia se faz sentido liberar como Beta acompanhado.",
  },
];

const ORDEM_MODULOS = [
  "compras",
  "financeiro_erp",
  "veterinario",
  "banho_tosa",
  "fiscal",
  "campanhas",
  "entregas",
  "whatsapp",
  "ecommerce",
  "comissoes",
  "app_mobile",
  "marketplaces",
];

/* Componente de card individual de módulo */
const CardModulo = ({ moduloKey }) => {
  const info = MODULOS_INFO[moduloKey];
  if (!info) return null;

  const Icone = ICONES_MODULO[moduloKey] || FiZap;
  const msgWhatsApp = encodeURIComponent(
    `Olá! Quero saber mais sobre o módulo ${info.nome} do CorePet. Pode me ajudar?`,
  );
  const msgContratar = encodeURIComponent(
    `Ola! Quero solicitar acesso Beta ao modulo ${info.nome} do CorePet.`,
  );

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow p-6 flex flex-col">
      {/* Cabeçalho do card */}
      <div className="flex items-start gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center flex-shrink-0">
          <Icone className="w-5 h-5 text-indigo-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-base font-bold text-gray-900">{info.nome}</h3>
          <p className="text-sm text-gray-500 mt-0.5">{info.descricao}</p>
        </div>
      </div>

      {/* Lista de recursos */}
      <ul className="space-y-2 flex-1 mb-5">
        {info.recursos.map((recurso) => (
          <li key={recurso} className="flex items-start gap-2">
            <FiCheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
            <span className="text-sm text-gray-700">{recurso}</span>
          </li>
        ))}
      </ul>

      {/* Preço e CTAs */}
      <div className="border-t border-gray-100 pt-4">
        <div className="flex items-end justify-between mb-4">
          <div>
            <p className="text-xs text-gray-400">tipo de acesso</p>
            <p className="text-2xl font-bold text-gray-900">
              Beta
              <span className="text-sm font-normal text-gray-400"> acompanhado</span>
            </p>
          </div>
          <span className="text-xs text-amber-700 font-semibold bg-amber-50 px-2 py-1 rounded-full">
            Manual
          </span>
        </div>

        <a
          href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgContratar}`}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-center gap-2 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 px-4 rounded-xl transition-colors text-sm"
        >
          <FiCreditCard className="w-4 h-4" />
          Solicitar acesso Beta
        </a>
        <a
          href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgWhatsApp}`}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-center gap-2 w-full mt-2 text-green-700 hover:text-green-800 text-sm font-medium py-2 px-4 rounded-xl border border-green-200 hover:bg-green-50 transition-colors"
        >
          <FiMessageCircle className="w-4 h-4" />
          Tirar dúvidas
        </a>
      </div>
    </div>
  );
};

/* Componente de FAQ accordion */
const ItemFAQ = ({ pergunta, resposta }) => {
  const [aberto, setAberto] = useState(false);

  return (
    <div className="border border-gray-100 rounded-xl overflow-hidden">
      <button
        onClick={() => setAberto(!aberto)}
        className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-semibold text-gray-800">{pergunta}</span>
        {aberto ? (
          <FiChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
        ) : (
          <FiChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
        )}
      </button>
      {aberto && (
        <div className="px-5 pb-4">
          <p className="text-sm text-gray-600 leading-relaxed">{resposta}</p>
        </div>
      )}
    </div>
  );
};

/* --------------------------------------------------------
   Página principal
-------------------------------------------------------- */
const Ajuda = () => {
  const [aba, setAba] = useState("planos");
  const msgGeral = encodeURIComponent("Olá! Tenho dúvidas sobre os planos do CorePet.");

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 text-white py-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-indigo-200 text-sm font-medium mb-2">Ajuda e Planos</p>
          <h1 className="text-3xl font-bold mb-3">
            {aba === "introducao"
              ? "Preparando seu sistema"
              : aba === "central"
                ? "Como usar o CorePet"
                : "Módulos Beta do CorePet"}
          </h1>
          <p className="text-indigo-100 text-base max-w-xl mx-auto">
            {aba === "introducao"
              ? "Checklist guiado, com sequencia recomendada, para configurar o sistema com seguranca do inicio ao fim."
              : aba === "central"
                ? "Aprenda a usar cada funcionalidade do sistema. Pesquise por dúvidas, navegue por módulo ou leia o passo a passo."
                : "O Plano Básico fica no centro da oferta. Os recursos avançados aparecem como Beta acompanhado para você conhecer e pedir liberação quando fizer sentido."}
          </p>
          <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
            <a
              href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgGeral}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-2 bg-white text-indigo-700 font-semibold px-6 py-3 rounded-xl hover:bg-indigo-50 transition-colors"
            >
              <FiMessageCircle className="w-4 h-4" />
              Falar com o suporte
            </a>
            <Link
              to="/dashboard"
              className="inline-flex items-center justify-center gap-2 border border-white/30 text-white font-medium px-6 py-3 rounded-xl hover:bg-white/10 transition-colors"
            >
              ← Voltar ao sistema
            </Link>
          </div>
        </div>
      </div>

      {/* Abas de navegação */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4">
          <nav className="flex gap-1 overflow-x-auto">
            <button
              onClick={() => setAba("planos")}
              className={`flex items-center gap-2 px-5 py-4 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
                aba === "planos"
                  ? "border-indigo-600 text-indigo-700"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <FiStar className="w-4 h-4" />
              Módulos Beta
            </button>
            <button
              onClick={() => setAba("introducao")}
              className={`flex items-center gap-2 px-5 py-4 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
                aba === "introducao"
                  ? "border-indigo-600 text-indigo-700"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <FiCheckSquare className="w-4 h-4" />
              Introdução Guiada
            </button>
            <button
              onClick={() => setAba("central")}
              className={`flex items-center gap-2 px-5 py-4 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
                aba === "central"
                  ? "border-indigo-600 text-indigo-700"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <FiBookOpen className="w-4 h-4" />
              Central de Ajuda
            </button>
          </nav>
        </div>
      </div>

      {/* Conteúdo da aba Central de Ajuda */}
      {aba === "central" && <CentralAjuda />}

      {/* Conteudo da aba Introducao Guiada */}
      {aba === "introducao" && <IntroducaoGuiada />}

      {/* Conteúdo da aba Módulos Beta */}
      {aba === "planos" && (
        <div className="max-w-5xl mx-auto px-4 py-10">
          {/* Seção: módulos base (inclusos sem custo) */}
          <div className="mb-10">
            <div className="bg-green-50 border border-green-200 rounded-2xl p-5 flex flex-col sm:flex-row gap-4 items-start">
              <FiCheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-green-800 text-base">
                  Já inclusos no seu plano — sem custo extra
                </p>
                <p className="text-sm text-green-700 mt-1">
                  PDV completo, histórico de vendas, financeiro de vendas, Pessoas, Pets, Produtos,
                  Estoque, Usuários, Cadastros essenciais, Lembretes, Calculadora de Ração e
                  Configurações essenciais já estão liberados para você usar hoje.
                </p>
              </div>
            </div>
          </div>

          {/* Seção: módulos beta */}
          <div className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-1">Módulos Beta disponíveis</h2>
            <p className="text-sm text-gray-500 mb-6">
              Eles mostram o que vem por aí e podem ser liberados como piloto acompanhado, sem
              checkout automático dentro do sistema.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {ORDEM_MODULOS.map((key) => (
                <CardModulo key={key} moduloKey={key} />
              ))}
            </div>
          </div>

          {/* Seção: como solicitar */}
          <div className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-1">Como pedir acesso</h2>
            <p className="text-sm text-gray-500 mb-6">Simples e direto — tudo pelo WhatsApp.</p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                {
                  passo: "1",
                  titulo: "Escolha o Beta",
                  descricao:
                    "Veja os módulos acima e escolha qual recurso avançado faz sentido testar primeiro.",
                },
                {
                  passo: "2",
                  titulo: "Fale com o suporte",
                  descricao:
                    'Clique em "Solicitar acesso Beta" ou "Tirar dúvidas". A gente explica o escopo e combina o piloto.',
                },
                {
                  passo: "3",
                  titulo: "Liberação acompanhada",
                  descricao:
                    "Quando aprovado, o acesso é liberado manualmente e acompanhado de perto para validar o uso.",
                },
              ].map((etapa) => (
                <div
                  key={etapa.passo}
                  className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
                >
                  <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center mb-3">
                    <span className="text-sm font-bold text-indigo-700">{etapa.passo}</span>
                  </div>
                  <p className="font-bold text-gray-900 text-sm mb-1">{etapa.titulo}</p>
                  <p className="text-sm text-gray-500">{etapa.descricao}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Seção: dúvidas comuns */}
          <div className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-1">Dúvidas comuns</h2>
            <p className="text-sm text-gray-500 mb-6">
              Perguntas que a maioria dos usuários faz antes de começar.
            </p>

            <div className="space-y-2">
              {FAQS.map((faq) => (
                <ItemFAQ key={faq.pergunta} pergunta={faq.pergunta} resposta={faq.resposta} />
              ))}
            </div>
          </div>

          {/* CTA final */}
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 text-white text-center">
            <h3 className="text-xl font-bold mb-2">Ainda tem dúvidas? Fala comigo!</h3>
            <p className="text-indigo-100 text-sm mb-5">
              Nossa equipe responde em minutos pelo WhatsApp. Nenhuma pergunta é boba — é melhor
              perguntar antes de ativar algo do que usar sem entender.
            </p>
            <a
              href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgGeral}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 bg-white text-indigo-700 font-bold px-8 py-3 rounded-xl hover:bg-indigo-50 transition-colors"
            >
              <FiMessageCircle className="w-5 h-5" />
              Falar com o suporte agora
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

export default Ajuda;
