/**
 * ModuloBloqueado - Tela de venda dos modulos premium.
 * Cada modulo tem preview interativo + argumentos de ROI para converter.
 */
import { useEffect } from "react";
import { FiCheckCircle, FiHelpCircle, FiLock, FiMessageCircle, FiTrendingUp } from "react-icons/fi";
import { Link } from "react-router-dom";
import { MODULOS_INFO, useModulos } from "../contexts/ModulosContext";
import { PREVIEWS } from "./moduloBloqueado/ModuloBloqueadoPreviews";

const WHATSAPP_NUMERO = "5518997401641";

/* ---------------------------------------------------
   DADOS DE VENDA - ROI e beneficios por modulo
--------------------------------------------------- */
const MODULOS_EXTRAS = {
  campanhas: {
    roi_banner:
      "Petshops com Campanhas recuperam em media R$ 3.500/mes que iam para o concorrente — sem gastar nada com marketing",
    payback: "Se paga com 1 cliente recuperado",
    beneficios: [
      {
        texto: "Mensagens automaticas no WhatsApp",
        detalhe: "Sem copiar e colar — o sistema dispara pra voce na hora certa",
      },
      {
        texto: "Segmentacao inteligente de clientes",
        detalhe: "Clientes sumidos, aniversariantes, por raca, por servico contratado...",
      },
      {
        texto: "Cartao fidelidade com regra automatica",
        detalhe:
          "O sistema identifica quem esta na 4a compra e dispara incentivo da 5a automaticamente",
      },
      {
        texto: "Fluxo de cashback para acelerar recompra",
        detalhe: "Define valor e validade do cashback para trazer o cliente de volta mais rapido",
      },
      {
        texto: "Reativacao de clientes parados (30 dias+)",
        detalhe: "Campanha automatica para recuperar clientes que sumiram da base",
      },
      {
        texto: "Recompra programada em 7 dias",
        detalhe: "Mensagem no momento certo para reposicao de racao, areia e itens recorrentes",
      },
      {
        texto: "Relatorio de retorno por campanha",
        detalhe: "Veja exatamente quantos clientes cada campanha trouxe de volta e quanto gerou",
      },
      {
        texto: "Promocoes e cupons com envio automatico",
        detalhe: "Crie promocoes relampago e envie para o publico certo",
      },
      {
        texto: "Historico de interacoes por cliente",
        detalhe: null,
      },
    ],
  },
  entregas: {
    roi_banner:
      "1 entrega por dia ja paga o modulo inteiro. A partir dai, e lucro puro — e o cliente nunca mais liga perguntando onde esta o pedido",
    payback: "Se paga com 7 entregas no mes",
    beneficios: [
      {
        texto: "Entregador ve a rota, confirma com foto e assina digitalmente",
        detalhe: "Prova de entrega indiscutivel — chega de 'nao recebi'",
      },
      {
        texto: "Link de rastreio automatico pelo WhatsApp",
        detalhe: "Zero ligacoes perguntando onde esta o pedido",
      },
      {
        texto: "Cliente recebe notificacao de saida automaticamente",
        detalhe: "Quando o pedido sai, o cliente e avisado na hora e ja se prepara para receber",
      },
      {
        texto: "Acompanhamento em tempo real no mapa",
        detalhe: "Mais transparencia para o cliente e menos desgaste para o caixa/atendimento",
      },
      {
        texto: "Controle de multiplos entregadores",
        detalhe: "Veja em tempo real quem esta onde e com quantas entregas",
      },
      {
        texto: "Controle de distancia, custo e manutencao da moto",
        detalhe: "Acompanhe km rodado, custo por entrega e alertas de revisao para reduzir gastos",
      },
      {
        texto: "Organizacao de rotas por sistema inteligente",
        detalhe:
          "Sequencia otimizada de paradas para reduzir tempo de entrega e consumo de combustivel",
      },
      {
        texto: "Historico completo de cada entrega",
        detalhe: "Nunca mais 'meu pedido nao chegou' sem ter como provar",
      },
    ],
  },
  ecommerce: {
    roi_banner:
      "30% das vendas online acontecem depois das 21h. Sua loja pode vender enquanto voce dorme — sem funcionario, sem esforco",
    payback: "Se paga com 1 venda online por mes",
    beneficios: [
      {
        texto: "Loja virtual com seu proprio dominio",
        detalhe: "Aparece no Google com o nome do seu pet shop — sem depender do Instagram",
      },
      {
        texto: "Pagamento online — Pix + Cartao",
        detalhe: "Receba antes de separar o pedido. Zero inadimplencia, zero fiado",
      },
      {
        texto: "Estoque sincronizado em tempo real",
        detalhe: "Produto esgotado no fisico? Some automaticamente do site tambem",
      },
      {
        texto: "Gestao de pedidos integrada ao sistema",
        detalhe: "Pedido online ja entra no seu fluxo normal, sem digitar nada",
      },
      {
        texto: "Analytics de vendas por produto e canal",
        detalhe: null,
      },
    ],
  },
  whatsapp: {
    roi_banner:
      "94% dos clientes preferem WhatsApp a ligar. Com atendimento automatico, voce responde em 8 segundos — mesmo de madrugada",
    payback: "Se paga com 1 hora de funcionario poupada por dia",
    beneficios: [
      {
        texto: "Bot que responde, consulta estoque e fecha venda",
        detalhe: "Conversa completa no WhatsApp e pedido pronto para o caixa apenas confirmar",
      },
      {
        texto: "Venda vai para o caixa pronta para confirmacao",
        detalhe: "Itens, valores, observacoes e forma de pagamento chegam organizados no sistema",
      },
      {
        texto: "Consulta fotos dos produtos no sistema e envia ao cliente",
        detalhe:
          "Ideal para tirar duvidas de tamanho, sabor, modelo e embalagem no proprio atendimento",
      },
      {
        texto: "Recupera carrinho e negocia automaticamente",
        detalhe: "Se o cliente para no meio, o bot retoma a conversa e tenta concluir a compra",
      },
      {
        texto: "Agendamento automatico de banho e tosa",
        detalhe: "Sem ocupar o telefone, sem erro de agenda",
      },
      {
        texto: "Retorno automatico de clientes sumidos",
        detalhe: "Bot manda mensagem quando o cliente nao aparece ha 30 dias",
      },
      {
        texto: "Historico completo das conversas",
        detalhe: "Saiba exatamente o que foi combinado com cada cliente",
      },
      {
        texto: "Atendimento padronizado 24h",
        detalhe: "Mesmo nivel de resposta em todos os turnos, sem depender de quem esta no caixa",
      },
    ],
  },
};

