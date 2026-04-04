export const TIPO_LABELS = {
  loyalty_stamp: {
    label: "Cartao Fidelidade",
    color: "bg-purple-100 text-purple-800",
    emoji: "\u{1F3F7}\uFE0F",
  },
  cashback: {
    label: "Cashback",
    color: "bg-green-100 text-green-800",
    emoji: "\u{1F4B0}",
  },
  birthday: {
    label: "Aniversario",
    color: "bg-pink-100 text-pink-800",
    emoji: "\u{1F382}",
  },
  birthday_customer: {
    label: "Aniversario Cliente",
    color: "bg-pink-100 text-pink-800",
    emoji: "\u{1F382}",
  },
  birthday_pet: {
    label: "Aniversario Pet",
    color: "bg-orange-100 text-orange-800",
    emoji: "\u{1F43E}",
  },
  welcome: {
    label: "Boas-vindas",
    color: "bg-blue-100 text-blue-800",
    emoji: "\u{1F44B}",
  },
  welcome_app: {
    label: "Boas-vindas App",
    color: "bg-blue-100 text-blue-800",
    emoji: "\u{1F44B}",
  },
  inactivity: {
    label: "Clientes Inativos",
    color: "bg-red-100 text-red-800",
    emoji: "\u{1F634}",
  },
  ranking_monthly: {
    label: "Ranking Mensal",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "\u{1F3C6}",
  },
  quick_repurchase: {
    label: "Recompra Rapida",
    color: "bg-teal-100 text-teal-800",
    emoji: "\u{1F501}",
  },
  monthly_highlight: {
    label: "Destaque Mensal",
    color: "bg-amber-100 text-amber-800",
    emoji: "\u{1F31F}",
  },
  win_back: {
    label: "Reativacao",
    color: "bg-red-100 text-red-800",
    emoji: "\u{1F504}",
  },
  raffle: {
    label: "Sorteio",
    color: "bg-yellow-100 text-yellow-800",
    emoji: "\u{1F3B2}",
  },
};

export const USER_CREATABLE_TYPES = new Set([
  "inactivity",
  "quick_repurchase",
  "bulk_segment",
]);

export const CUPOM_STATUS = {
  active: { label: "Ativo", color: "bg-green-100 text-green-700" },
  used: { label: "Usado", color: "bg-gray-100 text-gray-600" },
  expired: { label: "Expirado", color: "bg-red-100 text-red-600" },
  voided: { label: "Cancelado", color: "bg-red-100 text-red-600" },
};

export const RANK_LABELS = {
  bronze: {
    label: "Bronze",
    color: "bg-amber-100 text-amber-800",
    border: "border-amber-300",
    emoji: "\u{1F949}",
  },
  silver: {
    label: "Prata",
    color: "bg-gray-100 text-gray-700",
    border: "border-gray-400",
    emoji: "\u{1F948}",
  },
  gold: {
    label: "Ouro",
    color: "bg-yellow-100 text-yellow-800",
    border: "border-yellow-400",
    emoji: "\u{1F947}",
  },
  diamond: {
    label: "Platina",
    color: "bg-purple-100 text-purple-800",
    border: "border-purple-400",
    emoji: "\u{1F451}",
  },
  platinum: {
    label: "Diamante",
    color: "bg-cyan-100 text-cyan-800",
    border: "border-cyan-400",
    emoji: "\u{1F48E}",
  },
};

export const FRASES_ANIVERSARIO = {
  birthday_customer: {
    brinde:
      "\u{1F382} Feliz aniversario, {nome}! Seu carinho merece uma celebracao especial! Apareca na nossa loja para retirar seu presente surpresa. Sera um prazer ver voce! \u{1F381}",
    cupom:
      "\u{1F389} Feliz aniversario, {nome}! Neste dia tao especial preparamos um cupom de {desconto} de desconto pra voce celebrar com muito mimo pro seu pet! Use o codigo {code}. \u{1F43E}",
  },
  birthday_pet: {
    brinde:
      "\u{1F43E}\u{1F382} Que dia mais fofo! {nome_pet} esta fazendo aniversario e a gente nao podia deixar passar em branco! Venha buscar o mimo especial que separamos pro seu melhor amigo - tem muito carinho esperando por voces! Um beijo nas patinhas! \u{1F973}",
    cupom:
      "\u{1F388} O {nome_pet} ta de parabens hoje, {nome}! Para comemorar esse dia tao especial, preparamos um cupom de {desconto} de desconto pra mimar o(a) aniversariante! Use o codigo {code} e vai fundo nos mimos! \u{1F415}\u{1F381}",
  },
};

export const hoje = new Date().toISOString().slice(0, 10);
export const primeiroDiaMes = `${hoje.slice(0, 7)}-01`;

export function createDefaultPremio() {
  return {
    tipo_premio: "cupom",
    coupon_value: 50,
    coupon_valid_days: 10,
    mensagem:
      "Parabens! Voce foi um dos nossos melhores clientes do mes! \u{1F3C6}",
    mensagem_brinde:
      "Parabens! Voce foi um dos nossos melhores clientes do mes. Passe em nossa loja e retire seu brinde especial - sera um prazer recebe-lo! \u{1F381}",
    retirar_de: "",
    retirar_ate: "",
  };
}
