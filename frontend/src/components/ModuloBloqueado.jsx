/**
 * ModuloBloqueado - Tela de venda dos modulos premium.
 * Cada modulo tem preview interativo + argumentos de ROI para converter.
 */
import { useEffect, useState } from "react";
import {
  FiCheckCircle,
  FiCreditCard,
  FiLock,
  FiMessageCircle,
  FiTrendingUp,
} from "react-icons/fi";
import { MODULOS_INFO, useModulos } from "../contexts/ModulosContext";

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
        detalhe:
          "Sem copiar e colar — o sistema dispara pra voce na hora certa",
      },
      {
        texto: "Segmentacao inteligente de clientes",
        detalhe:
          "Clientes sumidos, aniversariantes, por raca, por servico contratado...",
      },
      {
        texto: "Cartao fidelidade com regra automatica",
        detalhe:
          "O sistema identifica quem esta na 4a compra e dispara incentivo da 5a automaticamente",
      },
      {
        texto: "Fluxo de cashback para acelerar recompra",
        detalhe:
          "Define valor e validade do cashback para trazer o cliente de volta mais rapido",
      },
      {
        texto: "Reativacao de clientes parados (30 dias+)",
        detalhe:
          "Campanha automatica para recuperar clientes que sumiram da base",
      },
      {
        texto: "Recompra programada em 7 dias",
        detalhe:
          "Mensagem no momento certo para reposicao de racao, areia e itens recorrentes",
      },
      {
        texto: "Relatorio de retorno por campanha",
        detalhe:
          "Veja exatamente quantos clientes cada campanha trouxe de volta e quanto gerou",
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
        detalhe:
          "Quando o pedido sai, o cliente e avisado na hora e ja se prepara para receber",
      },
      {
        texto: "Acompanhamento em tempo real no mapa",
        detalhe:
          "Mais transparencia para o cliente e menos desgaste para o caixa/atendimento",
      },
      {
        texto: "Controle de multiplos entregadores",
        detalhe: "Veja em tempo real quem esta onde e com quantas entregas",
      },
      {
        texto: "Controle de distancia, custo e manutencao da moto",
        detalhe:
          "Acompanhe km rodado, custo por entrega e alertas de revisao para reduzir gastos",
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
        detalhe:
          "Aparece no Google com o nome do seu pet shop — sem depender do Instagram",
      },
      {
        texto: "Pagamento online — Pix + Cartao",
        detalhe:
          "Receba antes de separar o pedido. Zero inadimplencia, zero fiado",
      },
      {
        texto: "Estoque sincronizado em tempo real",
        detalhe:
          "Produto esgotado no fisico? Some automaticamente do site tambem",
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
        detalhe:
          "Conversa completa no WhatsApp e pedido pronto para o caixa apenas confirmar",
      },
      {
        texto: "Venda vai para o caixa pronta para confirmacao",
        detalhe:
          "Itens, valores, observacoes e forma de pagamento chegam organizados no sistema",
      },
      {
        texto: "Consulta fotos dos produtos no sistema e envia ao cliente",
        detalhe:
          "Ideal para tirar duvidas de tamanho, sabor, modelo e embalagem no proprio atendimento",
      },
      {
        texto: "Recupera carrinho e negocia automaticamente",
        detalhe:
          "Se o cliente para no meio, o bot retoma a conversa e tenta concluir a compra",
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
        detalhe:
          "Mesmo nivel de resposta em todos os turnos, sem depender de quem esta no caixa",
      },
    ],
  },
};