function getExtras(modulo, info) {
  return (
    MODULOS_EXTRAS[modulo] || {
      roi_banner: `${info.nome} e um modulo premium com resultados comprovados.`,
      payback: null,
      beneficios: info.recursos.map((r) => ({ texto: r, detalhe: null })),
    }
  );
}

function getBeneficiosPorSecao(modulo, beneficios) {
  if (modulo === "whatsapp") {
    return [
      { titulo: "Vendas no WhatsApp", itens: beneficios.slice(0, 4) },
      { titulo: "Operacao automatizada", itens: beneficios.slice(4) },
    ];
  }

  if (modulo === "entregas") {
    return [
      {
        titulo: "Agilidade e experiencia do cliente",
        itens: beneficios.slice(0, 4),
      },
      { titulo: "Controle da operacao", itens: beneficios.slice(4) },
    ];
  }

  if (modulo === "campanhas") {
    return [
      { titulo: "Retencao e reativacao", itens: beneficios.slice(0, 6) },
      { titulo: "Gestao e resultado", itens: beneficios.slice(6) },
    ];
  }

  if (modulo === "ecommerce") {
    return [
      { titulo: "Vendas online", itens: beneficios.slice(0, 3) },
      { titulo: "Operacao e analise", itens: beneficios.slice(3) },
    ];
  }

  return [{ titulo: "Principais beneficios", itens: beneficios }];
}

