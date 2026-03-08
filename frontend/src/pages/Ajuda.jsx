/**
 * Ajuda.jsx — Página central de ajuda e planos do Sistema Pet.
 * Linguagem simples, foco em benefício para o usuário.
 */
import { useState } from "react";
import {
  FiBookOpen,
  FiCheckCircle,
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

const WHATSAPP_NUMERO = "5518997401641";

/* Ícones por módulo */
const ICONES_MODULO = {
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
    pergunta: "Como faço para contratar um módulo?",
    resposta:
      'Clique no botão "Falar com suporte" em qualquer módulo desta página ou direto pelo WhatsApp. O módulo é liberado automaticamente em até 5 minutos após a confirmação do pagamento.',
  },
  {
    pergunta: "Posso contratar só um módulo e não os outros?",
    resposta:
      "Sim! Cada módulo premium é independente e pode ser contratado separadamente. Você paga apenas pelo que vai usar.",
  },
  {
    pergunta: "Como funciona o pagamento?",
    resposta:
      "O pagamento é mensal e pode ser feito por Pix ou cartão de crédito. Sem fidelidade — você pode cancelar a qualquer momento sem multa.",
  },
  {
    pergunta: "O módulo é liberado na hora?",
    resposta:
      "Após a confirmação do pagamento, o módulo é liberado automaticamente em até 5 minutos. Você não precisa fazer nada — basta recarregar a página.",
  },
  {
    pergunta: "Se eu cancelar, perco os dados?",
    resposta:
      "Não. Seus dados ficam salvos. Se reativar o módulo no futuro, tudo estará lá como antes.",
  },
  {
    pergunta: "Posso testar antes de pagar?",
    resposta:
      "Sim! Fale com nosso suporte pelo WhatsApp e solicite um período de demonstração. Mostramos o módulo funcionando na sua própria conta.",
  },
  {
    pergunta: "Tenho dúvidas sobre um módulo específico. O que faço?",
    resposta:
      "Fale direto com a gente pelo WhatsApp. Nossa equipe explica o funcionamento e tira todas as dúvidas antes de qualquer contratação.",
  },
];

/* Ordem de exibição dos módulos */
const ORDEM_MODULOS = [
  "campanhas",
  "entregas",
  "whatsapp",
  "ecommerce",
  "app_mobile",
  "marketplaces",
];

/* Componente de card individual de módulo */
const CardModulo = ({ moduloKey }) => {
  const info = MODULOS_INFO[moduloKey];
  if (!info) return null;

  const Icone = ICONES_MODULO[moduloKey] || FiZap;
  const msgWhatsApp = encodeURIComponent(
    `Olá! Quero saber mais sobre o módulo ${info.nome} do Sistema Pet. Pode me ajudar?`,
  );
  const msgContratar = encodeURIComponent(
    `Olá! Quero contratar o módulo ${info.nome} do Sistema Pet.`,
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
            <p className="text-xs text-gray-400">a partir de</p>
            <p className="text-2xl font-bold text-gray-900">
              R$ {info.preco}
              <span className="text-sm font-normal text-gray-400">/mês</span>
            </p>
          </div>
          <span className="text-xs text-green-600 font-semibold bg-green-50 px-2 py-1 rounded-full">
            Sem fidelidade
          </span>
        </div>

        <a
          href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgContratar}`}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-center gap-2 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 px-4 rounded-xl transition-colors text-sm"
        >
          <FiCreditCard className="w-4 h-4" />
          Contratar este módulo
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
  const msgGeral = encodeURIComponent(
    "Olá! Tenho dúvidas sobre os planos do Sistema Pet.",
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 text-white py-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-indigo-200 text-sm font-medium mb-2">
            Ajuda e Planos
          </p>
          <h1 className="text-3xl font-bold mb-3">
            {aba === "central"
              ? "Como usar o Sistema Pet"
              : "Módulos extras do Sistema Pet"}
          </h1>
          <p className="text-indigo-100 text-base max-w-xl mx-auto">
            {aba === "central"
              ? "Aprenda a usar cada funcionalidade do sistema. Pesquise por dúvidas, navegue por módulo ou leia o passo a passo."
              : "O sistema base já está funcionando para você. Quer vender mais, entregar mais rápido ou atender sem parar? Veja o que cada módulo faz e quanto custa."}
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
              Módulos Premium
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

      {/* Conteúdo da aba Módulos Premium */}
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
                  PDV (vendas), Clientes, Pets, Produtos, Financeiro, Lembretes,
                  Comissões, Compras, RH, Inteligência Artificial (Chat) e
                  Configurações já estão liberados para você usar hoje.
                </p>
              </div>
            </div>
          </div>

          {/* Seção: módulos premium */}
          <div className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-1">
              Módulos premium disponíveis
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              Cada módulo é independente — contrate só o que fizer sentido para
              o seu negócio. Cancele a qualquer hora, sem multa.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {ORDEM_MODULOS.map((key) => (
                <CardModulo key={key} moduloKey={key} />
              ))}
            </div>
          </div>

          {/* Seção: como contratar */}
          <div className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-1">
              Como contratar
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              Simples e rápido — tudo pelo WhatsApp.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                {
                  passo: "1",
                  titulo: "Escolha o módulo",
                  descricao:
                    "Veja os módulos acima, entenda o que cada um faz e escolha o que resolve seu problema.",
                },
                {
                  passo: "2",
                  titulo: "Fale com o suporte",
                  descricao:
                    'Clique em "Contratar" ou "Tirar dúvidas". A gente explica tudo e confirma o acesso.',
                },
                {
                  passo: "3",
                  titulo: "Pronto, acesso liberado",
                  descricao:
                    "Em até 5 minutos após o pagamento o módulo aparece desbloqueado no sistema.",
                },
              ].map((etapa) => (
                <div
                  key={etapa.passo}
                  className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
                >
                  <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center mb-3">
                    <span className="text-sm font-bold text-indigo-700">
                      {etapa.passo}
                    </span>
                  </div>
                  <p className="font-bold text-gray-900 text-sm mb-1">
                    {etapa.titulo}
                  </p>
                  <p className="text-sm text-gray-500">{etapa.descricao}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Seção: dúvidas comuns */}
          <div className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-1">
              Dúvidas comuns
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              Perguntas que a maioria dos usuários faz antes de contratar.
            </p>

            <div className="space-y-2">
              {FAQS.map((faq) => (
                <ItemFAQ
                  key={faq.pergunta}
                  pergunta={faq.pergunta}
                  resposta={faq.resposta}
                />
              ))}
            </div>
          </div>

          {/* CTA final */}
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 text-white text-center">
            <h3 className="text-xl font-bold mb-2">
              Ainda tem dúvidas? Fala comigo!
            </h3>
            <p className="text-indigo-100 text-sm mb-5">
              Nossa equipe responde em minutos pelo WhatsApp. Nenhuma pergunta é
              boba — é melhor perguntar antes de contratar do que contratar sem
              saber.
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