/* ---------------------------------------------------
   Preview animado — Campanhas
--------------------------------------------------- */
const PreviewCampanhas = () => {
  const [ativo, setAtivo] = useState(0);
  const campanhas = [
    {
      nome: "Cartao fidelidade: 5a compra gratis",
      resumo: "Reteve 73 clientes no ultimo mes",
      impacto: "+R$ 2.180 no faturamento",
      detalhe: "A cada 10 mensagens, 4 clientes voltam para comprar",
      msgSistema:
        "🎉 Oi Mariana! Voce completou 4 compras. Na 5a voce ganha um snack premium gratis. Quer aproveitar hoje?",
      msgCliente: "Quero sim! Ja me manda as opcoes 😊",
    },
    {
      nome: "Cashback progressivo",
      resumo: "Aumentou ticket medio em 18%",
      impacto: "+R$ 1.420 em vendas de recompra",
      detalhe: "Cliente usa cashback em ate 12 dias e volta mais rapido",
      msgSistema:
        "💸 Pedido acima de R$ 120 libera R$ 15 de cashback para sua proxima compra. Quer ativar agora?",
      msgCliente: "Pode ativar, vou levar racao e petisco.",
    },
    {
      nome: "Reativacao: 30 dias sem comprar",
      resumo: "87 clientes voltaram apos 30 dias parados",
      impacto: "+R$ 980 recuperados no mes",
      detalhe: "A cada 20 mensagens automaticas, 6 clientes voltam",
      msgSistema:
        "🐾 Oi Joao! Sentimos sua falta. Faz 30 dias sem pedido e hoje voce tem frete gratis + 10% OFF.",
      msgCliente: "Boa! Quero repetir o ultimo pedido.",
    },
    {
      nome: "Recompra rapida: cliente volta em 7 dias",
      resumo: "58 clientes recompraram em ate 7 dias",
      impacto: "+R$ 1.240 em faturamento recorrente",
      detalhe: "Fluxo automatico evita esquecimento e acelera reposicao",
      msgSistema:
        "⏰ Oi Ana! Ja faz 7 dias da ultima compra. Quer reposicao automatica da mesma racao com 5% OFF?",
      msgCliente: "Pode fechar, mesma marca e tamanho.",
    },
  ];
  const campanhaAtiva = campanhas[ativo];

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Campanhas ativas
      </p>
      {campanhas.map((c, idx) => (
        <div
          key={c.nome}
          role="button"
          tabIndex={0}
          onMouseEnter={() => setAtivo(idx)}
          onFocus={() => setAtivo(idx)}
          onClick={() => setAtivo(idx)}
          className={`rounded-xl p-3 shadow-sm border transition-all duration-400 ${
            idx === ativo
              ? "bg-indigo-50 border-indigo-200"
              : "bg-white border-gray-100 hover:border-indigo-100"
          }`}
        >
          <p className="text-sm font-semibold text-gray-800">{c.nome}</p>
          <p className="text-xs text-gray-500 mt-1">{c.resumo}</p>
          <p className="text-xs font-medium text-indigo-700 mt-1">
            {c.impacto}
          </p>
          <p className="text-[11px] text-gray-400 mt-1">{c.detalhe}</p>
        </div>
      ))}

      {/* KPI grid */}
      <div className="grid grid-cols-3 gap-2 mt-3">
        {[
          { v: "R$ 5.820", l: "faturamento extra" },
          { v: "286", l: "impactados" },
          { v: "87", l: "reativados" },
        ].map((k) => (
          <div key={k.l} className="bg-indigo-50 rounded-lg p-2 text-center">
            <p className="text-sm font-bold text-indigo-700">{k.v}</p>
            <p className="text-xs text-indigo-500">{k.l}</p>
          </div>
        ))}
      </div>

      <div className="bg-indigo-50 rounded-lg px-3 py-2 border border-indigo-100">
        <p className="text-[11px] font-semibold text-indigo-700 uppercase tracking-wide">
          Campanha em destaque: {campanhaAtiva.nome}
        </p>
      </div>

      {/* WhatsApp mockup dinamico */}
      <div className="bg-[#e5ddd5] rounded-xl p-3 mt-2">
        <div key={campanhaAtiva.nome} className="space-y-2 animate-fadeIn">
          <div className="flex justify-end">
            <div className="bg-[#dcf8c6] rounded-lg rounded-tr-none px-3 py-2 shadow-sm max-w-[90%]">
              <p className="text-xs text-gray-800">
                {campanhaAtiva.msgSistema}
              </p>
              <p className="text-[10px] text-gray-400 text-right mt-1">
                Sistema Pet ✓✓
              </p>
            </div>
          </div>
          <div className="flex justify-start">
            <div className="bg-white rounded-lg rounded-tl-none px-3 py-2 shadow-sm max-w-[85%]">
              <p className="text-xs text-gray-800">
                {campanhaAtiva.msgCliente}
              </p>
              <p className="text-[10px] text-gray-400 text-right mt-1">
                Cliente
              </p>
            </div>
          </div>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
          <p className="text-[11px] text-green-700 font-medium">
            Passe o mouse na campanha (ou toque no celular) para atualizar a
            mensagem
          </p>
        </div>
      </div>
    </div>
  );
};