/* ---------------------------------------------------
   Componente principal
--------------------------------------------------- */
const ModuloBloqueado = ({ modulo, children }) => {
  const { moduloAtivo, modulosAtivos, moduloBetaPublico, moduloForaOfertaPublica } = useModulos();

  // Registrar tentativa de acesso a módulo bloqueado (tracking leve)
  useEffect(() => {
    if (modulosAtivos !== null && !moduloAtivo(modulo)) {
      // Evento local — pode ser expandido para analytics no futuro
      try {
        const tentativas = JSON.parse(sessionStorage.getItem("modulos_tentativas") || "{}");
        tentativas[modulo] = (tentativas[modulo] || 0) + 1;
        sessionStorage.setItem("modulos_tentativas", JSON.stringify(tentativas));
      } catch {
        // Silencioso — não bloqueia a UI
      }
    }
  }, [modulo, moduloAtivo, modulosAtivos]);

  // Enquanto carrega status dos modulos, nao monta filhos premium.
  // Isso evita chamadas de API antes de confirmar que o tenant tem acesso.
  if (modulosAtivos === null) {
    return <div className="min-h-[240px]" aria-hidden="true" />;
  }

  if (moduloAtivo(modulo)) {
    return children;
  }

  const info = MODULOS_INFO[modulo] || {
    nome: modulo,
    descricao: "Este modulo e premium.",
    preco: 0,
    recursos: [],
  };

  if (moduloForaOfertaPublica(modulo)) {
    return (
      <div className="min-h-full bg-slate-50 p-4 md:p-6 flex items-start justify-center">
        <div className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500">
            <FiLock className="h-6 w-6" />
          </div>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
            Recurso fora da oferta atual
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-900">
            Este recurso nao esta disponivel para novos tenants.
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
            O trial publico libera o Plano Basico completo por 30 dias. Modulos avancados entram
            apenas como Beta acompanhado, quando fizer sentido para o cliente e para a operacao.
          </p>
          <Link
            to="/dashboard"
            className="mt-6 inline-flex rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Voltar ao sistema
          </Link>
        </div>
      </div>
    );
  }

  const extras = getExtras(modulo, info);
  const secoesBeneficios = getBeneficiosPorSecao(modulo, extras.beneficios);
  const betaPublico = moduloBetaPublico(modulo);

  const msgWhatsApp = encodeURIComponent(
    betaPublico
      ? `Ola! Quero solicitar acesso Beta ao modulo ${info.nome} do CorePet. Pode me ajudar?`
      : `Ola! Quero saber mais sobre o modulo ${info.nome} do CorePet. Pode me ajudar?`,
  );

  const Preview = PREVIEWS[modulo] ?? null;

  return (
    <div className="min-h-full bg-gradient-to-br from-indigo-50 to-purple-50 p-4 md:p-6 flex items-start justify-center">
      <div className="w-full max-w-4xl">
        {/* Cabecalho */}
        <div className="text-center mb-5">
          <div className="inline-flex items-center gap-2 bg-white border border-indigo-200 rounded-full px-4 py-1.5 shadow-sm mb-3">
            <FiTrendingUp className="w-3.5 h-3.5 text-indigo-500" />
            <span className="text-xs font-semibold text-indigo-600">
              {betaPublico
                ? "Modulo Beta — piloto acompanhado"
                : "Modulo controlado — acesso sob liberacao"}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-1">{info.nome}</h2>
          <p className="text-gray-500 text-sm">{info.descricao}</p>
        </div>

        {/* Banner ROI */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-4 mb-5 text-white text-center shadow-lg">
          <p className="text-sm font-medium opacity-90">{extras.roi_banner}</p>
        </div>

        {/* Grid: preview + card */}
        <div className={`grid gap-6 ${Preview ? "lg:grid-cols-2" : "max-w-md mx-auto"}`}>
          {/* Preview visual */}
          {Preview && (
            <div className="bg-gray-50 rounded-2xl p-4 border border-gray-200 shadow-inner">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2 h-2 rounded-full bg-red-400" />
                <div className="w-2 h-2 rounded-full bg-amber-400" />
                <div className="w-2 h-2 rounded-full bg-green-400" />
                <span className="text-xs text-gray-400 ml-1 font-mono">
                  como vai ficar na sua conta
                </span>
              </div>
              <div className="select-none">
                <Preview />
              </div>
            </div>
          )}

          {/* Card de preco */}
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100 flex flex-col">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
              O que voce ganha
            </p>

            <div className="space-y-3 flex-1">
              {secoesBeneficios.map((secao) => (
                <div
                  key={secao.titulo}
                  className="rounded-xl border border-gray-100 bg-gray-50/60 p-3"
                >
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-2">
                    {secao.titulo}
                  </p>
                  <ul className="space-y-2.5">
                    {secao.itens.map((b) => (
                      <li key={`${secao.titulo}-${b.texto}`} className="flex items-start gap-2.5">
                        <FiCheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-gray-800">{b.texto}</p>
                          {b.detalhe && <p className="text-xs text-gray-500 mt-0.5">{b.detalhe}</p>}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            {/* Acesso */}
            <div className="mt-5 pt-5 border-t border-gray-100">
              <div className="flex items-end justify-between mb-1">
                <div>
                  <p className="text-xs text-gray-400">Tipo de acesso</p>
                  <p className="text-3xl font-bold text-gray-900">
                    Beta
                    <span className="text-base font-normal text-gray-400"> acompanhado</span>
                  </p>
                </div>
                {extras.payback && (
                  <p className="text-xs text-green-600 font-semibold text-right max-w-[130px] leading-tight">
                    👉 {extras.payback}
                  </p>
                )}
              </div>

              {/* CTAs */}
              <a
                href={`https://wa.me/${WHATSAPP_NUMERO}?text=${msgWhatsApp}`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-center gap-2 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-4 rounded-xl transition-colors mt-4"
              >
                <FiMessageCircle className="w-4 h-4" />
                Solicitar acesso Beta
              </a>
              <a
                href={`https://wa.me/${WHATSAPP_NUMERO}?text=${encodeURIComponent(`Quero saber mais sobre o modulo ${info.nome}`)}`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-center gap-2 w-full mt-2 text-green-600 hover:text-green-700 font-medium py-2 px-4 rounded-xl border border-green-200 hover:bg-green-50 transition-colors"
              >
                <FiMessageCircle className="w-4 h-4" />
                Tirar duvidas pelo WhatsApp
              </a>
            </div>

            {/* Rodape */}
            <div className="flex flex-col items-center gap-2 mt-4">
              <div className="flex items-center justify-center gap-2 text-xs text-gray-400">
                <FiLock className="w-3 h-3 flex-shrink-0" />
                <span>Liberacao manual por tenant, com acompanhamento do piloto.</span>
              </div>
              <Link
                to="/ajuda"
                className="inline-flex items-center gap-1.5 text-xs text-indigo-500 hover:text-indigo-700 font-medium transition-colors"
              >
                <FiHelpCircle className="w-3.5 h-3.5" />
                Ver todos os planos e duvidas frequentes
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModuloBloqueado;