/* ---------------------------------------------------
   Preview animado — Entregas
--------------------------------------------------- */
const PreviewEntregas = () => {
  const [pulse, setPulse] = useState(false);
  useEffect(() => {
    const t = setInterval(() => setPulse((p) => !p), 900);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-3">
      {/* Resumo rapido */}
      <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl p-3 text-white">
        <p className="text-xs font-medium opacity-90">
          Operacao de entregas hoje
        </p>
        <div className="grid grid-cols-3 gap-2 mt-2">
          <div>
            <p className="text-lg font-bold">94</p>
            <p className="text-[10px] opacity-90">entregas</p>
          </div>
          <div>
            <p className="text-lg font-bold">312 km</p>
            <p className="text-[10px] opacity-90">rodados</p>
          </div>
          <div>
            <p className="text-lg font-bold">R$ 1.128</p>
            <p className="text-[10px] opacity-90">faturamento extra</p>
          </div>
        </div>
      </div>

      {/* Controle de distancia, custo e manutencao */}
      <div className="bg-white rounded-xl p-3 border border-gray-100">
        <p className="text-xs font-semibold text-gray-700 mb-2">
          Controle de distancia, custos e manutencao da moto
        </p>
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-slate-50 rounded-lg p-2">
            <p className="text-[10px] text-gray-500">custo por km</p>
            <p className="text-sm font-bold text-slate-700">R$ 0,82</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-2">
            <p className="text-[10px] text-gray-500">combustivel hoje</p>
            <p className="text-sm font-bold text-slate-700">R$ 255</p>
          </div>
          <div className="bg-amber-50 rounded-lg p-2 border border-amber-100">
            <p className="text-[10px] text-amber-700">manutencao</p>
            <p className="text-sm font-bold text-amber-700">
              revisao em 4 dias
            </p>
          </div>
        </div>
      </div>

      {/* Rota inteligente */}
      <div className="bg-indigo-50 rounded-xl p-3 border border-indigo-100">
        <p className="text-xs font-semibold text-indigo-700">
          Rota inteligente organizada pelo sistema
        </p>
        <p className="text-[11px] text-indigo-600 mt-1">
          Sequencia otimizada: 6 paradas em 52 min (economia de 11 km no turno).
        </p>
      </div>

      {/* Acompanhamento em tempo real para cliente */}
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-4 border-2 border-green-200 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <div
            className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${
              pulse ? "bg-green-500 scale-125" : "bg-green-400"
            }`}
          />
          <p className="text-sm font-bold text-green-800">
            Acompanhamento em tempo real para o cliente
          </p>
        </div>

        <div className="space-y-2">
          <div className="bg-white rounded-lg border border-green-100 px-3 py-2">
            <p className="text-xs font-semibold text-green-700">
              1. Notificacao de saida
            </p>
            <p className="text-[11px] text-gray-600 mt-0.5">
              Cliente recebe no WhatsApp: "pedido saiu para entrega".
            </p>
          </div>

          <div className="bg-white rounded-lg border border-green-100 px-3 py-2">
            <p className="text-xs font-semibold text-green-700">
              2. Cliente acompanha no mapa
            </p>
            <p className="text-[11px] text-gray-600 mt-0.5">
              Acompanhamento ao vivo reduz ansiedade e evita ligacoes para a
              loja.
            </p>
          </div>

          <div className="bg-white rounded-lg border border-green-100 px-3 py-2">
            <p className="text-xs font-semibold text-green-700">
              3. Conclusao com comprovante
            </p>
            <p className="text-[11px] text-gray-600 mt-0.5">
              Entrega finalizada com foto/confirmacao no app e historico salvo.
            </p>
          </div>
        </div>
      </div>

      {/* App do entregador */}
      <div className="bg-blue-50 rounded-xl p-3 border border-blue-100">
        <p className="text-xs font-semibold text-blue-700 mb-1">
          App do entregador em tempo real
        </p>
        <p className="text-[11px] text-blue-700">
          Entregador consulta itens da venda, observacoes e pagamento no
          celular.
        </p>
        <p className="text-[11px] text-blue-700 mt-1">
          Resultado: menos erro de entrega, menos retrabalho e mais agilidade.
        </p>
      </div>
    </div>
  );
};

/* ---------------------------------------------------
   Preview animado — E-commerce
--------------------------------------------------- */
const PreviewEcommerce = () => {
  const [notifVis, setNotifVis] = useState(true);
  useEffect(() => {
    const t = setInterval(() => setNotifVis((v) => !v), 2200);
    return () => clearInterval(t);
  }, []);

  const barras = [40, 55, 70, 45, 60, 50, 90];
  const dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"];

  return (
    <div className="space-y-3">
      {/* Notificacao pulsando */}
      <div
        className={`rounded-xl p-3 border transition-all duration-500 ${
          notifVis
            ? "bg-indigo-600 border-indigo-700 shadow-lg shadow-indigo-200"
            : "bg-indigo-50 border-indigo-100"
        }`}
      >
        <div className="flex items-start gap-2">
          <div
            className={`text-lg transition-all duration-300 ${notifVis ? "scale-110" : "scale-100"}`}
          >
            🛒
          </div>
          <div>
            <p
              className={`text-xs font-bold ${notifVis ? "text-white" : "text-indigo-700"}`}
            >
              NOVO PEDIDO RECEBIDO
            </p>
            <p
              className={`text-sm font-semibold ${notifVis ? "text-indigo-100" : "text-gray-700"}`}
            >
              Fernanda C. — R$ 189,90 🎂 Pix confirmado
            </p>
            <p
              className={`text-xs ${notifVis ? "text-indigo-200" : "text-gray-400"}`}
            >
              Racao Golden 15kg + Petisco Dental — Domingo 23:47
            </p>
          </div>
        </div>
      </div>

      {/* Mini grafico */}
      <div className="bg-white rounded-xl p-3 border border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-gray-500">Vendas — ultimos 7 dias</p>
          <p className="text-sm font-bold text-gray-800">R$ 2.847</p>
        </div>
        <div className="flex items-end gap-1 h-12">
          {barras.map((h, i) => (
            <div
              key={i}
              className={`flex-1 rounded-t transition-all duration-300 ${
                i === 6 ? "bg-indigo-500" : "bg-indigo-200"
              }`}
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
        <div className="flex justify-between mt-1">
          {dias.map((d, i) => (
            <span
              key={d}
              className={`text-[10px] flex-1 text-center ${
                i === 6 ? "text-indigo-600 font-bold" : "text-gray-400"
              }`}
            >
              {d}
            </span>
          ))}
        </div>
        <p className="text-[10px] text-indigo-600 text-center mt-1">
          🔥 Dom foi o melhor dia — voce estava dormindo
        </p>
      </div>

      {/* Top produtos */}
      <div className="bg-white rounded-xl p-3 border border-gray-100">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Top produtos online esta semana
        </p>
        {[
          { e: "🐶", n: "Racao Golden 15kg", v: "R$ 89,90", rep: 31 },
          { e: "🐱", n: "Areia Higienica 4kg", v: "R$ 29,90", rep: 24 },
          { e: "🦮", n: "Coleira Anti-pulga M", v: "R$ 47,90", rep: 18 },
        ].map((p) => (
          <div key={p.n} className="flex items-center gap-2 py-1.5">
            <span className="text-lg">{p.e}</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-gray-800 truncate">
                {p.n}
              </p>
              <div className="flex-1 bg-gray-100 rounded-full h-1 mt-1">
                <div
                  className="bg-indigo-400 h-1 rounded-full"
                  style={{ width: `${(p.rep / 35) * 100}%` }}
                />
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs font-bold text-indigo-600">{p.v}</p>
              <p className="text-[10px] text-gray-400">{p.rep}x</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ---------------------------------------------------
   Preview animado — WhatsApp
--------------------------------------------------- */
const PreviewWhatsApp = () => {
  return (
    <div className="space-y-3">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { v: "47", l: "atendimentos hoje" },
          { v: "94%", l: "automaticos" },
          { v: "8s", l: "tempo de resposta" },
        ].map((s) => (
          <div key={s.l} className="bg-green-50 rounded-lg p-2 text-center">
            <p className="text-base font-bold text-green-700">{s.v}</p>
            <p className="text-[10px] text-green-600 leading-tight">{s.l}</p>
          </div>
        ))}
      </div>

      {/* Chat mockup */}
      <div className="bg-[#e5ddd5] rounded-xl p-3 space-y-2 min-h-[320px]">
        {/* Cliente pergunta */}
        <div className="flex justify-start">
          <div className="bg-white rounded-lg rounded-tl-none px-3 py-2 shadow-sm max-w-[80%]">
            <p className="text-xs text-gray-800">
              Oi! Quero saber o preco da racao Golden 15kg 🐶
            </p>
            <p className="text-[10px] text-gray-400 text-right mt-1">14:22</p>
          </div>
        </div>

        <div className="flex justify-end">
          <div className="bg-[#dcf8c6] rounded-lg rounded-tr-none px-3 py-2 shadow-sm max-w-[85%]">
            <p className="text-xs text-gray-800">
              Ola! 😊 A racao Golden 15kg esta <strong>R$ 179,90</strong>. Temos
              em estoque! Quer que eu adicione ao carrinho?
            </p>
            <p className="text-[10px] text-gray-400 text-right mt-1">
              14:22 ✓✓
            </p>
          </div>
        </div>

        <div className="flex justify-start">
          <div className="bg-white rounded-lg rounded-tl-none px-3 py-2 shadow-sm max-w-[80%]">
            <p className="text-xs text-gray-800">Sim! E entregam?</p>
            <p className="text-[10px] text-gray-400 text-right mt-1">14:23</p>
          </div>
        </div>
        <div className="flex justify-end">
          <div className="bg-[#dcf8c6] rounded-lg rounded-tr-none px-3 py-2 shadow-sm max-w-[85%]">
            <p className="text-xs text-gray-800">
              Sim! Entrega em ate 2h. Frete R$ 8,00. Confirmo o pedido? 🛵
            </p>
            <p className="text-[10px] text-gray-400 text-right mt-1">
              14:23 ✓✓
            </p>
          </div>
        </div>

        <div className="flex justify-start">
          <div className="bg-white rounded-lg rounded-tl-none px-3 py-2 shadow-sm max-w-[82%]">
            <p className="text-xs text-gray-800">
              Tenho duvida se essa coleira P serve no meu pet. Vou mandar foto.
            </p>
            <div className="mt-1.5 inline-flex items-center gap-1.5 bg-gray-100 rounded px-2 py-1">
              <span className="text-[10px]">📷</span>
              <span className="text-[10px] text-gray-600">
                foto_porte_pet.jpg
              </span>
            </div>
            <p className="text-[10px] text-gray-400 text-right mt-1">14:24</p>
          </div>
        </div>

        <div className="flex justify-end">
          <div className="bg-[#dcf8c6] rounded-lg rounded-tr-none px-3 py-2 shadow-sm max-w-[88%]">
            <p className="text-xs text-gray-800">
              Analisei a foto ✅ Pelo porte do pet, recomendo o tamanho M. Ja te
              envio as fotos do modelo azul e preto no catalogo.
            </p>
            <div className="mt-1.5 flex items-center gap-1.5">
              <span className="text-[10px] bg-white/80 rounded px-1.5 py-0.5 text-gray-600">
                🖼️ Foto azul
              </span>
              <span className="text-[10px] bg-white/80 rounded px-1.5 py-0.5 text-gray-600">
                🖼️ Foto preta
              </span>
            </div>
            <p className="text-[10px] text-gray-400 text-right mt-1">
              14:24 ✓✓
            </p>
          </div>
        </div>
      </div>

      <div className="bg-indigo-50 rounded-xl p-3 border border-indigo-100">
        <p className="text-xs font-semibold text-indigo-700">
          No sistema (caixa/PDV)
        </p>
        <p className="text-[11px] text-indigo-700 mt-1">
          Venda #PDV-10492 gerada automaticamente com 3 itens (R$ 267,70). O
          caixa apenas confirma e finaliza.
        </p>
      </div>

      <div className="bg-green-50 rounded-xl p-3 border border-green-100 text-center">
        <p className="text-xs text-green-700 font-semibold">
          1 minuto. Sem funcionario.
        </p>
      </div>
    </div>
  );
};

/* ---------------------------------------------------
   Mapa de previews por modulo
--------------------------------------------------- */
const PREVIEWS = {
  campanhas: PreviewCampanhas,
  entregas: PreviewEntregas,
  ecommerce: PreviewEcommerce,
  whatsapp: PreviewWhatsApp,
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
  const { moduloAtivo } = useModulos();

  if (moduloAtivo(modulo)) {
    return children;
  }

  const info = MODULOS_INFO[modulo] || {
    nome: modulo,
    descricao: "Este modulo e premium.",
    preco: 0,
    recursos: [],
  };

  const extras = getExtras(modulo, info);
  const secoesBeneficios = getBeneficiosPorSecao(modulo, extras.beneficios);

  const msgWhatsApp = encodeURIComponent(
    `Ola! Quero contratar o modulo ${info.nome} do Sistema Pet. Pode me ajudar?`,
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
              Modulo Premium — Resultados Comprovados
            </span>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-1">{info.nome}</h2>
          <p className="text-gray-500 text-sm">{info.descricao}</p>
        </div>

        {/* Banner ROI */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-4 mb-5 text-white text-center shadow-lg">
          <p className="text-sm font-medium opacity-90">
            💡 {extras.roi_banner}
          </p>
        </div>

        {/* Grid: preview + card */}
        <div
          className={`grid gap-6 ${Preview ? "lg:grid-cols-2" : "max-w-md mx-auto"}`}
        >
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
                      <li
                        key={`${secao.titulo}-${b.texto}`}
                        className="flex items-start gap-2.5"
                      >
                        <FiCheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-gray-800">
                            {b.texto}
                          </p>
                          {b.detalhe && (
                            <p className="text-xs text-gray-500 mt-0.5">
                              {b.detalhe}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            {/* Preco */}
            <div className="mt-5 pt-5 border-t border-gray-100">
              <div className="flex items-end justify-between mb-1">
                <div>
                  <p className="text-xs text-gray-400">Valor mensal</p>
                  <p className="text-3xl font-bold text-gray-900">
                    R${info.preco}
                    <span className="text-base font-normal text-gray-400">
                      /mes
                    </span>
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
                <FiCreditCard className="w-4 h-4" />
                Contratar agora — R${info.preco}/mes
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
            <div className="flex items-center justify-center gap-2 text-xs text-gray-400 mt-4">
              <FiLock className="w-3 h-3 flex-shrink-0" />
              <span>
                Liberado automaticamente em ate 5 minutos apos confirmacao.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModuloBloqueado;
